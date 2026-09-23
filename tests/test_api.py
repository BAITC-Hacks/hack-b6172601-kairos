"""Fast tests that need no API key. They prove the wiring, not the model."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_registered_tools():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tools"] == []


def test_tools_endpoint_returns_schemas():
    response = client.get("/api/tools")
    assert response.status_code == 200
    names = [t["function"]["name"] for t in response.json()["tools"]]
    assert names == []


def test_empty_question_is_rejected():
    response = client.post("/api/ask", json={"question": ""})
    assert response.status_code == 422
    assert response.json()["ok"] is False


def test_static_index_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Money Graph" in response.text
    assert 'id="graph-canvas"' in response.text
