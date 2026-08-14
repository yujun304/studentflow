from fastapi.testclient import TestClient

from app.core.security import current_user
from app.main import api, app
from app.models.entities import Role, User


def fake_user() -> User:
    import uuid

    return User(
        id=uuid.uuid4(),
        email="teacher@example.com",
        name="선생님",
        password_hash="unused",
        role=Role.TEACHER,
        term_id=uuid.uuid4(),
        is_active=True,
    )


def test_followup_contracts_are_in_openapi():
    paths = api.openapi()["paths"]
    expected = {
        "/teams",
        "/events/{event_id}/attendance",
        "/meeting-records",
        "/comments",
        "/memos",
        "/reminders",
        "/notifications",
        "/archive/terms",
        "/audit-logs",
        "/operations/decisions",
        "/operations/handovers",
        "/operations/maps",
    }
    assert expected <= set(paths)


def test_pending_contract_returns_clear_501():
    api.dependency_overrides[current_user] = fake_user
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/comments",
                params={"target_type": "task", "target_id": "00000000-0000-0000-0000-000000000001"},
            )
        assert response.status_code == 501
        assert response.json()["code"] == "feature_not_ready"
    finally:
        api.dependency_overrides.clear()
