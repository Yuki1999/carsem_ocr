from fastapi.testclient import TestClient

from app.api.agent import AGENT_ENDPOINT_SCOPES, router
from app.api.app import app


def test_agent_router_exposes_stable_machine_api_paths():
    paths = {route.path for route in router.routes}

    assert "/extractions" in paths
    assert "/extractions/{job_id}" in paths
    assert "/templates" in paths
    assert "/history" in paths
    assert "/history/{record_id}" in paths


def test_agent_endpoint_scopes_cover_initial_skill_surface():
    assert AGENT_ENDPOINT_SCOPES["POST /extractions"] == {"documents:extract"}
    assert AGENT_ENDPOINT_SCOPES["GET /templates"] == {"templates:read"}
    assert AGENT_ENDPOINT_SCOPES["GET /history"] == {"history:read"}


def test_agent_api_requires_bearer_api_key():
    response = TestClient(app).get("/api/v1/agent/templates")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer API key"
