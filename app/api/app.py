import asyncio
import base64
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from ..config import get_settings
from ..db.session import create_engine_from_settings, get_session_factory, session_scope, set_current_tenant
from ..repositories.history import HistoryRepository
from ..repositories.jobs import JobRepository, customs_job_to_payload, extraction_job_to_payload
from ..repositories.llm_settings import LlmSettingsRepository
from ..repositories.templates import TemplateRepository
from ..repositories.tenants import get_or_create_tenant
from ..storage.assets import LocalAssetStorage
from .agent import router as agent_router, set_extraction_enqueue_callback
from ..store.history_store import (
    save_history_record,
    list_history_records,
    load_history_record,
    update_history_record_response,
    get_history_zip_path,
    get_history_asset_path,
    read_history_text_file,
    delete_history_record,
)
from ..store.llm_settings_store import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_API_KEY,
    load_llm_settings,
    save_llm_settings,
    resolve_active_llm_config,
)
from ..store.template_store import (
    load_templates,
    save_templates,
    reset_templates,
)
from ..services.customs_submission import (
    build_submission_draft,
    attach_submission_draft,
    merge_submission_draft,
    validate_submission_draft,
)
from ..services.customs_browser import submit_to_customs_site
from ..services.llm_extract import run_llm_extract
from ..services.mineru_extractor import run_mineru_and_read_text, normalize_newlines, guess_text_from_outputs
from ..services.excel_extractor import run_excel_and_read_text
from ..services.opendataloader_extractor import run_opendataloader_and_read_text
from ..services.qwen_vision_extractor import run_qwen_vision_extract
from ..services.spatial_extract import parse_region_rules, extract_fields_by_regions
from ..services.text_extract import extract_kv_fields

app = FastAPI()
app.include_router(agent_router, prefix="/api/v1/agent")

FIXED_MINERU_API_TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3MjAwNjY1OCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3MjYwOTM3MSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTMzNzIxNzc0MjAiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI5YzQ5YThiMi1iMTliLTRlMzYtYmIzMS05MGRiYTQxMTdlMjYiLCJlbWFpbCI6IiIsImV4cCI6MTc4MDM4NTM3MX0.shcTkrDG_GTPlPzPM_lqmmdVT4nPJE4OqE6-XLXA2uNQ8F-MpNvO2KA926FNdTJz6-ZN2UsYRhAugPL2h7zw8Q"
DEFAULT_MINERU_MODEL_VERSION = "vlm"
DEFAULT_MINERU_PARSE_METHOD = "auto"
DEFAULT_MINERU_LANG_LIST = ["en"]
DEFAULT_OCR_ENGINE = "mineru"
MAX_PREVIEW_CHARS = 300000
MAX_EXTRACT_TASKS = 200
_EXTRACT_TASKS: dict[str, dict[str, Any]] = {}
_EXTRACT_TASKS_LOCK = asyncio.Lock()
_CUSTOMS_SUBMIT_TASKS: dict[str, dict[str, Any]] = {}
_CUSTOMS_SUBMIT_TASKS_LOCK = asyncio.Lock()
ROTATION_ANGLES = (0, 90, 180, 270)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:16066",
        "http://127.0.0.1:16066",
        "http://101.132.68.191:16066",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://101.132.68.191:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_root = Path(__file__).resolve().parent.parent.parent
dist_dir = project_root / "frontend" / "dist"
dist_assets_dir = dist_dir / "assets"
if dist_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_assets_dir)), name="assets")

_file_save_history_record = save_history_record
_file_list_history_records = list_history_records
_file_load_history_record = load_history_record
_file_update_history_record_response = update_history_record_response
_file_get_history_zip_path = get_history_zip_path
_file_get_history_asset_path = get_history_asset_path
_file_read_history_text_file = read_history_text_file
_file_delete_history_record = delete_history_record
_file_load_llm_settings = load_llm_settings
_file_save_llm_settings = save_llm_settings
_file_load_templates = load_templates
_file_save_templates = save_templates
_file_reset_templates = reset_templates


def _database_stores_enabled() -> bool:
    return bool(get_settings().use_database_stores)


def _database_jobs_enabled() -> bool:
    return bool(get_settings().use_database_jobs)


@contextmanager
def _tenant_repository_session():
    settings = get_settings()
    factory = get_session_factory()
    with session_scope(factory) as session:
        tenant = get_or_create_tenant(session, settings.default_tenant_slug, name=settings.default_tenant_slug)
        set_current_tenant(session, str(tenant.id))
        yield session, str(tenant.id)


def _local_asset_storage() -> LocalAssetStorage:
    configured = Path(get_settings().local_asset_root)
    root = configured if configured.is_absolute() else project_root / configured
    return LocalAssetStorage(root)


def load_templates(project_root: Path) -> list[dict[str, Any]]:
    if not _database_stores_enabled():
        return _file_load_templates(project_root=project_root)
    with _tenant_repository_session() as (session, tenant_id):
        return TemplateRepository(session).list_templates(tenant_id)


def save_templates(project_root: Path, payload: Any) -> list[dict[str, Any]]:
    if not _database_stores_enabled():
        return _file_save_templates(project_root=project_root, payload=payload)
    with _tenant_repository_session() as (session, tenant_id):
        return TemplateRepository(session).replace_templates(tenant_id, payload)


def reset_templates(project_root: Path) -> list[dict[str, Any]]:
    if not _database_stores_enabled():
        return _file_reset_templates(project_root=project_root)
    with _tenant_repository_session() as (session, tenant_id):
        return TemplateRepository(session).reset_templates(tenant_id)


def load_llm_settings(project_root: Path) -> dict[str, Any]:
    if not _database_stores_enabled():
        return _file_load_llm_settings(project_root=project_root)
    with _tenant_repository_session() as (session, tenant_id):
        return LlmSettingsRepository(session).load_settings(tenant_id)


def save_llm_settings(project_root: Path, payload: Any) -> dict[str, Any]:
    if not _database_stores_enabled():
        return _file_save_llm_settings(project_root=project_root, payload=payload)
    with _tenant_repository_session() as (session, tenant_id):
        return LlmSettingsRepository(session).save_settings(tenant_id, payload)


def save_history_record(
    project_root: Path,
    response_payload: dict[str, Any],
    zip_bytes: bytes | None,
    extra_assets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not _database_stores_enabled():
        return _file_save_history_record(
            project_root=project_root,
            response_payload=response_payload,
            zip_bytes=zip_bytes,
            extra_assets=extra_assets,
        )
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).save_history_record(
            tenant_id=tenant_id,
            response_payload=response_payload,
            zip_bytes=zip_bytes,
            extra_assets=extra_assets,
        )


def list_history_records(project_root: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not _database_stores_enabled():
        return _file_list_history_records(project_root=project_root, limit=limit)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).list_history_records(tenant_id, limit=limit)


def load_history_record(project_root: Path, record_id: str) -> dict[str, Any] | None:
    if not _database_stores_enabled():
        return _file_load_history_record(project_root=project_root, record_id=record_id)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).load_history_record(tenant_id, record_id)


def update_history_record_response(
    project_root: Path,
    record_id: str,
    response_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not _database_stores_enabled():
        return _file_update_history_record_response(
            project_root=project_root,
            record_id=record_id,
            response_payload=response_payload,
        )
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).update_history_record_response(
            tenant_id,
            record_id,
            response_payload,
        )


def get_history_zip_path(project_root: Path, record_id: str) -> Path | None:
    if not _database_stores_enabled():
        return _file_get_history_zip_path(project_root=project_root, record_id=record_id)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).get_history_zip_path(tenant_id, record_id)


def get_history_asset_path(project_root: Path, record_id: str, file_path: str) -> Path | None:
    if not _database_stores_enabled():
        return _file_get_history_asset_path(project_root=project_root, record_id=record_id, file_path=file_path)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).get_history_asset_path(tenant_id, record_id, file_path)


def read_history_text_file(project_root: Path, record_id: str, file_path: str) -> dict[str, Any] | None:
    if not _database_stores_enabled():
        return _file_read_history_text_file(project_root=project_root, record_id=record_id, file_path=file_path)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).read_history_text_file(tenant_id, record_id, file_path)


def delete_history_record(project_root: Path, record_id: str) -> bool:
    if not _database_stores_enabled():
        return _file_delete_history_record(project_root=project_root, record_id=record_id)
    with _tenant_repository_session() as (session, tenant_id):
        return HistoryRepository(session, _local_asset_storage()).delete_history_record(tenant_id, record_id)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/ready")
