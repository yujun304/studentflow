import uuid
from datetime import date, datetime, time
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.entities import (
    AttendanceStatus,
    DecisionStatus,
    EventType,
    NoticeType,
    RequestStatus,
    Role,
    RunItemStatus,
    SubmissionStatus,
    TaskStatus,
    TaskType,
)

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class LoginIn(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role: Role
    department_id: uuid.UUID | None
    term_id: uuid.UUID
    grade: int | None
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    role: Role = Role.MEMBER
    department_id: uuid.UUID | None = None
    term_id: uuid.UUID
    grade: int | None = Field(default=None, ge=1, le=3)


class UserUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None
    department_id: uuid.UUID | None = None
    grade: int | None = Field(default=None, ge=1, le=3)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class TermIn(BaseModel):
    name: str
    starts_on: date
    ends_on: date
    is_current: bool = False


class EventIn(BaseModel):
    title: str
    type: EventType
    description: str | None = None
    location: str | None = None
    event_date: date
    starts_at: time | None = None
    ends_at: time | None = None
    department_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] = Field(default_factory=list)


class EventOut(ORMModel):
    id: uuid.UUID
    title: str
    type: EventType
    description: str | None
    location: str | None
    event_date: date
    starts_at: time | None
    ends_at: time | None
    status: str
    manager_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskIn(BaseModel):
    title: str
    description: str | None = None
    type: TaskType = TaskType.SIMPLE
    event_id: uuid.UUID | None = None
    due_at: datetime | None = None
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None
    type: TaskType
    status: TaskStatus
    event_id: uuid.UUID | None
    due_at: datetime | None
    assigned_to_me: bool = False
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)
    can_edit: bool = False


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    type: TaskType | None = None
    event_id: uuid.UUID | None = None
    due_at: datetime | None = None
    assignee_ids: list[uuid.UUID] | None = None


class StatusIn(BaseModel):
    status: TaskStatus


class SubmissionIn(BaseModel):
    content: str | None = None


class ReviewIn(BaseModel):
    status: SubmissionStatus
    reason: str | None = None


