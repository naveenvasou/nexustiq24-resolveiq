"""
Integration tests for FastAPI REST Endpoints.
"""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_root_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "ResolveIQ" in res.text


def test_health_check():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["track"] == 4
    assert data["total_articles"] == 8


def test_list_scenarios():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 5
    modes = [s["expected_mode"] for s in scenarios]
    assert "RESOLUTION_DRAFT" in modes
    assert "HANDOVER_SUMMARY" in modes


def test_resolve_endpoint():
    payload = {"conversation_id": "CONV-001", "account_id": "ACC-1001"}
    res = client.post("/api/resolve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["resolution"]["mode"] == "RESOLUTION_DRAFT"
    assert data["resolution"]["validation"]["is_valid"] is True


def test_validate_endpoint_tampering():
    payload = {
        "account_id": "ACC-1001",
        "draft_text": "Hello Sarah, your Fiber 500 has an unexpected fee of $777.00."
    }
    res = client.post("/api/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["verdict"] == "REJECTED"
