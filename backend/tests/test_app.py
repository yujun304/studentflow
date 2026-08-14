from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoint_requires_login():
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_csrf_endpoint_sets_cookie():
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"]
    assert "studentflow_csrf" in response.cookies