class SubmissionFileOut(ORMModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size: int


class TeamDraftIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    role_description: str | None = Field(default=None, max_length=200)
    leader_id: uuid.UUID | None = None
    member_ids: list[uuid.UUID] = Field(min_length=1)
    schedule_at: datetime


class TeamReviewOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    role_description: str | None
    leader_id: uuid.UUID | None
    leader_name: str | None
    member_ids: list[uuid.UUID]
    member_names: list[str]
    schedule_at: datetime


class TeamFormationIn(BaseModel):
    content: str | None = None
    teams: list[TeamDraftIn] = Field(min_length=1)


class SubmissionReviewOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    submitted_by: uuid.UUID
    submitted_by_name: str
    status: SubmissionStatus
    version_id: uuid.UUID
    version: int
    content: str | None
    submitted_at: datetime
    files: list[SubmissionFileOut] = Field(default_factory=list)
    teams: list[TeamReviewOut] = Field(default_factory=list)


class NoticeIn(BaseModel):
    title: str
    content: str
    type: NoticeType = NoticeType.GENERAL
    pinned: bool = False
    capacity: int | None = Field(default=None, ge=1)
    waiting_enabled: bool = False
    recipient_ids: list[uuid.UUID] = Field(default_factory=list)


class NoticeOut(ORMModel):
    id: uuid.UUID
    title: str
    content: str
    type: NoticeType
    pinned: bool
    capacity: int | None
    waiting_enabled: bool
    created_at: datetime
    recipient_ids: list[uuid.UUID] = Field(default_factory=list)
    can_edit: bool = False


class NoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    type: NoticeType | None = None
    pinned: bool | None = None
    capacity: int | None = Field(default=None, ge=1)
    waiting_enabled: bool | None = None
    recipient_ids: list[uuid.UUID] | None = None


class ScheduleRequestIn(BaseModel):
    event_id: uuid.UUID
    requested_date: date
    requested_start: time | None = None
    requested_end: time | None = None
    reason: str


class ScheduleReviewIn(BaseModel):
    status: RequestStatus
    reason: str | None = None


# 후속 기능은 먼저 데이터 계약을 고정하고, 실제 규칙은 다음 단계에서 채운다.
class TeamIn(BaseModel):
    name: str
    description: str | None = None
    role_description: str | None = None
    event_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    leader_id: uuid.UUID | None = None
    member_ids: list[uuid.UUID] = Field(default_factory=list)
    schedule_at: datetime | None = None


class TeamOut(TeamIn, ORMModel):
    id: uuid.UUID
    term_id: uuid.UUID
    created_by: uuid.UUID | None
    approved_at: datetime | None


class AttendanceIn(BaseModel):
    user_id: uuid.UUID
    status: AttendanceStatus
    note: str | None = None


class AttendanceOut(AttendanceIn, ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID


class AttendanceChecklistItemOut(BaseModel):
    attendance_id: uuid.UUID | None = None
    user_id: uuid.UUID
    user_name: str
    grade: int | None
    department_id: uuid.UUID | None
    department_name: str | None
    status: AttendanceStatus
    note: str | None = None
    recorded_by: uuid.UUID | None = None
    recorded_by_name: str | None = None
    updated_at: datetime | None = None


class AttendanceSummary(BaseModel):
    total: int
    pending: int
    present: int
    absent: int
    late: int
    left_early: int


class AttendanceChecklistOut(BaseModel):
    event_id: uuid.UUID
    event_title: str
    event_date: date
    starts_at: time | None
    ends_at: time | None
    is_event_day: bool
    is_during_event: bool
    can_edit: bool
    summary: AttendanceSummary
    items: list[AttendanceChecklistItemOut]


class MeetingRecordIn(BaseModel):
    title: str
    held_at: datetime
    location: str | None = None
    summary: str | None = None
    decisions: str | None = None
    next_actions: str | None = None
    event_id: uuid.UUID | None = None
    attendee_ids: list[uuid.UUID] = Field(default_factory=list)


class MeetingRecordOut(MeetingRecordIn, ORMModel):
    id: uuid.UUID
    term_id: uuid.UUID


class CommentIn(BaseModel):
    target_type: str
    target_id: uuid.UUID
    content: str
    parent_id: uuid.UUID | None = None


class CommentOut(CommentIn, ORMModel):
    id: uuid.UUID
    author_id: uuid.UUID
    created_at: datetime


class QuickMemoIn(BaseModel):
    content: str


class QuickMemoOut(QuickMemoIn, ORMModel):
    id: uuid.UUID
    created_at: datetime


class ReminderIn(BaseModel):
    title: str
    content: str | None = None
    remind_at: datetime
    color: str = "#356ae6"


class ReminderOut(ReminderIn, ORMModel):
    id: uuid.UUID
    completed_at: datetime | None
    category: str
    source_type: str | None
    source_id: uuid.UUID | None


class CalendarItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str | None = None
    starts_at: datetime
    color: str = "#356ae6"


class CalendarItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    starts_at: datetime | None = None
    color: str | None = None


class CalendarItemOut(BaseModel):
    id: str
    source: str
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    color: str
    editable: bool = False


class SavedItemIn(BaseModel):
    target_type: str
    target_id: uuid.UUID


class SavedItemOut(SavedItemIn, ORMModel):
    id: uuid.UUID
    created_at: datetime


class PushSubscriptionIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushSubscriptionDeleteIn(BaseModel):
    endpoint: str


class PushConfigOut(BaseModel):
    enabled: bool
    public_key: str | None = None


class NotificationSendIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str | None = Field(default=None, max_length=2000)
    recipient_ids: list[uuid.UUID] = Field(min_length=1)
    target_type: str | None = Field(default=None, max_length=50)
    target_id: uuid.UUID | None = None


class NotificationOut(ORMModel):
    id: uuid.UUID
    type: str
    title: str
    content: str | None
    target_type: str | None
    target_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime


class DecisionCardIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    owner_id: uuid.UUID
    due_at: datetime | None = None
    event_id: uuid.UUID | None = None
    meeting_record_id: uuid.UUID | None = None
    create_task: bool = True


class DecisionCardStatusIn(BaseModel):
    status: DecisionStatus


class DecisionCardOut(ORMModel):
    id: uuid.UUID
    title: str
    detail: str | None
    owner_id: uuid.UUID
    owner_name: str = ""
    due_at: datetime | None
    event_id: uuid.UUID | None
    meeting_record_id: uuid.UUID | None
    task_id: uuid.UUID | None
    status: DecisionStatus
    completed_at: datetime | None
    can_manage: bool = False
    created_at: datetime


class HandoverGuideIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1)
    what_worked: str | None = None
    pitfalls: str | None = None
    checklist: str | None = None
    event_id: uuid.UUID | None = None
    publish: bool = False


class HandoverGuideOut(ORMModel):
    id: uuid.UUID
    term_id: uuid.UUID
    term_name: str = ""
    event_id: uuid.UUID | None
    title: str
    summary: str
    what_worked: str | None
    pitfalls: str | None
    checklist: str | None
    published_at: datetime | None
    can_manage: bool = False
    created_at: datetime


class EventRunItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    planned_at: datetime
    location_label: str | None = Field(default=None, max_length=200)
    assignee_id: uuid.UUID | None = None
    note: str | None = None
    sequence: int = 0


class EventRunItemStatusIn(BaseModel):
    status: RunItemStatus
    note: str | None = None


class EventRunItemOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    planned_at: datetime
    location_label: str | None
    assignee_id: uuid.UUID | None
    assignee_name: str | None = None
    status: RunItemStatus
    note: str | None
    sequence: int
    can_manage: bool = False


class SchoolMapOut(ORMModel):
    id: uuid.UUID
    term_id: uuid.UUID
    event_id: uuid.UUID | None
    title: str
    image_url: str = ""
    can_manage: bool = False
    created_at: datetime


class MapAssignmentIn(BaseModel):
    user_id: uuid.UUID
    label: str = Field(min_length=1, max_length=120)
    activity: str = Field(min_length=1, max_length=300)
    x_ratio: float = Field(ge=0, le=1)
    y_ratio: float = Field(ge=0, le=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class MapAssignmentOut(ORMModel):
    id: uuid.UUID
    map_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str = ""
    label: str
    activity: str
    x_ratio: float
    y_ratio: float
    starts_at: datetime | None
    ends_at: datetime | None
    can_manage: bool = False
