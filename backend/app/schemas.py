import uuid
from datetime import date, datetime, time
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.entities import (
    ApplicationStatus,
    AttendanceStatus,
    DecisionStatus,
    EventType,
    NoticeType,
    RequestStatus,
    Role,
    RunItemStatus,
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
    login_id: str | None = None
    name: str
    role: Role
    department_id: uuid.UUID | None
    term_id: uuid.UUID
    grade: int | None
    is_active: bool
    onboarding_completed_at: datetime | None = None


class TutorialStepOut(BaseModel):
    key: str
    title: str
    description: str
    href: str
    action_label: str
    done: bool


class TutorialStatusOut(BaseModel):
    started: bool
    completed: bool
    completed_count: int
    total_count: int
    steps: list[TutorialStepOut]


class UserCreate(BaseModel):
    email: EmailStr
    login_id: str | None = Field(default=None, min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    role: Role = Role.MEMBER
    department_id: uuid.UUID | None = None
    term_id: uuid.UUID
    grade: int | None = Field(default=None, ge=1, le=3)


class UserUpdate(BaseModel):
    name: str | None = None
    login_id: str | None = Field(default=None, min_length=1, max_length=100)
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
    can_manage: bool = False


class EventUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    location: str | None = Field(default=None, max_length=200)
    event_date: date
    starts_at: time | None = None
    ends_at: time | None = None


class TeacherEventCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: EventType = EventType.EVENT
    purpose: str = Field(min_length=1, max_length=2000)
    target_participants: str = Field(min_length=1, max_length=1000)
    schedule_plan: str = Field(min_length=1, max_length=2000)
    program_plan: str = Field(min_length=1, max_length=5000)
    preparation_plan: str | None = Field(default=None, max_length=2000)
    safety_plan: str | None = Field(default=None, max_length=2000)
    location: str = Field(min_length=1, max_length=200)
    event_date: date
    starts_at: time | None = None
    ends_at: time | None = None
    operation_dates: list[date] = Field(min_length=1, max_length=30)
    team_requirements: list["TeamRequirementIn"] = Field(min_length=1, max_length=20)
    team_manager_id: uuid.UUID
    participant_ids: list[uuid.UUID] = Field(min_length=1)
    formation_due_at: datetime | None = None


class TeacherEventCreateOut(BaseModel):
    event_id: uuid.UUID
    task_id: uuid.UUID


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
    operation_days: int | None = None
    teams_per_day: int | None = None
    people_per_team: int | None = None
    team_role_description: str | None = None
    team_requirements: list[dict] | None = None
    operation_dates: list[date] | None = None
    formation_draft: list[dict] | None = None
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


class SubmissionFileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size: int
    created_at: datetime
    download_path: str


class TaskSubmissionOut(BaseModel):
    id: uuid.UUID
    submitted_by: uuid.UUID
    submitter_name: str
    version: int
    content: str | None
    created_at: datetime
    files: list[SubmissionFileOut] = Field(default_factory=list)


class TeamDraftIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    role_description: str | None = Field(default=None, max_length=200)
    leader_id: uuid.UUID | None = None
    member_ids: list[uuid.UUID] = Field(min_length=1)
    schedule_at: datetime


class TeamFormationIn(BaseModel):
    content: str | None = None
    teams: list[TeamDraftIn] = Field(min_length=1)
    repeatable_member_ids: list[uuid.UUID] = Field(default_factory=list)


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
    read: bool = False
    applied_count: int = 0
    application_status: ApplicationStatus | None = None


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
    target_type: Literal["task"]
    target_id: uuid.UUID
    content: str = Field(min_length=1, max_length=2000)
    parent_id: uuid.UUID | None = None


class CommentOut(CommentIn, ORMModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str = ""
    is_mine: bool = False
    can_delete: bool = False
    deleted: bool = False
    created_at: datetime


class CommunityPostIn(BaseModel):
    kind: Literal["DISCUSSION", "SUGGESTION", "POLL"] = "SUGGESTION"
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=10, max_length=5000)
    is_anonymous: bool = False
    poll_options: list[str] = Field(default_factory=list, max_length=6)


class CommunityPostUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=10, max_length=5000)
    is_anonymous: bool = False


class CommunityRecommendationCountIn(BaseModel):
    count: int = Field(ge=0, le=999)


class CommunityCommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    is_anonymous: bool = False


class CommunityCommentUpdate(CommunityCommentIn):
    pass


class CommunityPollVoteIn(BaseModel):
    option_id: uuid.UUID


class CommunityPollOptionOut(BaseModel):
    id: uuid.UUID
    label: str
    position: int
    vote_count: int = 0


class CommunityCommentOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID | None
    author_name: str
    content: str
    is_anonymous: bool = False
    is_mine: bool = False
    created_at: datetime


class TeamRequirementIn(BaseModel):
    name: str = Field(max_length=50)
    people_count: int = Field(ge=1, le=20)
    role_description: str = Field(max_length=500)
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    operation_dates: list[date] | None = Field(default=None, max_length=30)


class CommunityEventPlanFields(BaseModel):
    purpose: str | None = Field(default=None, max_length=2000)
    target_participants: str | None = Field(default=None, max_length=1000)
    schedule_plan: str | None = Field(default=None, max_length=1000)
    location_plan: str | None = Field(default=None, max_length=1000)
    program_plan: str | None = Field(default=None, max_length=5000)
    role_plan: str | None = Field(default=None, max_length=3000)
    budget_plan: str | None = Field(default=None, max_length=2000)
    safety_plan: str | None = Field(default=None, max_length=2000)
    operation_days: int | None = Field(default=None, ge=1, le=30)
    teams_per_day: int | None = Field(default=None, ge=1, le=20)
    people_per_team: int | None = Field(default=None, ge=1, le=20)
    team_role_description: str | None = Field(default=None, max_length=500)
    team_requirements: list[TeamRequirementIn] | None = Field(
        default=None, min_length=1, max_length=20
    )
    operation_dates: list[date] | None = Field(default=None, min_length=1, max_length=30)
    team_manager_id: uuid.UUID | None = None
    poster_manager_id: uuid.UUID | None = None
    poster_required: bool = True


class CommunityEventPlanIn(CommunityEventPlanFields):
    base_version: int | None = Field(default=None, ge=1)


class CommunityEventPlanOut(CommunityEventPlanFields, ORMModel):
    team_manager_id: uuid.UUID | None = None
    poster_manager_id: uuid.UUID | None = None
    team_requirements: list[TeamRequirementIn] | None = None
    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID
    status: Literal["DRAFT", "IN_REVIEW", "CHANGES_REQUESTED", "REJECTED", "APPROVED"] = "DRAFT"
    version: int = 1
    submitted_at: datetime | None = None
    submitted_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    approved_by: uuid.UUID | None = None
    review_note: str | None = None
    team_task_id: uuid.UUID | None = None
    can_edit: bool = False
    can_submit: bool = False
    can_review: bool = False
    can_convert: bool = False
    created_at: datetime
    updated_at: datetime


class CommunityPlanSubmitIn(BaseModel):
    base_version: int = Field(ge=1)


class CommunityPlanReviewIn(BaseModel):
    action: Literal["APPROVE", "REQUEST_CHANGES", "REJECT"]
    note: str | None = Field(default=None, max_length=2000)


class CommunityPlanWriterIn(BaseModel):
    writer_id: uuid.UUID


class CommunityAgendaScheduleIn(BaseModel):
    meeting_date: date
    meeting_time_slot: Literal["MORNING", "LUNCH", "AFTER_SCHOOL"]
    meeting_time: time | None = None


class CommunityPlanSuggestionIn(BaseModel):
    section: Literal[
        "purpose",
        "target_participants",
        "schedule_plan",
        "location_plan",
        "program_plan",
        "role_plan",
        "budget_plan",
        "safety_plan",
    ]
    proposed_content: str = Field(min_length=1, max_length=5000)
    reason: str | None = Field(default=None, max_length=1000)


class CommunityPlanSuggestionResolveIn(BaseModel):
    action: Literal["ADOPT", "REJECT"]
    base_version: int = Field(ge=1)


class CommunityPlanSuggestionOut(BaseModel):
    id: uuid.UUID
    section: str
    proposed_content: str
    reason: str | None
    status: Literal["OPEN", "ADOPTED", "REJECTED"]
    author_id: uuid.UUID
    author_name: str
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class CommunityPlanRevisionOut(BaseModel):
    id: uuid.UUID
    version: int
    editor_id: uuid.UUID
    editor_name: str
    created_at: datetime


class CommunityPlanContributorOut(BaseModel):
    user_id: uuid.UUID
    name: str


class CommunityPlanWorkspaceOut(BaseModel):
    plan: CommunityEventPlanOut
    contributors: list[CommunityPlanContributorOut] = Field(default_factory=list)
    suggestions: list[CommunityPlanSuggestionOut] = Field(default_factory=list)
    revisions: list[CommunityPlanRevisionOut] = Field(default_factory=list)


class CommunityPostOut(BaseModel):
    id: uuid.UUID
    kind: Literal["DISCUSSION", "SUGGESTION", "POLL"]
    title: str
    content: str
    author_id: uuid.UUID | None
    author_name: str
    is_anonymous: bool = False
    is_mine: bool = False
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0
    comments: list[CommunityCommentOut] = Field(default_factory=list)
    poll_options: list[CommunityPollOptionOut] = Field(default_factory=list)
    total_votes: int = 0
    current_user_vote: uuid.UUID | None = None
    recommendation_count: int = 0
    recommended_by_me: bool = False
    test_recommendation_bonus: int = 0
    agenda_at: datetime | None = None
    plan_writer_id: uuid.UUID | None = None
    plan_writer_name: str | None = None
    meeting_date: date | None = None
    meeting_time_slot: str | None = None
    meeting_time: time | None = None
    can_assign_plan_writer: bool = False
    can_schedule_meeting: bool = False
    can_write_plan: bool = False
    plan: CommunityEventPlanOut | None = None
    converted_event_id: uuid.UUID | None = None
    converted_at: datetime | None = None


class CommunityEventConversionIn(BaseModel):
    event_date: date
    location: str | None = Field(default=None, max_length=200)
    starts_at: time | None = None
    ends_at: time | None = None


class ProposalCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    topic: str | None = Field(default=None, max_length=160)


class ProposalVersionCreateIn(ProposalCreateIn):
    base_version: int = Field(ge=1)
    change_summary: str = Field(min_length=1, max_length=500)


class ProposalFeedbackIn(BaseModel):
    category: Literal["STRENGTH", "CONCERN", "CHANGE", "NEW_IDEA"]
    content: str = Field(min_length=1, max_length=1000)


class ProposalFeedbackOut(BaseModel):
    id: uuid.UUID
    version_number: int
    author_id: uuid.UUID
    author_name: str
    category: Literal["STRENGTH", "CONCERN", "CHANGE", "NEW_IDEA"]
    content: str
    is_mine: bool = False
    created_at: datetime
    updated_at: datetime


class ProposalAttachmentOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size: int
    download_path: str
    purpose: Literal["GENERAL", "IDEA_FILE", "MEETING_AUDIO"] = "GENERAL"


class ProposalVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    title: str
    description: str
    topic: str | None = None
    change_summary: str | None = None
    author_id: uuid.UUID
    author_name: str
    created_at: datetime
    attachments: list[ProposalAttachmentOut] = Field(default_factory=list)


class ProposalSummaryOut(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    new_ideas: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    provider: Literal["ai", "fallback"] = "fallback"
    generated_at: datetime


class ProposalListOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    topic: str | None = None
    status: Literal["DISCUSSING", "RE_REVIEW", "CONFIRMED"]
    planning_stage: Literal[
        "DISCUSSING",
        "MEETING_AGENDA",
        "MEETING_COMPLETED",
        "FINAL_PLAN_DRAFT",
        "PENDING_TEACHER_REVIEW",
        "REVISION_REQUESTED",
        "REJECTED",
        "APPROVED",
        "ASSIGNING_TEAMS",
        "SCHEDULED",
    ] = "DISCUSSING"
    current_version: int
    author_name: str
    feedback_count: int = 0
    has_current_user_feedback: bool = False
    recommendation_count: int = 0
    recommended_by_me: bool = False
    feedback_required: bool = False
    required_feedback_recommendation_threshold: int = 13
    is_current_user_feedback_required: bool = False
    required_feedback_count: int = 0
    completed_required_feedback_count: int = 0
    updated_at: datetime


class ProposalDetailOut(ProposalListOut):
    current: ProposalVersionOut
    versions: list[ProposalVersionOut] = Field(default_factory=list)
    feedback: list[ProposalFeedbackOut] = Field(default_factory=list)
    summary: ProposalSummaryOut | None = None
    can_confirm: bool = False
    can_edit: bool = False
    can_delete: bool = False


class ProposalConfirmIn(BaseModel):
    base_version: int = Field(ge=1)


class ProposalMeetingNotesIn(BaseModel):
    transcript: str = Field(default="", max_length=100000)
    manual_notes: str | None = Field(default=None, max_length=20000)


class ProposalMeetingRecordDraftIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=100000)


class ProposalMeetingRecordDraftOut(BaseModel):
    title: str
    held_at: datetime | None = None
    location: str = ""
    summary: str = ""
    decisions: str = ""
    next_actions: str = ""


class ProposalPlanningDocumentIn(BaseModel):
    document: dict = Field(default_factory=dict)


class ProposalWorkflowOut(BaseModel):
    stage: Literal[
        "DISCUSSING",
        "MEETING_AGENDA",
        "MEETING_COMPLETED",
        "FINAL_PLAN_DRAFT",
        "PENDING_TEACHER_REVIEW",
        "REVISION_REQUESTED",
        "REJECTED",
        "APPROVED",
        "ASSIGNING_TEAMS",
        "SCHEDULED",
    ]
    brief_plan: dict | None = None
    meeting_audio: ProposalAttachmentOut | None = None
    meeting_transcript: str | None = None
    meeting_notes: dict | None = None
    final_plan: dict | None = None
    plan: CommunityEventPlanOut | None = None
    can_manage: bool = False
    can_promote: bool = False
    audio_extensions: list[str] = Field(default_factory=list)
    audio_max_bytes: int
    can_transcribe: bool = False
    can_auto_process: bool = False
    can_generate_brief: bool = False


class QuickMemoIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


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


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    detail: str | None
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


class EventRunItemsReorderIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1)


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
    floor_label: str
    floor_order: int
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


class MapAssignmentPositionIn(BaseModel):
    x_ratio: float = Field(ge=0, le=1)
    y_ratio: float = Field(ge=0, le=1)


class EventCompletionRecordIn(BaseModel):
    summary: str = Field(min_length=1)
    outcomes: str | None = None
    incidents: str | None = None
    recommendations: str | None = None
    attendee_count: int | None = Field(default=None, ge=0)
    completed_at: datetime
    create_handover_draft: bool = True


class EventCompletionRecordOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    event_title: str = ""
    summary: str
    outcomes: str | None
    incidents: str | None
    recommendations: str | None
    attendee_count: int | None
    completed_at: datetime
    handover_guide_id: uuid.UUID | None
    can_manage: bool = False
    created_at: datetime
