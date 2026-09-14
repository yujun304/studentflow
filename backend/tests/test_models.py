import app.models  # noqa: F401
from app.core.database import Base


def test_mvp_tables_are_registered():
    expected = {
        "users",
        "departments",
        "terms",
        "events",
        "tasks",
        "submissions",
        "submission_versions",
        "files",
        "notices",
        "notice_applications",
        "schedule_change_requests",
        "teams",
        "team_members",
        "attendance",
        "meeting_records",
        "meeting_attendees",
        "comments",
        "community_event_plans",
        "quick_memos",
        "reminders",
        "saved_items",
        "notifications",
        "push_subscriptions",
        "decision_cards",
        "handover_guides",
        "event_run_items",
        "school_maps",
        "map_assignments",
        "event_completion_records",
    }
    assert expected <= set(Base.metadata.tables)
