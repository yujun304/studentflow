import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(str, enum.Enum):
    MEMBER = "MEMBER"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    EXECUTIVE_BOARD = "EXECUTIVE_BOARD"
    TEACHER = "TEACHER"


class EventType(str, enum.Enum):
    EVENT = "EVENT"
    CAMPAIGN = "CAMPAIGN"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    REJECTED = "REJECTED"


class TaskType(str, enum.Enum):
    SIMPLE = "SIMPLE"
    SUBMISSION = "SUBMISSION"
    TEAM_FORMATION = "TEAM_FORMATION"


class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NoticeType(str, enum.Enum):
    GENERAL = "GENERAL"
    EVENT = "EVENT"
    SURVEY = "SURVEY"
    FIRST_COME = "FIRST_COME"


class ApplicationStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    WAITING = "WAITING"
    CANCELLED = "CANCELLED"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AttendanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    LEFT_EARLY = "LEFT_EARLY"


class DecisionStatus(str, enum.Enum):
    OPEN = "OPEN"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class RunItemStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ISSUE = "ISSUE"


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimeMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Department(UUIDMixin, TimeMixin, Base):
    __tablename__ = "departments"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Term(UUIDMixin, TimeMixin, Base):
    __tablename__ = "terms"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class User(UUIDMixin, TimeMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("grade IS NULL OR grade BETWEEN 1 AND 3", name="ck_users_grade"),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), default=Role.MEMBER)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    grade: Mapped[int | None] = mapped_column(Integer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1)


class RefreshSession(UUIDMixin, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(UUIDMixin, TimeMixin, Base):
    __tablename__ = "events"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    starts_at: Mapped[time | None] = mapped_column(Time)
    ends_at: Mapped[time | None] = mapped_column(Time)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    manager_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")


class EventParticipant(UUIDMixin, Base):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class Task(UUIDMixin, TimeMixin, Base):
    __tablename__ = "tasks"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[TaskType] = mapped_column(Enum(TaskType, name="task_type"))
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), default=TaskStatus.TODO
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class TaskAssignee(UUIDMixin, Base):
    __tablename__ = "task_assignees"
    __table_args__ = (UniqueConstraint("task_id", "user_id"),)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class Submission(UUIDMixin, TimeMixin, Base):
    __tablename__ = "submissions"
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), index=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class SubmissionVersion(UUIDMixin, Base):
    __tablename__ = "submission_versions"
    __table_args__ = (UniqueConstraint("submission_id", "version"),)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoredFile(UUIDMixin, Base):
    __tablename__ = "files"
    submission_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("submission_versions.id"), index=True
    )
    meeting_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("meeting_records.id"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(150))
    size: Mapped[int] = mapped_column(BigInteger)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notice(UUIDMixin, TimeMixin, Base):
    __tablename__ = "notices"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[NoticeType] = mapped_column(Enum(NoticeType, name="notice_type"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity: Mapped[int | None] = mapped_column(Integer)
    waiting_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class NoticeRecipient(UUIDMixin, Base):
    __tablename__ = "notice_recipients"
    __table_args__ = (UniqueConstraint("notice_id", "user_id"),)
    notice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notices.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NoticeApplication(UUIDMixin, Base):
    __tablename__ = "notice_applications"
    __table_args__ = (UniqueConstraint("notice_id", "user_id"),)
    notice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notices.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status")
    )
    sequence: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScheduleChangeRequest(UUIDMixin, TimeMixin, Base):
    __tablename__ = "schedule_change_requests"
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    requested_date: Mapped[date] = mapped_column(Date)
    requested_start: Mapped[time | None] = mapped_column(Time)
    requested_end: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus, name="request_status"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Team(UUIDMixin, TimeMixin, Base):
    __tablename__ = "teams"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), index=True)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("submissions.id"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    role_description: Mapped[str | None] = mapped_column(String(200))
    leader_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    schedule_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class TeamMember(UUIDMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class Attendance(UUIDMixin, TimeMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"), default=AttendanceStatus.PENDING
    )
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class MeetingRecord(UUIDMixin, TimeMixin, Base):
    __tablename__ = "meeting_records"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    held_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    decisions: Mapped[str | None] = mapped_column(Text)
    next_actions: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class MeetingAttendee(UUIDMixin, Base):
    __tablename__ = "meeting_attendees"
    __table_args__ = (UniqueConstraint("meeting_record_id", "user_id"),)
    meeting_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meeting_records.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class Comment(UUIDMixin, TimeMixin, Base):
    __tablename__ = "comments"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comments.id"))
    content: Mapped[str] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuickMemo(UUIDMixin, TimeMixin, Base):
    __tablename__ = "quick_memos"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    converted_type: Mapped[str | None] = mapped_column(String(50))
    converted_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class Reminder(UUIDMixin, TimeMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("user_id", "source_type", "source_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    category: Mapped[str] = mapped_column(String(40), default="PERSONAL", index=True)
    color: Mapped[str] = mapped_column(String(20), default="#356ae6")
    source_type: Mapped[str | None] = mapped_column(String(40), index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)


class SavedItem(UUIDMixin, Base):
    __tablename__ = "saved_items"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(UUIDMixin, Base):
    __tablename__ = "notifications"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PushSubscription(UUIDMixin, TimeMixin, Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "endpoint"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    p256dh: Mapped[str] = mapped_column(Text)
    auth: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(String(300))


class DecisionCard(UUIDMixin, TimeMixin, Base):
    __tablename__ = "decision_cards"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    meeting_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("meeting_records.id", ondelete="SET NULL"), index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), unique=True
    )
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus, name="decision_status"), default=DecisionStatus.OPEN
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HandoverGuide(UUIDMixin, TimeMixin, Base):
    __tablename__ = "handover_guides"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    what_worked: Mapped[str | None] = mapped_column(Text)
    pitfalls: Mapped[str | None] = mapped_column(Text)
    checklist: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class EventRunItem(UUIDMixin, TimeMixin, Base):
    __tablename__ = "event_run_items"
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    planned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location_label: Mapped[str | None] = mapped_column(String(200))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[RunItemStatus] = mapped_column(
        Enum(RunItemStatus, name="run_item_status"), default=RunItemStatus.PLANNED
    )
    note: Mapped[str | None] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class SchoolMap(UUIDMixin, TimeMixin, Base):
    __tablename__ = "school_maps"
    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id"), unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class MapAssignment(UUIDMixin, TimeMixin, Base):
    __tablename__ = "map_assignments"
    __table_args__ = (
        CheckConstraint("x_ratio >= 0 AND x_ratio <= 1", name="ck_map_assignment_x"),
        CheckConstraint("y_ratio >= 0 AND y_ratio <= 1", name="ck_map_assignment_y"),
    )
    map_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school_maps.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    activity: Mapped[str] = mapped_column(String(300))
    x_ratio: Mapped[float] = mapped_column(Float)
    y_ratio: Mapped[float] = mapped_column(Float)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
