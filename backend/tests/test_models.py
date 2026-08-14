from app.core.database import Base
import app.models  # noqa: F401


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
    }
    assert expected <= set(Base.metadata.tables)
