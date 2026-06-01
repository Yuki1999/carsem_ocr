from fastapi.testclient import TestClient

from app.api.app import app


def test_readiness_endpoint_reports_basic_checks_without_db_mode():
    response = TestClient(app).get("/api/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] in {"disabled", "ok"}
    assert payload["checks"]["asset_storage"] == "ok"
