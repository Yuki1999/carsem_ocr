from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CustomsSubmitJob, ExtractionJob


def build_request_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_extraction_job(
        self,
        *,
        tenant_id: str,
        request_payload: dict[str, Any],
        idempotency_key: str = "",
    ) -> ExtractionJob:
        request_hash = build_request_hash(request_payload)
        tenant_uuid = _tenant_uuid(tenant_id)
        if idempotency_key:
            existing = self.session.execute(
                select(ExtractionJob).where(
                    ExtractionJob.tenant_id == tenant_uuid,
                    ExtractionJob.idempotency_key == idempotency_key,
                    ExtractionJob.request_hash == request_hash,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
        job = ExtractionJob(
            tenant_id=tenant_uuid,
            status="queued",
            stage="queued",
            progress=0,
            message="等待调度",
            request_payload=request_payload,
            result_payload={},
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_extraction_job(self, tenant_id: str, job_id: str) -> ExtractionJob | None:
        return self.session.execute(
            select(ExtractionJob).where(ExtractionJob.tenant_id == _tenant_uuid(tenant_id), ExtractionJob.id == uuid.UUID(job_id))
        ).scalar_one_or_none()

    def update_extraction_job(self, tenant_id: str, job_id: str, updates: dict[str, Any]) -> ExtractionJob | None:
        job = self.get_extraction_job(tenant_id, job_id)
        if job is None:
            return None
        _apply_job_updates(job, updates)
        self.session.flush()
        return job

    def list_extraction_jobs(self, tenant_id: str, limit: int = 80) -> list[ExtractionJob]:
        return list(
            self.session.execute(
                select(ExtractionJob)
                .where(ExtractionJob.tenant_id == _tenant_uuid(tenant_id))
                .order_by(ExtractionJob.updated_at.desc(), ExtractionJob.created_at.desc())
                .limit(max(1, min(limit, 200)))
            ).scalars()
        )

    def create_customs_submit_job(self, *, tenant_id: str, submit_engine: str, draft_id: str | None = None) -> CustomsSubmitJob:
        job = CustomsSubmitJob(
            tenant_id=_tenant_uuid(tenant_id),
            draft_id=uuid.UUID(draft_id) if draft_id else None,
            status="queued",
            submit_engine=submit_engine,
            result_payload={},
            error="",
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_customs_submit_job(self, tenant_id: str, job_id: str) -> CustomsSubmitJob | None:
        return self.session.execute(
            select(CustomsSubmitJob).where(CustomsSubmitJob.tenant_id == _tenant_uuid(tenant_id), CustomsSubmitJob.id == uuid.UUID(job_id))
        ).scalar_one_or_none()

    def update_customs_submit_job(self, tenant_id: str, job_id: str, updates: dict[str, Any]) -> CustomsSubmitJob | None:
        job = self.get_customs_submit_job(tenant_id, job_id)
        if job is None:
            return None
        if "status" in updates:
            job.status = str(updates["status"] or "")
        if "submit_engine" in updates:
            job.submit_engine = str(updates["submit_engine"] or "")
        if "result" in updates:
            job.result_payload = updates["result"] if isinstance(updates["result"], dict) else {}
        if "result_payload" in updates:
            job.result_payload = updates["result_payload"] if isinstance(updates["result_payload"], dict) else {}
        if "error" in updates:
            job.error = str(updates["error"] or "")
        self.session.flush()
        return job

    def list_customs_submit_jobs(self, tenant_id: str, limit: int = 80) -> list[CustomsSubmitJob]:
        return list(
            self.session.execute(
                select(CustomsSubmitJob)
                .where(CustomsSubmitJob.tenant_id == _tenant_uuid(tenant_id))
                .order_by(CustomsSubmitJob.updated_at.desc(), CustomsSubmitJob.created_at.desc())
                .limit(max(1, min(limit, 200)))
            ).scalars()
        )


def extraction_job_to_payload(job: ExtractionJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "updated_at": job.updated_at.isoformat() if job.updated_at else "",
        "result": job.result_payload,
    }


def customs_job_to_payload(job: CustomsSubmitJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "status": job.status,
        "stage": job.status,
        "progress": 100 if job.status in {"succeeded", "failed"} else 0,
        "message": "",
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "updated_at": job.updated_at.isoformat() if job.updated_at else "",
        "submit_engine": job.submit_engine,
        "result": job.result_payload,
    }


def _apply_job_updates(job: ExtractionJob, updates: dict[str, Any]) -> None:
    if "status" in updates:
        job.status = str(updates["status"] or "")
    if "stage" in updates:
        job.stage = str(updates["stage"] or "")
    if "progress" in updates:
        job.progress = max(0, min(100, int(updates["progress"] or 0)))
    if "message" in updates:
        job.message = str(updates["message"] or "")
    if "error" in updates:
        job.error = str(updates["error"] or "")
    if "result" in updates:
        job.result_payload = updates["result"] if isinstance(updates["result"], dict) else {}
    if "result_payload" in updates:
        job.result_payload = updates["result_payload"] if isinstance(updates["result_payload"], dict) else {}


def _tenant_uuid(tenant_id: str) -> uuid.UUID:
    return uuid.UUID(str(tenant_id))
