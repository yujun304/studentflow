from app.main import api


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
        "/operations/completion-records",
        "/operations/events/{event_id}/completion",
    }
    assert expected <= set(paths)
