from __future__ import annotations

from typing import Any

from .customs_browser import _flatten_submission_payload


def submit_to_customs_site_with_playwright(
    draft: dict[str, Any],
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """使用 Playwright 登录报关系统并提交一份草稿数据。"""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"playwright_unavailable: {exc}") from exc

    credentials = credentials if isinstance(credentials, dict) else {}
    site_url = str(credentials.get("site_url") or "https://vatest.carsem.com.cn").rstrip("/")
    username = str(credentials.get("username") or "vip@dianxin").strip()
    password = str(credentials.get("password") or "xinpwd@@@2026").strip()
    if not site_url or not username or not password:
        raise RuntimeError("缺少报关系统登录凭据")

    dialogs: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        # 网站在保存或提交后可能通过浏览器弹窗返回结果，因此统一拦截并记录。
        page.on("dialog", lambda dialog: _accept_dialog(dialogs, dialog))
        try:
            # 先完成登录，并等待页面真正跳离登录地址。
            page.goto(f"{site_url}/Home/Login", wait_until="domcontentloaded", timeout=30000)
            page.locator("#username").fill(username)
            page.locator("#password").fill(password)
            page.locator("button[type='submit']").click()
            page.wait_for_function("() => !window.location.pathname.toLowerCase().includes('/home/login')", timeout=30000)

            # 登录成功后，表单页会预生成报关单号；拿不到通常意味着页面结构或流程变了。
            page.wait_for_selector("#dataForm", timeout=30000)
            page.wait_for_function(
                "() => document.querySelector('#declarationNo') && document.querySelector('#declarationNo').value !== ''",
                timeout=30000,
            )
            declaration_no = str(page.locator("#declarationNo").input_value() or "").strip()
            if not declaration_no:
                raise RuntimeError("page_structure_changed: 未获取到报关单号")

            _fill_submission_form(page, draft, declaration_no)
            _submit_form_with_page_actions(page)
            _wait_for_submit_feedback(page)
            _raise_if_submit_feedback_indicates_failure(dialogs)

            return {
                "ok": True,
                "message": _resolve_submit_message(dialogs),
                "declaration_no": declaration_no,
                "site_url": site_url,
                "submit_engine": "playwright",
            }
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"page_structure_changed: {exc}") from exc
        finally:
            context.close()
            browser.close()


def _accept_dialog(dialogs: list[str], dialog: Any) -> None:
    """记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。"""
    try:
        dialogs.append(str(dialog.message or "").strip())
    finally:
        dialog.accept()


def _submit_form_with_page_actions(page: Any) -> None:
    """优先点击常见的保存/提交按钮，找不到时再退回到原生表单提交。"""
    selectors = (
        "#btnSave",
        "#btnSubmit",
        "#saveButton",
        "#submitButton",
        "#dataForm button[type='submit']",
        "button[type='submit']",
        "button:has-text('保存')",
        "button:has-text('提交')",
        "input[type='submit']",
        "input[value='保存']",
        "input[value='提交']",
    )
    for selector in selectors:
        locator = _first_locator(page.locator(selector))
        if _locator_count(locator) > 0:
            locator.click()
            return

    form = _first_locator(page.locator("#dataForm"))
    if _locator_count(form) == 0:
        raise RuntimeError("page_structure_changed: 未找到报关表单")
    form.evaluate("(form) => { if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); } }")


def _wait_for_submit_feedback(page: Any) -> None:
    """尽量等待提交后的页面反馈完成，避免立即读取结果导致误判。"""
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
        return
    except Exception:
        pass
    try:
        page.wait_for_timeout(1500)
    except Exception:
        pass


def _raise_if_submit_feedback_indicates_failure(dialogs: list[str]) -> None:
    """根据最近一次弹窗消息判断网站是否明确返回了失败。"""
    if not dialogs:
        return
    latest = str(dialogs[-1] or "").strip()
    lowered = latest.lower()
    failure_signals = ("失败", "错误", "异常", "不能为空", "未填写", "invalid", "error", "failed")
    if any(signal in latest for signal in failure_signals[:4]) or any(signal in lowered for signal in failure_signals[4:]):
        raise RuntimeError(f"submission_rejected: {latest or '网站返回失败'}")


def _resolve_submit_message(dialogs: list[str]) -> str:
    """优先返回网站给出的提示语，没有弹窗时使用默认成功消息。"""
    if dialogs:
        message = str(dialogs[-1] or "").strip()
        if message:
            return message
    return "数据保存成功"


def _first_locator(locator: Any) -> Any:
    """兼容 Playwright Locator 与其 `.first` 属性的两种用法。"""
    first = getattr(locator, "first", None)
    if first is None:
        return locator
    return first() if callable(first) else first


def _locator_count(locator: Any) -> int:
    """安全获取 locator 数量；页面结构变化时返回 0 而不是直接抛错。"""
    try:
        count = locator.count()
    except Exception:
        return 0
    try:
        return int(count)
    except Exception:
        return 0


def _fill_submission_form(page: Any, draft: dict[str, Any], declaration_no: str) -> None:
    """将草稿数据拆成表头和明细，再按页面控件结构逐项填充。"""
    pairs = _flatten_submission_payload(draft, declaration_no)
    values = _group_submission_payload(pairs)
    header = values["header"]
    details = values["details"]

    # 报关单号通常由页面预生成，这里用 evaluate 直接回填，避免只读或前端绑定限制。
    page.locator("#declarationNo").evaluate("(el, value) => { el.value = value; }", header.get("DeclarationNo", ""))
    for field_name, value in header.items():
        if field_name == "DeclarationNo":
            continue
        locator = page.locator(f"#dataForm input[name='{field_name}']").first
        locator.fill(value)

    if details:
        # 先补齐明细行数量，再逐行写入，保持与页面的动态增行逻辑一致。
        for _ in range(len(details)):
            page.locator("#addDetailRow").click()
        rows = page.locator("#detailsContainer .detail-row")
        for idx, item in enumerate(details):
            row = rows.nth(idx)
            for field_name, value in item.items():
                row.locator(f"input[name='{field_name}']").fill(value)


def _group_submission_payload(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """按字段类型把扁平键值对重组为表头数据和明细行数据。"""
    header_fields = {
        "DeclarationNo",
        "MainBLNo",
        "SubBLNo",
        "CustomerName",
        "TradeType",
        "OriginCountry",
        "InvoiceNo",
        "Quantity",
        "GrossWeight",
        "NetWeight",
        "TotalSheets",
        "TotalQuantity",
        "GoodQuantity",
        "TotalPrice",
    }
    detail_fields = {"ItemCode", "ItemOrigin", "ItemQuantity", "ItemGoodQuantity", "ItemPrice", "ItemUnitPrice"}

    header: dict[str, str] = {}
    detail_rows: list[dict[str, str]] = []
    current_detail: dict[str, str] = {}
    for key, value in pairs:
        if key in header_fields:
            header[key] = value
            continue
        if key in detail_fields:
            current_detail[key] = value
            # 一组明细字段收齐后视为一行，按出现顺序写回页面。
            if len(current_detail) == len(detail_fields):
                detail_rows.append(current_detail)
                current_detail = {}
    if current_detail:
        detail_rows.append(current_detail)
    return {"header": header, "details": detail_rows}