async def readiness():
    settings = get_settings()
    checks = {"database": "disabled", "asset_storage": "ok"}
    if settings.use_database_stores or settings.use_database_jobs or settings.environment.strip().lower() == "production":
        try:
            engine = create_engine_from_settings(settings)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"failed: {str(exc)[:160]}"
            return JSONResponse({"status": "not_ready", "checks": checks}, status_code=503)
    return {"status": "ready", "checks": checks}


@app.get("/api/llm-settings")
async def llm_settings_get_api():
    try:
        settings = load_llm_settings(project_root=project_root)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载 LLM 设置失败: {str(exc)[:180]}")
    return JSONResponse(settings)


@app.get("/api/platform-insights")
async def platform_insights_api():
    try:
        payload = await _build_platform_insights_payload()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载平台运营概览失败: {str(exc)[:180]}")
    return JSONResponse(payload)


@app.put("/api/llm-settings")
async def llm_settings_put_api(payload: dict = Body(...)):
    try:
        settings = save_llm_settings(project_root=project_root, payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存 LLM 设置失败: {str(exc)[:180]}")
    return JSONResponse(settings)

@app.get("/api/templates")
async def templates_get_api():
    try:
        items = load_templates(project_root=project_root)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载模板失败: {str(exc)[:180]}")
    return JSONResponse({"items": items})


@app.put("/api/templates")
async def templates_put_api(payload: dict = Body(...)):
    try:
        items = save_templates(project_root=project_root, payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存模板失败: {str(exc)[:180]}")
    return JSONResponse({"items": items})


@app.delete("/api/templates")
async def templates_reset_api():
    try:
        items = reset_templates(project_root=project_root)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重置模板失败: {str(exc)[:180]}")
    return JSONResponse({"items": items})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_extract_task(task_id: str, **updates) -> None:
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            JobRepository(session).update_extraction_job(tenant_id, task_id, updates)
        return
    async with _EXTRACT_TASKS_LOCK:
        task = _EXTRACT_TASKS.get(task_id)
        if not task:
            task = None
        if task:
            task.update(updates)
            task["updated_at"] = _utc_now_iso()
            return
    try:
        with _tenant_repository_session() as (session, tenant_id):
            JobRepository(session).update_extraction_job(tenant_id, task_id, updates)
    except Exception:
        return


async def _update_customs_submit_task(task_id: str, **updates) -> None:
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            JobRepository(session).update_customs_submit_job(tenant_id, task_id, updates)
        return
    async with _CUSTOMS_SUBMIT_TASKS_LOCK:
        task = _CUSTOMS_SUBMIT_TASKS.get(task_id)
        if not task:
            task = None
        if task:
            task.update(updates)
            task["updated_at"] = _utc_now_iso()
            return
    try:
        with _tenant_repository_session() as (session, tenant_id):
            JobRepository(session).update_customs_submit_job(tenant_id, task_id, updates)
    except Exception:
        return


def _prune_extract_tasks_unlocked() -> None:
    if len(_EXTRACT_TASKS) <= MAX_EXTRACT_TASKS:
        return
    items = sorted(
        _EXTRACT_TASKS.items(),
        key=lambda kv: str(kv[1].get("updated_at") or kv[1].get("created_at") or ""),
        reverse=True,
    )
    keep_ids = {task_id for task_id, _ in items[:MAX_EXTRACT_TASKS]}
    for task_id in list(_EXTRACT_TASKS.keys()):
        if task_id not in keep_ids:
            _EXTRACT_TASKS.pop(task_id, None)


def _prune_customs_submit_tasks_unlocked() -> None:
    if len(_CUSTOMS_SUBMIT_TASKS) <= MAX_EXTRACT_TASKS:
        return
    items = sorted(
        _CUSTOMS_SUBMIT_TASKS.items(),
        key=lambda kv: str(kv[1].get("updated_at") or kv[1].get("created_at") or ""),
        reverse=True,
    )
    keep_ids = {task_id for task_id, _ in items[:MAX_EXTRACT_TASKS]}
    for task_id in list(_CUSTOMS_SUBMIT_TASKS.keys()):
        if task_id not in keep_ids:
            _CUSTOMS_SUBMIT_TASKS.pop(task_id, None)


def _resolve_template_for_history(detail: dict[str, Any]) -> dict[str, Any]:
    vendor = str(detail.get("vendor") or detail.get("response", {}).get("vendor") or "").strip()
    doc_type = str(detail.get("doc_type") or detail.get("response", {}).get("doc_type") or "").strip()
    try:
        items = load_templates(project_root=project_root)
    except Exception:
        items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("vendor") or "").strip() == vendor and str(item.get("doc_type") or "").strip() == doc_type:
            return item
    return {}


def _build_customs_submission_prompt(template: dict[str, Any], response_payload: dict[str, Any]) -> str:
    customs_mapping = template.get("customs_mapping") if isinstance(template, dict) else {}
    mapping_hint = customs_mapping if isinstance(customs_mapping, dict) else {}
    return (
        "请将输入内容整理为报关网站填报草稿，直接输出 JSON 对象。"
        "输出结构必须为："
        '{"header":{"Mawb":"","Hawb":"","CustomerName":"","TradeType":"","OriginCountry":"","InvoiceNo":"","Quantity":"","GrossWeight":"","NetWeight":"","TotalSheets":"","TotalQuantity":"","GoodQuantity":"","TotalPrice":""},'
        '"details":[{"ItemCode":"","ItemOrigin":"","ItemQuantity":"","ItemGoodQuantity":"","ItemPrice":"","ItemUnitPrice":""}],'
        '"packet_id":"","header_candidates":{},'
        '"invoice_lines":[{"source_row":"","ITEM":"","P/O No":"","SAMSUNG P/N":"","PC":"","@RMB/1000":"","@USD/1000":"","RMB":"","USD":"","Country of Origin":""}],'
        '"packing_lines":[{"source_row":"","C/T NO":"","ITEM":"","P/O No":"","SAMSUNG P/N":"","PC":""}],'
        '"meta":{"mapping_notes":"","unmapped_fields":[]}}。'
        "header 和 details 只允许使用这些目标字段；缺失值返回空字符串；无明细时返回空数组。"
        " 报关资料按一票业务处理，不要把发票和箱单拆成两条订单。"
        " 商品明细按发票原始商品行生成；即使 ITEM、P/O No、SAMSUNG P/N 完全相同，也不要合并发票行。"
        " 箱单按 ITEM + P/O No + SAMSUNG P/N 汇总校验，C/T NO 只是装箱来源，不决定商品明细条数。"
        " 如果发票数量与箱单汇总数量不一致，仍继续生成草稿，申报数量取发票数量，并在 header_candidates 或 meta 中说明需人工复核。"
        " header_candidates 用于字段冲突的人工选择：每个字段可输出 recommended、candidates、review_required、reason。"
        " CustomerName 表示发货客户，必须优先从 OCR 结果中的 `Shipper's Name` 或 `Shipper's Name and Address` 提取。"
        " 如果同时存在 Shipper 与 Consignee，CustomerName 只能取 Shipper，不能取 Consignee、收货方、收货客户。"
        " TradeType 对应单据中的 Freight Terms 或 Incoterm。"
        " 必须优先从 `Freight Terms`、`Incoterm` 或 `Incoterms` 提取，不要从运输方式、付款方式或备注字段推断。"
        " Quantity 对应件数。"
        " 必须优先从 `No. of Process RCP` 提取。"
        " TotalQuantity 对应总数量。"
        " 必须优先从 `Qty`、`QTY` 或 `Summary Quantity` 提取。"
        " GoodQuantity 对应良品总数量。"
        " 必须优先从 `Gross Qty` 或 `Summary Gross Qty` 提取。"
        " TotalSheets 对应总片数。"
        " 必须优先从 `Die Qty`、`WaferQty`、`Wafer Qty` 或 `Summary WaferQty` 提取，不表示件数或文档页数。"
        " OriginCountry 表示原产国，必须优先从 `Country of Origin`、`原产国` 或 `ORIGINAL OF COUNTRY` 提取。"
        " 不能使用启运国、From、起运国、出发国或其他运输起运字段来填写 OriginCountry。"
        " 如果同时存在原产国和启运国，OriginCountry 只能取原产国。"
        f" 当前单据类型：{str(response_payload.get('doc_type') or '').strip()}，厂商：{str(response_payload.get('vendor') or '').strip()}。"
        f" 如果模板中已有历史映射，请作为强提示参考：{mapping_hint}。"
    )


def _build_customs_submission_context(response_payload: dict[str, Any]) -> str:
    preview = str(response_payload.get("preview") or "").strip()
    detected = response_payload.get("detected")
    fallback_detected = response_payload.get("fallback_detected")
    region_detected = response_payload.get("region_detected")
    source = {
        "vendor": response_payload.get("vendor"),
        "doc_type": response_payload.get("doc_type"),
        "detected": detected if isinstance(detected, dict) else {},
        "fallback_detected": fallback_detected if isinstance(fallback_detected, dict) else {},
        "region_detected": region_detected if isinstance(region_detected, dict) else {},
        "preview": preview[:4000],
    }
    return json.dumps(source, ensure_ascii=False)


def _count_submission_review(submission: Any) -> dict[str, int | str]:
    if not isinstance(submission, dict):
        return {"missing": 0, "review": 0, "label": "未生成草稿"}
    meta = submission.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    missing_items = meta.get("required_missing")
    missing = len(missing_items) if isinstance(missing_items, list) else 0
    packet = meta.get("packet")
    if not isinstance(packet, dict):
        packet = {}
    review = 0
    for key in ("field_reviews", "detail_reviews"):
        items = packet.get(key)
        if isinstance(items, list):
            review += sum(1 for item in items if isinstance(item, dict) and bool(item.get("review_required")))
    status = str(meta.get("submit_status") or "idle").strip()
    if missing or review:
        label = f"缺失 {missing} / 复核 {review}"
    elif status == "succeeded":
        label = "已填报"
    elif status == "failed":
        label = "填报失败"
    else:
        label = "低风险"
    return {"missing": missing, "review": review, "label": label}


def _build_platform_recommendations(
    *,
    queue: dict[str, int],
    templates: dict[str, Any],
    review: dict[str, int],
    automation: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    if review["missing_fields"] or review["review_items"]:
        recommendations.append(f"当前存在待复核资料：缺失 {review['missing_fields']} 项，复核 {review['review_items']} 项。")
    if templates["vendor"] < templates["common"]:
        recommendations.append("来源专属模板覆盖偏少，建议优先为高频客户沉淀专属模板。")
    if queue["failed"] > 0:
        recommendations.append(f"近期有 {queue['failed']} 个任务失败，建议先查看审核中心异常记录。")
    if not automation["enabled"]:
        recommendations.append("自动化流水线未开启，客户试点阶段建议先人工审核后再逐步开启。")
    if not recommendations:
        recommendations.append("平台状态稳定，可继续扩大样本并沉淀模板规则。")
    return recommendations[:4]


def _safe_load_history_detail(record_id: Any) -> dict[str, Any] | None:
    try:
        return load_history_record(project_root=project_root, record_id=str(record_id or ""))
    except Exception:
        return None


async def _build_platform_insights_payload() -> dict[str, Any]:
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            job_repo = JobRepository(session)
            extract_tasks = [extraction_job_to_payload(row) for row in job_repo.list_extraction_jobs(tenant_id, limit=200)]
            customs_tasks = [customs_job_to_payload(row) for row in job_repo.list_customs_submit_jobs(tenant_id, limit=200)]
    else:
        async with _EXTRACT_TASKS_LOCK:
            extract_tasks = list(_EXTRACT_TASKS.values())
        async with _CUSTOMS_SUBMIT_TASKS_LOCK:
            customs_tasks = list(_CUSTOMS_SUBMIT_TASKS.values())
    queue = {"queued": 0, "running": 0, "failed": 0, "succeeded": 0}
    for task in [*extract_tasks, *customs_tasks]:
        status = str(task.get("status") if isinstance(task, dict) else "").strip().lower()
        if status in queue:
            queue[status] += 1

    try:
        history_items = list_history_records(project_root=project_root, limit=200)
    except Exception:
        history_items = []

    try:
        template_items = load_templates(project_root=project_root)
    except Exception:
        template_items = []
    common_count = sum(1 for item in template_items if str(item.get("vendor") or "").strip() == "通用模板")
    doc_types = sorted(
        {str(item.get("doc_type") or "").strip() for item in template_items if str(item.get("doc_type") or "").strip()},
        key=lambda x: ("到货单", "物流通知书", "送货单", "发票", "报关单").index(x)
        if x in ("到货单", "物流通知书", "送货单", "发票", "报关单")
        else 99,
    )
    template_stats = {
        "total": len(template_items),
        "common": common_count,
        "vendor": max(0, len(template_items) - common_count),
        "doc_types": doc_types,
    }

    try:
        settings = load_llm_settings(project_root=project_root)
    except Exception:
        settings = {}
    active_config = resolve_active_llm_config(settings)
    automation = {
        "enabled": bool(active_config.get("auto_mode_enabled")),
        "submit_mode": str(active_config.get("customs_submit_mode") or "http"),
        "active_model": str(active_config.get("llm_model") or ""),
    }

    review = {
        "drafts_checked": 0,
        "drafts_with_warnings": 0,
        "missing_fields": 0,
        "review_items": 0,
    }
    recent = []
    for item in history_items[:30]:
        detail = _safe_load_history_detail(item.get("id") if isinstance(item, dict) else "")
        response_payload = detail.get("response") if isinstance(detail, dict) else {}
        if not isinstance(response_payload, dict):
            response_payload = {}
        submission = response_payload.get("submission")
        review_info = _count_submission_review(submission)
        if isinstance(submission, dict):
            review["drafts_checked"] += 1
            review["missing_fields"] += int(review_info["missing"])
            review["review_items"] += int(review_info["review"])
            if int(review_info["missing"]) or int(review_info["review"]):
                review["drafts_with_warnings"] += 1
        if len(recent) < 8 and isinstance(item, dict):
            recent.append({
                "id": str(item.get("id") or ""),
                "filename": str(item.get("filename") or ""),
                "vendor": str(item.get("vendor") or ""),
                "doc_type": str(item.get("doc_type") or ""),
                "created_at": str(item.get("created_at") or ""),
                "status": str(response_payload.get("submission", {}).get("meta", {}).get("submit_status") or "idle")
                if isinstance(response_payload.get("submission"), dict)
                else "idle",
                "review_label": str(review_info["label"]),
            })

    payload = {
        "generated_at": _utc_now_iso(),
        "queue": queue,
        "history": {
            "total": len(history_items),
            "recent": recent,
        },
        "templates": template_stats,
        "review": review,
        "automation": automation,
    }
    payload["recommendations"] = _build_platform_recommendations(
        queue=queue,
        templates=template_stats,
        review=review,
        automation=automation,
    )
    return payload


def _generate_submission_draft_with_llm(response_payload: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    resolved_llm_base_url, resolved_llm_model, resolved_llm_api_key = _resolve_runtime_llm_settings(
        llm_base_url="",
        llm_model="",
        llm_api_key="",
    )
    llm_result = run_llm_extract(
        text=_build_customs_submission_context(response_payload),
        user_prompt=_build_customs_submission_prompt(template, response_payload),
        targets=["header", "details", "meta"],
        base_url=resolved_llm_base_url,
        model=resolved_llm_model,
        api_key=resolved_llm_api_key,
    )
    draft = build_submission_draft(
        response_payload=response_payload,
        template=template,
        llm_output=llm_result.get("detected") if isinstance(llm_result, dict) else None,
    )
    draft["meta"]["llm_model"] = str(llm_result.get("model") or resolved_llm_model)
    draft["meta"]["llm_endpoint"] = str(llm_result.get("endpoint") or resolved_llm_base_url)
    return draft


def _get_history_response_payload(record_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    detail = load_history_record(project_root=project_root, record_id=record_id)
    if not detail:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    response_payload = detail.get("response")
    if not isinstance(response_payload, dict):
        response_payload = {}
    return detail, response_payload


async def _run_customs_submit_task(task_id: str, record_id: str, draft: dict[str, Any]) -> None:
    await _update_customs_submit_task(
        task_id,
        status="running",
        stage="logging_in",
        progress=15,
        message="正在登录报关系统",
    )
    try:
        try:
            settings = load_llm_settings(project_root=project_root)
        except Exception:
            settings = {}
        customs_submit_mode = (
            str(settings.get("customs_submit_mode") or "http").strip().lower()
            if isinstance(settings, dict)
            else "http"
        )
        credentials = {
            "site_url": str(os.getenv("CUSTOMS_SITE_URL") or "https://vatest.carsem.com.cn").strip(),
            "username": str(os.getenv("CUSTOMS_USERNAME") or "").strip(),
            "password": str(os.getenv("CUSTOMS_PASSWORD") or "").strip(),
        }
        result = await asyncio.to_thread(submit_to_customs_site, draft, credentials, customs_submit_mode)
        detail, response_payload = _get_history_response_payload(record_id)
        merged_draft = merge_submission_draft(response_payload.get("submission") or {}, draft)
        meta = merged_draft.setdefault("meta", {})
        meta["submit_status"] = "succeeded"
        meta["submit_message"] = str(result.get("message") or "提交成功")
        meta["submit_result"] = result
        meta["submit_engine"] = str(result.get("submit_engine") or customs_submit_mode)
        updated_response = attach_submission_draft(response_payload, merged_draft)
        update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
        await _update_customs_submit_task(
            task_id,
            status="succeeded",
            stage="done",
            progress=100,
            message=str(result.get("message") or "提交成功"),
            result=result,
        )
    except Exception as exc:
        try:
            detail, response_payload = _get_history_response_payload(record_id)
            merged_draft = merge_submission_draft(response_payload.get("submission") or {}, draft)
            meta = merged_draft.setdefault("meta", {})
            meta["submit_status"] = "failed"
            meta["submit_message"] = str(exc)
            meta["submit_result"] = None
            updated_response = attach_submission_draft(response_payload, merged_draft)
            update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
        except Exception:
            pass
        await _update_customs_submit_task(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            message="报关填报失败",
            error=str(exc)[:300],
        )


def _build_extract_payload(
    *,
    file_name: str,
    file_bytes: bytes,
    vendor: str,
    doc_type: str,
    fields: str,
    region_rules: str,
    llm_prompt: str,
    llm_base_url: str,
    llm_model: str,
    llm_api_key: str,
    mineru_model_version: str,
    backend: str,
    parse_method: str,
    lang_list: str,
    ocr_engine: str = DEFAULT_OCR_ENGINE,
    progress_cb: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    def progress(stage: str, pct: int, message: str) -> None:
        if progress_cb:
            progress_cb(stage, pct, message)

    allowed = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".doc", ".docx", ".ppt", ".pptx", ".xlsx"]
    suffix = Path(file_name).suffix.lower()
    if suffix not in allowed:
        raise ValueError("仅支持 PDF/Office/图片/Excel 文件")
    if not file_bytes:
        raise ValueError("上传文件为空")
    original_file_bytes = file_bytes

    manual_targets = _parse_fields(fields)
    try:
        parsed_region_rules = parse_region_rules(region_rules)
    except ValueError as exc:
        raise ValueError(str(exc))
    region_targets = [rule.field for rule in parsed_region_rules]
    targets = _merge_targets(manual_targets, region_targets)
    llm_prompt_text = llm_prompt.strip()
    if not llm_prompt_text:
        raise ValueError("请填写大模型提取提示词")
    resolved_llm_base_url, resolved_llm_model, resolved_llm_api_key = _resolve_runtime_llm_settings(
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
    )
    resolved_ocr_engine = _normalize_ocr_engine(ocr_engine)
    requested_model_version = _normalize_model_version(mineru_model_version or backend or DEFAULT_MINERU_MODEL_VERSION)
    requested_parse_method = str(parse_method or DEFAULT_MINERU_PARSE_METHOD).strip() or DEFAULT_MINERU_PARSE_METHOD
    lang_items = _parse_lang_list(lang_list)
    api_token_value = str(FIXED_MINERU_API_TOKEN or "").strip() or None
    suffix = Path(file_name).suffix.lower()

    osd_rotation_attempted = False
    osd_rotation_used = False
    osd_rotation_message = ""
    osd_rotation_page_angles: list[int] = []
    if suffix == ".pdf":
        osd_rotation_attempted = True
        progress("preprocess_osd", 15, "Tesseract OSD 自动校正方向")
        rotated_bytes, used, message, page_angles = _auto_rotate_pdf_with_osd(file_bytes)
        file_bytes = rotated_bytes
        osd_rotation_used = used
        osd_rotation_message = message
        osd_rotation_page_angles = page_angles

    def run_single_extraction(current_bytes: bytes, rotation_angle: int) -> tuple[dict[str, Any], dict[str, Any], int, int]:
        actual_model_version = requested_model_version
        fallback_used = False
        fallback_reason = None
        is_excel_file = suffix == ".xlsx"
        effective_ocr_engine = "excel" if is_excel_file else resolved_ocr_engine
        if is_excel_file:
            outputs_local = run_excel_and_read_text(
                file_name=file_name,
                file_bytes=current_bytes,
            )
            actual_model_version = "excel"
        elif resolved_ocr_engine == "qwen_vision":
            qwen_output = run_qwen_vision_extract(
                file_name=file_name,
                file_bytes=current_bytes,
                vendor=vendor,
                doc_type=doc_type,
                llm_prompt=llm_prompt_text,
                base_url=resolved_llm_base_url,
                model=resolved_llm_model,
                api_key=resolved_llm_api_key,
                targets=targets,
            )
            detected = qwen_output.get("detected", {})
            preview_text = normalize_newlines(str(qwen_output.get("preview") or qwen_output.get("markdown") or qwen_output.get("content") or ""))
            payload_local = {
                "filename": file_name,
                "vendor": str(vendor or "").strip(),
                "doc_type": str(doc_type or "").strip(),
                "targets": targets,
                "detected": detected if isinstance(detected, dict) else {},
                "fallback_detected": {},
                "region_detected": {},
                "llm_detected": detected if isinstance(detected, dict) else {},
                "llm_prompt": llm_prompt_text,
                "llm_endpoint": qwen_output.get("endpoint"),
                "llm_model": qwen_output.get("model"),
                "llm_content_preview": (qwen_output.get("content", "") or "")[:1200],
                "preview": preview_text[:MAX_PREVIEW_CHARS],
                "ocr_engine": effective_ocr_engine,
                "ocr_engine_label": _ocr_engine_label(effective_ocr_engine),
                "mineru_api": "",
                "mineru_url": "",
                "model_version": "qwen_vision",
                "backend": "qwen_vision",
                "requested_model_version": requested_model_version,
                "requested_backend": requested_model_version,
                "parse_method": requested_parse_method,
                "lang_list": lang_items,
                "region_rules": region_rules,
                "region_rules_count": len(parsed_region_rules),
                "fallback_used": False,
                "fallback_reason": None,
                "parse_package": {
                    "zip_url": "",
                    "zip_entries": [],
                    "zip_size": 0,
                },
                "rotation_angle": rotation_angle,
                "osd_rotation_attempted": osd_rotation_attempted,
                "osd_rotation_used": osd_rotation_used,
                "osd_rotation_message": osd_rotation_message,
                "osd_rotation_page_angles": osd_rotation_page_angles,
            }
            outputs_local = {
                "text": preview_text,
                "markdown": str(qwen_output.get("markdown") or preview_text),
                "json": detected if isinstance(detected, dict) else {},
                "middle_json": None,
                "history_assets": qwen_output.get("history_assets") or [],
                "zip_entries": [],
                "zip_size": 0,
            }
            score = _count_detected_hits(payload_local.get("detected"))
            quality = _estimate_text_quality(payload_local.get("preview"))
            payload_local["preview_quality_score"] = quality
            return payload_local, outputs_local, score, quality
        elif resolved_ocr_engine == "opendataloader":
            outputs_local = run_opendataloader_and_read_text(
                file_name=file_name,
                file_bytes=current_bytes,
            )
            actual_model_version = "opendataloader"
        else:
            try:
                outputs_local = run_mineru_and_read_text(
                    file_name=file_name,
                    file_bytes=current_bytes,
                    backend=actual_model_version,
                    parse_method=requested_parse_method,
                    lang_list=lang_items,
                    api_token=api_token_value,
                    model_version=actual_model_version,
                )
            except RuntimeError as exc:
                error_text = str(exc)
                if _should_fallback_to_pipeline(actual_model_version, error_text):
                    fallback_used = True
                    fallback_reason = error_text[:500]
                    actual_model_version = "pipeline"
                    try:
                        outputs_local = run_mineru_and_read_text(
                            file_name=file_name,
                            file_bytes=current_bytes,
                            backend=actual_model_version,
                            parse_method=requested_parse_method,
                            lang_list=lang_items,
                            api_token=api_token_value,
                            model_version=actual_model_version,
                        )
                    except RuntimeError as second_exc:
                        raise RuntimeError(str(second_exc))
                else:
                    raise RuntimeError(error_text)

        text = normalize_newlines(guess_text_from_outputs(outputs_local))
        llm_output = run_llm_extract(
            text=text,
            user_prompt=llm_prompt_text,
            targets=targets,
            base_url=resolved_llm_base_url,
            model=resolved_llm_model,
            api_key=resolved_llm_api_key,
        )

        llm_detected = llm_output.get("detected", {})
        region_detected = extract_fields_by_regions(outputs_local.get("middle_json"), parsed_region_rules)
        detected = {**llm_detected, **region_detected}
        merged_targets = _merge_targets(targets, list(detected.keys()))
        guess = {}
        if not detected and targets:
            guess = extract_kv_fields(guess_text_from_outputs(outputs_local), targets)
        if not detected and guess:
            detected = guess
            merged_targets = _merge_targets(merged_targets, list(guess.keys()))

        payload_local: dict[str, Any] = {
            "filename": file_name,
            "vendor": str(vendor or "").strip(),
            "doc_type": str(doc_type or "").strip(),
            "targets": merged_targets,
            "detected": detected,
            "fallback_detected": guess,
            "region_detected": region_detected,
            "llm_detected": llm_detected,
            "llm_prompt": llm_prompt_text,
            "llm_endpoint": llm_output.get("endpoint"),
            "llm_model": llm_output.get("model"),
            "llm_content_preview": (llm_output.get("content", "") or "")[:1200],
            "preview": text[:MAX_PREVIEW_CHARS],
            "ocr_engine": effective_ocr_engine,
            "ocr_engine_label": _ocr_engine_label(effective_ocr_engine),
            "mineru_api": "" if is_excel_file else "official",
            "mineru_url": "" if is_excel_file else "https://mineru.net/api/v4/file-urls/batch",
            "model_version": actual_model_version,
            "backend": actual_model_version,
            "requested_model_version": requested_model_version,
            "requested_backend": requested_model_version,
            "parse_method": requested_parse_method,
            "lang_list": lang_items,
            "region_rules": region_rules,
            "region_rules_count": len(parsed_region_rules),
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "parse_package": {
                "zip_url": outputs_local.get("zip_url"),
                "zip_entries": outputs_local.get("zip_entries") or [],
                "zip_size": outputs_local.get("zip_size") or 0,
            },
            "rotation_angle": rotation_angle,
            "osd_rotation_attempted": osd_rotation_attempted,
            "osd_rotation_used": osd_rotation_used,
            "osd_rotation_message": osd_rotation_message,
            "osd_rotation_page_angles": osd_rotation_page_angles,
        }
        score = _count_detected_hits(payload_local.get("detected"))
        quality = _estimate_text_quality(payload_local.get("preview"))
        payload_local["preview_quality_score"] = quality
        return payload_local, outputs_local, score, quality

    candidates = _build_rotation_candidates(file_name=file_name, file_bytes=file_bytes)
    tried_rotation_angles: list[int] = []
    best_payload: dict[str, Any] | None = None
    best_outputs: dict[str, Any] | None = None
    best_candidate_bytes: bytes | None = None
    best_score = -1
    best_quality = -10**9
    first_error: str | None = None

    for idx, (angle, candidate_bytes) in enumerate(candidates):
        stage = "running_excel" if suffix == ".xlsx" else ("running_mineru" if idx == 0 else "running_rotate_retry")
        msg = "解析 Excel 表格" if suffix == ".xlsx" else ("解析中" if idx == 0 else f"低命中重试旋转 {angle}°")
        pct = 25 if idx == 0 else min(82, 50 + idx * 10)
        progress(stage, pct, msg)
        tried_rotation_angles.append(angle)
        try:
            payload_try, outputs_try, score_try, quality_try = run_single_extraction(candidate_bytes, angle)
        except RuntimeError as exc:
            if first_error is None:
                first_error = str(exc)
            continue
        if (score_try > best_score) or (score_try == best_score and quality_try > best_quality):
            best_payload = payload_try
            best_outputs = outputs_try
            best_candidate_bytes = candidate_bytes
            best_score = score_try
            best_quality = quality_try
        target_count = len(payload_try.get("targets") or [])
        if idx == 0 and not _should_try_rotation_retry(score_try, target_count, quality_try):
            break
        if best_score >= max(1, target_count):
            break

    if not best_payload or not best_outputs:
        raise RuntimeError(first_error or "提取失败")

    response_payload = best_payload
    response_payload["rotation_tried_angles"] = tried_rotation_angles
    response_payload["rotation_retry_used"] = len(tried_rotation_angles) > 1
    response_payload["rotation_selected_angle"] = int(response_payload.get("rotation_angle") or 0)

    progress("saving_history", 90, "历史记录保存中")
    history_error = None
    try:
        extra_assets = _build_history_preview_assets(
            file_name=file_name,
            original_file_bytes=original_file_bytes,
            selected_file_bytes=best_candidate_bytes,
            response_payload=response_payload,
        )
        extra_assets.extend(best_outputs.get("history_assets") or [])
        history_summary = save_history_record(
            project_root=project_root,
            response_payload=response_payload,
            zip_bytes=best_outputs.get("zip_bytes"),
            extra_assets=extra_assets,
        )
        history_payload = dict(history_summary)
        history_payload["download_url"] = f"/api/history/{history_summary['id']}/download"
        response_payload["history"] = history_payload
    except Exception as exc:
        history_error = str(exc)[:300]
    if history_error:
        response_payload["history_error"] = history_error
    return response_payload


@app.post("/api/extract")
async def extract_api(
    file: UploadFile = File(...),
    vendor: str = Form(""),
    doc_type: str = Form(""),
    fields: str = Form(""),
    region_rules: str = Form(""),
    llm_prompt: str = Form(""),
    llm_base_url: str = Form(""),
    llm_model: str = Form(""),
    llm_api_key: str = Form(""),
    mineru_model_version: str = Form("vlm"),
    backend: str = Form("vlm"),  # backward compatibility for old frontend payloads
    parse_method: str = Form("auto"),
    lang_list: str = Form("ch"),
    ocr_engine: str = Form(DEFAULT_OCR_ENGINE),
):
    file_bytes = await file.read()
    try:
        payload = _build_extract_payload(
            file_name=file.filename,
            file_bytes=file_bytes,
            vendor=vendor,
            doc_type=doc_type,
            fields=fields,
            region_rules=region_rules,
            llm_prompt=llm_prompt,
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            mineru_model_version=mineru_model_version,
            backend=backend,
            parse_method=parse_method,
            lang_list=lang_list,
            ocr_engine=ocr_engine,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return JSONResponse(payload)


async def _run_extract_task(task_id: str, task_input: dict[str, Any]) -> None:
    loop = asyncio.get_running_loop()

    def progress_cb(stage: str, pct: int, message: str) -> None:
        asyncio.run_coroutine_threadsafe(
            _update_extract_task(
                task_id,
                stage=stage,
                progress=max(0, min(100, int(pct))),
                message=message,
                status="running",
            ),
            loop,
        )

    await _update_extract_task(task_id, status="running", stage="running_prepare", progress=10, message="任务已启动")
    try:
        try:
            settings = load_llm_settings(project_root=project_root)
        except Exception:
            settings = {}
        auto_mode_enabled = bool(settings.get("auto_mode_enabled")) if isinstance(settings, dict) else False
        customs_submit_mode = (
            str(settings.get("customs_submit_mode") or "http").strip().lower()
            if isinstance(settings, dict)
            else "http"
        )

        payload = await asyncio.to_thread(
            _build_extract_payload,
            file_name=task_input["file_name"],
            file_bytes=task_input["file_bytes"],
            vendor=task_input["vendor"],
            doc_type=task_input["doc_type"],
            fields=task_input["fields"],
            region_rules=task_input["region_rules"],
            llm_prompt=task_input["llm_prompt"],
            llm_base_url=task_input["llm_base_url"],
            llm_model=task_input["llm_model"],
            llm_api_key=task_input["llm_api_key"],
            mineru_model_version=task_input["mineru_model_version"],
            backend=task_input["backend"],
            parse_method=task_input["parse_method"],
            lang_list=task_input["lang_list"],
            ocr_engine=task_input.get("ocr_engine", DEFAULT_OCR_ENGINE),
            progress_cb=progress_cb,
        )
        history = payload.get("history") if isinstance(payload, dict) else None
        auto_mode_status = "idle"
        auto_mode_message = ""
        customs_submit_task_id = ""

        if auto_mode_enabled and isinstance(history, dict) and history.get("id"):
            await _update_extract_task(
                task_id,
                status="running",
                stage="running_submission_mapping",
                progress=93,
                message="正在生成报关草稿",
            )
            record_id = str(history.get("id") or "").strip()
            detail, response_payload = _get_history_response_payload(record_id)
            template = _resolve_template_for_history(detail)
            draft = await asyncio.to_thread(
                _generate_submission_draft_with_llm,
                response_payload,
                template,
            )
            draft = merge_submission_draft(draft, draft)
            draft.setdefault("meta", {})
            draft["meta"]["submit_status"] = "idle"
            draft["meta"]["submit_message"] = ""
            draft["meta"]["submit_result"] = None
            updated_response = attach_submission_draft(response_payload, draft)
            update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
            response_payload = updated_response

            await _update_extract_task(
                task_id,
                status="running",
                stage="running_customs_submit",
                progress=97,
                message="正在自动填报报关系统",
            )
            draft["meta"]["submit_status"] = "running"
            draft["meta"]["submit_message"] = "正在自动填报报关系统"
            updated_response = attach_submission_draft(response_payload, draft)
            update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
            response_payload = updated_response

            try:
                submit_result = await asyncio.to_thread(
                    submit_to_customs_site,
                    draft,
                    {
                        "site_url": str(os.getenv("CUSTOMS_SITE_URL") or "https://vatest.carsem.com.cn").strip(),
                        "username": str(os.getenv("CUSTOMS_USERNAME") or "vip@dianxin").strip(),
                        "password": str(os.getenv("CUSTOMS_PASSWORD") or "xinpwd@@@2026").strip(),
                    },
                    customs_submit_mode,
                )
            except Exception as exc:
                draft["meta"]["submit_status"] = "failed"
                draft["meta"]["submit_message"] = str(exc)
                draft["meta"]["submit_result"] = None
                draft["meta"]["submit_engine"] = customs_submit_mode
                updated_response = attach_submission_draft(response_payload, draft)
                update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
                raise

            draft["meta"]["submit_status"] = "succeeded"
            draft["meta"]["submit_message"] = str(submit_result.get("message") or "自动填报完成")
            draft["meta"]["submit_result"] = submit_result
            draft["meta"]["submit_engine"] = str(submit_result.get("submit_engine") or customs_submit_mode)
            updated_response = attach_submission_draft(response_payload, draft)
            update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
            auto_mode_status = "succeeded"
            auto_mode_message = str(submit_result.get("message") or "自动填报完成")

        await _update_extract_task(
            task_id,
            status="succeeded",
            stage="done",
            progress=100,
            message="提取完成",
            result={
                "history": history if isinstance(history, dict) else None,
                "fallback_used": bool(payload.get("fallback_used")) if isinstance(payload, dict) else False,
                "model_version": payload.get("model_version") if isinstance(payload, dict) else "",
                "ocr_engine": payload.get("ocr_engine") if isinstance(payload, dict) else DEFAULT_OCR_ENGINE,
                "ocr_engine_label": payload.get("ocr_engine_label") if isinstance(payload, dict) else _ocr_engine_label(DEFAULT_OCR_ENGINE),
                "auto_mode_enabled": auto_mode_enabled,
                "auto_mode_status": auto_mode_status,
                "auto_mode_message": auto_mode_message,
                "submit_engine": str(submit_result.get("submit_engine") or customs_submit_mode) if auto_mode_enabled and isinstance(history, dict) and history.get("id") else "",
                "customs_submit_task_id": customs_submit_task_id,
            },
        )
    except ValueError as exc:
        await _update_extract_task(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            message="参数校验失败",
            error=str(exc),
        )
    except RuntimeError as exc:
        await _update_extract_task(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            message="提取失败",
            error=str(exc),
        )
    except Exception as exc:
        await _update_extract_task(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            message="任务异常终止",
            error=str(exc)[:300],
        )


async def _enqueue_agent_extraction_task(task_id: str, payload: dict[str, Any]) -> None:
    file_name = str(payload.get("filename") or payload.get("file_name") or "").strip()
    if not file_name:
        raise ValueError("filename is required")
    encoded = str(payload.get("file_base64") or payload.get("content_base64") or "").strip()
    if not encoded:
        raise ValueError("file_base64 is required")
    try:
        file_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("file_base64 is invalid") from exc
    if not file_bytes:
        raise ValueError("decoded file is empty")
    task_input = {
        "file_name": file_name,
        "file_bytes": file_bytes,
        "vendor": str(payload.get("vendor") or "").strip(),
        "doc_type": str(payload.get("doc_type") or "").strip(),
        "fields": str(payload.get("fields") or ""),
        "region_rules": str(payload.get("region_rules") or ""),
        "llm_prompt": str(payload.get("llm_prompt") or ""),
        "llm_base_url": str(payload.get("llm_base_url") or ""),
        "llm_model": str(payload.get("llm_model") or ""),
        "llm_api_key": str(payload.get("llm_api_key") or ""),
        "mineru_model_version": str(payload.get("mineru_model_version") or "vlm"),
        "backend": str(payload.get("backend") or "vlm"),
        "parse_method": str(payload.get("parse_method") or "auto"),
        "lang_list": str(payload.get("lang_list") or "ch"),
        "ocr_engine": str(payload.get("ocr_engine") or DEFAULT_OCR_ENGINE),
    }
    asyncio.create_task(_run_extract_task(task_id, task_input))


set_extraction_enqueue_callback(_enqueue_agent_extraction_task)


@app.post("/api/extract/submit")
async def extract_submit_api(
    file: UploadFile = File(...),
    vendor: str = Form(""),
    doc_type: str = Form(""),
    fields: str = Form(""),
    region_rules: str = Form(""),
    llm_prompt: str = Form(""),
    llm_base_url: str = Form(""),
    llm_model: str = Form(""),
    llm_api_key: str = Form(""),
    mineru_model_version: str = Form("vlm"),
    backend: str = Form("vlm"),
    parse_method: str = Form("auto"),
    lang_list: str = Form("ch"),
    ocr_engine: str = Form(DEFAULT_OCR_ENGINE),
):
    file_name = str(file.filename or "").strip()
    if not file_name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")

    now = _utc_now_iso()
    task_input = {
        "file_name": file_name,
        "file_bytes": file_bytes,
        "vendor": str(vendor or "").strip(),
        "doc_type": str(doc_type or "").strip(),
        "fields": fields,
        "region_rules": region_rules,
        "llm_prompt": llm_prompt,
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "llm_api_key": llm_api_key,
        "mineru_model_version": mineru_model_version,
        "backend": backend,
        "parse_method": parse_method,
        "lang_list": lang_list,
        "ocr_engine": ocr_engine,
    }
    if _database_jobs_enabled():
        request_payload = {key: value for key, value in task_input.items() if key != "file_bytes"}
        request_payload["file_size"] = len(file_bytes)
        with _tenant_repository_session() as (session, tenant_id):
            job = JobRepository(session).create_extraction_job(
                tenant_id=tenant_id,
                request_payload=request_payload,
            )
            task_id = job.id.hex
    else:
        task_id = uuid.uuid4().hex
        async with _EXTRACT_TASKS_LOCK:
            _EXTRACT_TASKS[task_id] = {
                "id": task_id,
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待调度",
                "error": "",
                "created_at": now,
                "updated_at": now,
                "filename": file_name,
                "vendor": str(vendor or "").strip(),
                "doc_type": str(doc_type or "").strip(),
                "result": None,
            }
            _prune_extract_tasks_unlocked()
    asyncio.create_task(_run_extract_task(task_id, task_input))
    return JSONResponse({"task_id": task_id, "status": "queued", "created_at": now})


@app.get("/api/extract/tasks")
async def extract_tasks_api(limit: int = Query(default=80, ge=1, le=200)):
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            items = [extraction_job_to_payload(row) for row in JobRepository(session).list_extraction_jobs(tenant_id, limit=limit)]
        return JSONResponse({"items": items})
    async with _EXTRACT_TASKS_LOCK:
        items = list(_EXTRACT_TASKS.values())
    items.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
    return JSONResponse({"items": items[:limit]})


@app.get("/api/extract/tasks/{task_id}")
async def extract_task_detail_api(task_id: str):
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            task = JobRepository(session).get_extraction_job(tenant_id, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            return JSONResponse(extraction_job_to_payload(task))
    async with _EXTRACT_TASKS_LOCK:
        task = _EXTRACT_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JSONResponse(task)


def _parse_fields(raw: str) -> list[str]:
    if not raw:
        return []
    cleaned = (
        raw.replace("\n", ",")
        .replace("，", ",")
        .replace("；", ",")
        .replace(";", ",")
        .replace("|", ",")
        .replace("、", ",")
    )
    items: list[str] = []
    seen = set()
    for token in cleaned.split(","):
        value = token.strip()
        if not value or value in seen:
            continue
        items.append(value)
        seen.add(value)
    return items


def _merge_targets(a: list[str], b: list[str]) -> list[str]:
    merged: list[str] = []
    seen = set()
    for item in a + b:
        if not item or item in seen:
            continue
        merged.append(item)
        seen.add(item)
    return merged


def _resolve_runtime_llm_settings(
    llm_base_url: str,
    llm_model: str,
    llm_api_key: str,
) -> tuple[str, str, str]:
    base = str(llm_base_url or "").strip()
    model = str(llm_model or "").strip()
    api_key = str(llm_api_key or "").strip()

    if base and model:
        return base, model, api_key

    try:
        stored = load_llm_settings(project_root=project_root)
        active = resolve_active_llm_config(stored)
    except Exception:
        active = {
            "llm_base_url": DEFAULT_LLM_BASE_URL,
            "llm_model": DEFAULT_LLM_MODEL,
            "llm_api_key": DEFAULT_LLM_API_KEY,
        }

    resolved_base = base or str(active.get("llm_base_url") or DEFAULT_LLM_BASE_URL).strip() or DEFAULT_LLM_BASE_URL
    resolved_model = model or str(active.get("llm_model") or DEFAULT_LLM_MODEL).strip() or DEFAULT_LLM_MODEL
    resolved_api_key = api_key or str(active.get("llm_api_key") or DEFAULT_LLM_API_KEY).strip()
    return resolved_base, resolved_model, resolved_api_key


def _should_fallback_to_pipeline(backend: str, err: str) -> bool:
    b = _normalize_model_version(backend)
    if b == "pipeline":
        return False
    if "vlm" not in b:
        return False
    e = (err or "").lower()
    return (
        "enginecore encountered an issue" in e
        or "enginedeaderror" in e
        or "500" in e
        or "internal server error" in e
        or "timeout" in e
    )


def _normalize_model_version(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return DEFAULT_MINERU_MODEL_VERSION
    lowered = text.lower()
    if "vlm" in lowered:
        return "vlm"
    if "pipeline" in lowered or "hybrid" in lowered:
        return "pipeline"
    return text


def _normalize_ocr_engine(raw: str) -> str:
    text = str(raw or "").strip().lower()
    if not text:
        return DEFAULT_OCR_ENGINE
    if text in {"mineru", "opendataloader", "qwen_vision", "excel"}:
        return text
    raise ValueError("ocr_engine 仅支持 mineru、opendataloader、qwen_vision 或 excel")


def _ocr_engine_label(engine: str) -> str:
    normalized = _normalize_ocr_engine(engine)
    if normalized == "excel":
        return "Excel 表格解析"
    if normalized == "qwen_vision":
        return "Qwen3.5-Plus 端到端"
    if normalized == "opendataloader":
        return "OpenDataLoader PDF"
    return "MinerU"


def _parse_lang_list(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return list(DEFAULT_MINERU_LANG_LIST)
    items: list[str] = []
    seen = set()
    for token in text.replace(";", ",").replace("；", ",").split(","):
        value = token.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        items.append(value)
    return items or list(DEFAULT_MINERU_LANG_LIST)


def _count_detected_hits(detected: Any) -> int:
    if not isinstance(detected, dict):
        return 0
    return sum(1 for value in detected.values() if _has_meaningful_value(value))


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _should_try_rotation_retry(hit_count: int, target_count: int, quality_score: int = 0) -> bool:
    # If OCR preview quality is poor, force rotation retry even when hit rate looks acceptable.
    if quality_score < 25:
        return True
    if target_count <= 0:
        return hit_count <= 0
    if target_count <= 3:
        return hit_count <= 0
    return (hit_count / max(1, target_count)) < 0.45


def _estimate_text_quality(text: Any) -> int:
    s = str(text or "")
    if not s:
        return -200
    sample = s[:2400]
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", sample))
    digits = len(re.findall(r"[0-9]", sample))
    # Math/symbol noise often dominates in wrong-orientation OCR.
    noise = len(re.findall(r"[∴≠≈≤≥√∑∫±÷×^{}\\$]", sample))
    garble = len(re.findall(r"(\\therefore|\\frac|\\neq|\\sum|\\int)", sample))
    lines = [x.strip() for x in sample.splitlines() if x.strip()]
    useful_lines = sum(1 for line in lines if len(re.findall(r"[A-Za-z\u4e00-\u9fff]", line)) >= 4)
    return letters + min(digits, 120) + useful_lines * 2 - noise * 5 - garble * 10


def _build_rotation_candidates(file_name: str, file_bytes: bytes) -> list[tuple[int, bytes]]:
    suffix = Path(file_name).suffix.lower()
    candidates: list[tuple[int, bytes]] = [(0, file_bytes)]
    if suffix == ".pdf":
        for angle in ROTATION_ANGLES[1:]:
            rotated = _rotate_pdf_bytes(file_bytes, angle)
            if rotated:
                candidates.append((angle, rotated))
        return candidates
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}:
        for angle in ROTATION_ANGLES[1:]:
            rotated = _rotate_image_bytes(file_bytes, angle, suffix=suffix)
            if rotated:
                candidates.append((angle, rotated))
    return candidates


def _build_history_preview_assets(
    *,
    file_name: str,
    original_file_bytes: bytes,
    selected_file_bytes: bytes | None,
    response_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}:
        return []
    if not isinstance(selected_file_bytes, (bytes, bytearray)) or not selected_file_bytes:
        return []
    rotation_selected_angle = int(response_payload.get("rotation_selected_angle") or response_payload.get("rotation_angle") or 0)
    osd_rotation_used = bool(response_payload.get("osd_rotation_used"))
    selected_bytes = bytes(selected_file_bytes)
    if selected_bytes == bytes(original_file_bytes) and rotation_selected_angle == 0 and not osd_rotation_used:
        return []
    return [
        {
            "path": f"preview/final_selected{suffix}",
            "content": selected_bytes,
        }
    ]


def _auto_rotate_pdf_with_osd(file_bytes: bytes) -> tuple[bytes, bool, str, list[int]]:
    if not file_bytes:
        return file_bytes, False, "empty_input", []
    if not shutil.which("tesseract") or not shutil.which("pdftoppm"):
        rotated, used, msg = _auto_rotate_pdf_with_ocrmypdf(file_bytes)
        return rotated, used, f"osd_tools_missing|fallback:{msg}", []

    try:
        page_angles, meta = _detect_pdf_page_rotations_with_tesseract(file_bytes)
        normalized = [angle if angle in (0, 90, 180, 270) else 0 for angle in page_angles]
        if len(normalized) == 0:
            return file_bytes, False, f"osd_no_pages:{meta}", normalized
        if all(angle == 0 for angle in normalized):
            return file_bytes, False, f"osd_no_rotation:{meta}", normalized
        rotated = _rotate_pdf_pages_by_angles(file_bytes, normalized)
        if rotated and rotated != file_bytes:
            changed = sum(1 for angle in normalized if angle != 0)
            summary = ",".join(str(x) for x in normalized[:16])
            if len(normalized) > 16:
                summary += ",..."
            return rotated, True, f"osd_rotated:changed={changed};angles={summary};{meta}", normalized
        return file_bytes, False, f"osd_no_effect:{meta}", normalized
    except Exception as exc:
        rotated, used, msg = _auto_rotate_pdf_with_ocrmypdf(file_bytes)
        return rotated, used, f"osd_exception:{str(exc)[:160]}|fallback:{msg}", []


def _auto_rotate_pdf_with_ocrmypdf(file_bytes: bytes) -> tuple[bytes, bool, str]:
    if not shutil.which("ocrmypdf"):
        return file_bytes, False, "ocrmypdf_not_found"
    try:
        with tempfile.TemporaryDirectory(prefix="carsem_osd_ocrmypdf_") as td:
            in_path = Path(td) / "input.pdf"
            out_path = Path(td) / "output.pdf"
            in_path.write_bytes(file_bytes)
            cmd = [
                "ocrmypdf",
                "--rotate-pages",
                "--skip-text",
                "--output-type",
                "pdf",
                "--quiet",
                str(in_path),
                str(out_path),
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
                check=False,
                text=True,
            )
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
                return file_bytes, False, f"ocrmypdf_failed:{proc.returncode}:{msg[:220] or 'unknown'}"
            if not out_path.is_file():
                return file_bytes, False, "ocrmypdf_no_output"
            out_bytes = out_path.read_bytes()
            if not out_bytes:
                return file_bytes, False, "ocrmypdf_empty_output"
            return out_bytes, out_bytes != file_bytes, "ocrmypdf_ok"
    except subprocess.TimeoutExpired:
        return file_bytes, False, "ocrmypdf_timeout"
    except Exception as exc:
        return file_bytes, False, f"ocrmypdf_exception:{str(exc)[:200]}"


def _detect_pdf_page_rotations_with_tesseract(file_bytes: bytes) -> tuple[list[int], str]:
    with tempfile.TemporaryDirectory(prefix="carsem_osd_detect_") as td:
        tmp_dir = Path(td)
        pdf_path = tmp_dir / "input.pdf"
        prefix = tmp_dir / "page"
        pdf_path.write_bytes(file_bytes)

        proc_pdf = subprocess.run(
            ["pdftoppm", "-r", "170", "-png", str(pdf_path), str(prefix)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=240,
            check=False,
            text=True,
        )
        if proc_pdf.returncode != 0:
            msg = (proc_pdf.stderr or proc_pdf.stdout or "").strip().replace("\n", " ")
            raise RuntimeError(f"pdftoppm_failed:{proc_pdf.returncode}:{msg[:220]}")

        png_files = sorted(tmp_dir.glob("page-*.png"), key=_extract_page_number_from_png)
        if not png_files:
            raise RuntimeError("pdftoppm_no_images")

        rotations: list[int] = []
        low_conf = 0
        parse_err = 0
        for image_path in png_files:
            proc_osd = subprocess.run(
                ["tesseract", str(image_path), "stdout", "--psm", "0", "-l", "osd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
                text=True,
            )
            output = f"{proc_osd.stdout or ''}\n{proc_osd.stderr or ''}"
            angle, conf = _parse_tesseract_osd_output(output)
            if angle not in (0, 90, 180, 270):
                angle = 0
            if conf is not None and conf < 3.0:
                angle = 0
                low_conf += 1
            if "Rotate:" not in output:
                parse_err += 1
            rotations.append(angle)

        meta = f"pages={len(rotations)},low_conf={low_conf},parse_err={parse_err}"
        return rotations, meta


def _parse_tesseract_osd_output(output: str) -> tuple[int, float | None]:
    text = str(output or "")
    m_angle = re.search(r"Rotate:\s*([0-9]+)", text, flags=re.IGNORECASE)
    m_conf = re.search(r"Orientation confidence:\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
    angle = int(m_angle.group(1)) % 360 if m_angle else 0
    conf = float(m_conf.group(1)) if m_conf else None
    return angle, conf


def _extract_page_number_from_png(path: Path) -> int:
    m = re.search(r"-(\d+)\.png$", path.name)
    if not m:
        return 10**9
    try:
        return int(m.group(1))
    except Exception:
        return 10**9


def _rotate_pdf_pages_by_angles(file_bytes: bytes, page_angles: list[int]) -> bytes | None:
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        return None
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        for idx, page in enumerate(reader.pages):
            angle = page_angles[idx] if idx < len(page_angles) else 0
            if angle in (90, 180, 270):
                page = page.rotate(angle)
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        return None


def _rotate_pdf_bytes(file_bytes: bytes, angle: int) -> bytes | None:
    if angle % 360 == 0:
        return file_bytes
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        return None
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page.rotate(angle))
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        return None


def _rotate_image_bytes(file_bytes: bytes, angle: int, suffix: str) -> bytes | None:
    if angle % 360 == 0:
        return file_bytes
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        source = Image.open(io.BytesIO(file_bytes))
        rotated = source.rotate(-angle, expand=True)
        target_format = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".bmp": "BMP",
            ".gif": "GIF",
            ".tiff": "TIFF",
        }.get(suffix.lower(), (source.format or "PNG"))
        out = io.BytesIO()
        save_kwargs = {"format": target_format}
        if target_format == "JPEG":
            save_kwargs["quality"] = 95
        rotated.save(out, **save_kwargs)
        return out.getvalue()
    except Exception:
        return None


@app.get("/api/history")
async def history_api(limit: int = Query(default=50, ge=1, le=200)):
    try:
        items = list_history_records(project_root=project_root, limit=limit)
    except Exception as exc:
        return JSONResponse(
            {
                "items": [],
                "error": f"list_history_failed: {str(exc)[:180]}",
            },
            status_code=200,
        )
    return {"items": items}


@app.post("/api/history/{record_id}/submission-draft")
async def generate_submission_draft_api(record_id: str):
    detail, response_payload = _get_history_response_payload(record_id)
    template = _resolve_template_for_history(detail)
    try:
        draft = _generate_submission_draft_with_llm(response_payload=response_payload, template=template)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成报关草稿失败: {str(exc)[:240]}")
    updated_response = attach_submission_draft(response_payload, draft)
    update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
    return JSONResponse({"record_id": record_id, "submission": draft})


@app.put("/api/history/{record_id}/submission-draft")
async def save_submission_draft_api(record_id: str, payload: dict = Body(...)):
    _, response_payload = _get_history_response_payload(record_id)
    existing = response_payload.get("submission")
    merged = merge_submission_draft(existing if isinstance(existing, dict) else {}, payload if isinstance(payload, dict) else {})
    validation = validate_submission_draft(merged)
    merged["meta"]["required_missing"] = validation["required_missing"]
    updated_response = attach_submission_draft(response_payload, merged)
    update_history_record_response(project_root=project_root, record_id=record_id, response_payload=updated_response)
    return JSONResponse({"record_id": record_id, "submission": merged, "validation": validation})


@app.post("/api/history/{record_id}/submit-customs")
async def submit_customs_api(record_id: str):
    _, response_payload = _get_history_response_payload(record_id)
    draft = response_payload.get("submission")
    if not isinstance(draft, dict):
        raise HTTPException(status_code=400, detail="请先生成填报草稿")
    validation = validate_submission_draft(draft)
    if not validation["ok"]:
        return JSONResponse(
            {
                "detail": validation["message"],
                "required_missing": validation["required_missing"],
            },
            status_code=400,
        )

    try:
        settings = load_llm_settings(project_root=project_root)
    except Exception:
        settings = {}
    customs_submit_mode = str(settings.get("customs_submit_mode") or "http").strip().lower() if isinstance(settings, dict) else "http"

    now = _utc_now_iso()
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            job = JobRepository(session).create_customs_submit_job(
                tenant_id=tenant_id,
                submit_engine=customs_submit_mode,
            )
            task_id = job.id.hex
    else:
        task_id = uuid.uuid4().hex
        async with _CUSTOMS_SUBMIT_TASKS_LOCK:
            _CUSTOMS_SUBMIT_TASKS[task_id] = {
                "id": task_id,
                "record_id": record_id,
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待提交",
                "error": "",
                "created_at": now,
                "updated_at": now,
                "submit_engine": customs_submit_mode,
                "result": None,
            }
            _prune_customs_submit_tasks_unlocked()

    asyncio.create_task(_run_customs_submit_task(task_id, record_id, validation["draft"]))

    return JSONResponse({
        "task_id": task_id,
        "status": "queued",
        "created_at": now,
        "mode": customs_submit_mode,
    })

@app.get("/api/customs-submit/tasks")
async def customs_submit_tasks_api(limit: int = Query(default=80, ge=1, le=200)):
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            items = [customs_job_to_payload(row) for row in JobRepository(session).list_customs_submit_jobs(tenant_id, limit=limit)]
        return JSONResponse({"items": items})
    async with _CUSTOMS_SUBMIT_TASKS_LOCK:
        items = list(_CUSTOMS_SUBMIT_TASKS.values())
    items.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
    return JSONResponse({"items": items[:limit]})


@app.get("/api/customs-submit/tasks/{task_id}")
async def customs_submit_task_detail_api(task_id: str):
    if _database_jobs_enabled():
        with _tenant_repository_session() as (session, tenant_id):
            task = JobRepository(session).get_customs_submit_job(tenant_id, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            return JSONResponse(customs_job_to_payload(task))
    async with _CUSTOMS_SUBMIT_TASKS_LOCK:
        task = _CUSTOMS_SUBMIT_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JSONResponse(task)


@app.delete("/api/history/{record_id}")
async def history_delete_api(record_id: str):
    deleted = delete_history_record(project_root=project_root, record_id=record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return {"ok": True, "id": record_id}


@app.get("/api/history/{record_id}")
async def history_detail_api(record_id: str):
    detail = load_history_record(project_root=project_root, record_id=record_id)
    if not detail:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return JSONResponse(detail)


@app.get("/api/history/{record_id}/download")
async def history_download_api(record_id: str):
    zip_path = get_history_zip_path(project_root=project_root, record_id=record_id)
    if not zip_path:
        raise HTTPException(status_code=404, detail="压缩包不存在")
    filename = f"{record_id}.zip"
    return FileResponse(path=zip_path, media_type="application/zip", filename=filename)


@app.get("/api/history/{record_id}/asset/{file_path:path}")
async def history_asset_api(record_id: str, file_path: str):
    path = get_history_asset_path(project_root=project_root, record_id=record_id, file_path=file_path)
    if not path:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path=path)


@app.get("/api/history/{record_id}/text/{file_path:path}")
async def history_text_api(record_id: str, file_path: str):
    data = read_history_text_file(project_root=project_root, record_id=record_id, file_path=file_path)
    if not data:
        raise HTTPException(status_code=404, detail="文本文件不存在或不可读取")
    return JSONResponse(data)


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            "<h3>前端尚未构建。请先运行: cd frontend && npm install && npm run build</h3>",
            status_code=200,
        )
    return FileResponse(index_file)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    if not dist_dir.exists():
        raise HTTPException(status_code=404, detail="前端资源不存在")
    requested = (dist_dir / full_path).resolve()
    if requested.is_file() and str(requested).startswith(str(dist_dir.resolve())):
        return FileResponse(requested)
    index_file = dist_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="前端入口不存在")
