import uuid

from app.db.models import CustomsSubmitJob
from app.repositories.jobs import build_request_hash, customs_job_to_payload


def test_build_request_hash_is_stable_for_equivalent_payloads():
    first = build_request_hash({"b": 2, "a": 1})
    second = build_request_hash({"a": 1, "b": 2})

    assert first == second
    assert len(first) == 64


def test_customs_job_to_payload_uses_stable_status_shape():
    job = CustomsSubmitJob(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        status="queued",
        submit_engine="playwright",
        result_payload={},
        error="",
    )

    payload = customs_job_to_payload(job)

    assert payload["id"] == "00000000-0000-0000-0000-000000000001"
    assert payload["status"] == "queued"
    assert payload["submit_engine"] == "playwright"
