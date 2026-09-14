import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user
from app.core.storage import storage
from app.models.entities import (
    CommunityPost,
    CommunityEventPlan,
    CommunityRecommendation,
    Comment,
    Notification,
    ProposalAttachment,
    ProposalFeedback,
    ProposalSummary,
    ProposalVersion,
    Role,
    SavedItem,
    Task,
    TaskStatus,
    User,
)
from app.schemas import (
    ProposalAttachmentOut,
    ProposalConfirmIn,
    ProposalCreateIn,
    ProposalDetailOut,
    ProposalFeedbackIn,
    ProposalFeedbackOut,
    ProposalListOut,
    ProposalSummaryOut,
    ProposalMeetingNotesIn,
    ProposalMeetingRecordDraftIn,
    ProposalMeetingRecordDraftOut,
    ProposalPlanningDocumentIn,
    ProposalWorkflowOut,
    ProposalVersionCreateIn,
    ProposalVersionOut,
)
from app.services.notifications import create_notifications
from app.services.proposal_summary import summarize_feedback
from app.services.proposal_planning import (
    brief_plan_fallback,
    final_plan_fallback,
    meeting_notes_fallback,
    plan_fields,
)
from app.services.proposal_audio_ai import (
    ProposalAIError,
    assemble_processed_meeting,
    generate_brief_plan_json,
    generate_plan_json,
    generate_meeting_record_json,
    process_meeting_audio,
    transcribe_audio,
)
from app.core.config import settings

router = APIRouter(prefix="/proposals", tags=["proposals"])
VALID_STATUSES = {"DISCUSSING", "RE_REVIEW", "CONFIRMED"}
EDITABLE_PLAN_STATUSES = {"DRAFT", "CHANGES_REQUESTED", "REJECTED"}
STUDENT_ROLES = {Role.MEMBER, Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD}


def proposal_ai_error_status(error: ProposalAIError) -> int:
    if error.code == "proposal_transcription_balance_required":
        return 402
    if error.code in {
        "proposal_ai_disabled",
        "proposal_ai_key_missing",
        "proposal_transcription_key_missing",
        "proposal_ai_model_missing",
    }:
        return 503
    return 502


async def get_proposal(
    db: AsyncSession, proposal_id: uuid.UUID, user: User, *, for_update: bool = False
) -> CommunityPost:
    statement = select(CommunityPost).where(
        CommunityPost.id == proposal_id, CommunityPost.term_id == user.term_id
    )
    if for_update:
        statement = statement.with_for_update()
    proposal = await db.scalar(statement)
    if not proposal:
        raise AppError(404, "proposal_not_found", "제안을 찾을 수 없습니다.")
    return proposal


async def current_version(
    db: AsyncSession, proposal: CommunityPost, *, for_update: bool = False
) -> ProposalVersion:
    statement = select(ProposalVersion).where(
        ProposalVersion.post_id == proposal.id,
        ProposalVersion.version_number == proposal.current_proposal_version,
    )
    if for_update:
        statement = statement.with_for_update()
    version = await db.scalar(statement)
    if not version:
        raise AppError(409, "proposal_version_missing", "제안 버전 데이터가 없습니다.")
    return version


def attachment_out(item: ProposalAttachment) -> ProposalAttachmentOut:
    return ProposalAttachmentOut(
        id=item.id,
        original_name=item.original_name,
        mime_type=item.mime_type,
        size=item.size,
        download_path=f"/api/v1/proposals/attachments/{item.id}",
        purpose=item.purpose,
    )


def can_manage_workflow(proposal: CommunityPost, user: User) -> bool:
    return user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD} or user.id in {
        proposal.author_id,
        proposal.plan_writer_id,
    }


async def ensure_event_plan(
    db: AsyncSession, proposal: CommunityPost, user: User
) -> CommunityEventPlan:
    plan = await db.scalar(
        select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
    )
    if plan:
        return plan
    author_id = proposal.plan_writer_id or proposal.author_id
    plan = CommunityEventPlan(
        post_id=proposal.id,
        author_id=author_id,
        status="DRAFT",
        poster_required=False,
    )
    db.add(plan)
    await db.flush()
    return plan


async def proposal_recommendations(db: AsyncSession, proposal: CommunityPost) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(CommunityRecommendation)
        .where(CommunityRecommendation.post_id == proposal.id)
    )
    return (count or 0) + proposal.test_recommendation_bonus


def is_feedback_required(proposal: CommunityPost, recommendation_count: int) -> bool:
    return (
        proposal.proposal_feedback_required_at is not None
        or recommendation_count
        >= settings.proposal_required_feedback_recommendation_threshold
    )


async def required_feedback_progress(
    db: AsyncSession, proposal: CommunityPost, version: ProposalVersion
) -> tuple[int, int]:
    student_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == proposal.term_id,
                    User.is_active.is_(True),
                    User.role.in_(STUDENT_ROLES),
                )
            )
        ).all()
    )
    if not student_ids:
        return 0, 0
    completed_ids = set(
        (
            await db.scalars(
                select(ProposalFeedback.author_id).where(
                    ProposalFeedback.proposal_version_id == version.id,
                    ProposalFeedback.author_id.in_(student_ids),
                    ProposalFeedback.deleted_at.is_(None),
                )
            )
        ).all()
    )
    return len(student_ids), len(completed_ids)


async def students_missing_feedback(
    db: AsyncSession, proposal: CommunityPost, version: ProposalVersion
) -> set[uuid.UUID]:
    student_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == proposal.term_id,
                    User.is_active.is_(True),
                    User.role.in_(STUDENT_ROLES),
                )
            )
        ).all()
    )
    completed_ids = set(
        (
            await db.scalars(
                select(ProposalFeedback.author_id).where(
                    ProposalFeedback.proposal_version_id == version.id,
                    ProposalFeedback.author_id.in_(student_ids or {proposal.author_id}),
                    ProposalFeedback.deleted_at.is_(None),
                )
            )
        ).all()
    )
    return student_ids - completed_ids


def feedback_prompt_items(feedback: list[ProposalFeedback]) -> list[dict[str, str]]:
    return [
        {"category": str(item.category), "content": item.content}
        for item in feedback
        if item.content.strip()
    ]


async def proposal_planning_stage(
    db: AsyncSession, proposal: CommunityPost, plan: CommunityEventPlan | None = None
) -> str:
    if plan is None:
        plan = await db.scalar(
            select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
        )
    stage = "DISCUSSING"
    if proposal.agenda_at:
        stage = "MEETING_AGENDA"
    if plan and plan.meeting_notes:
        stage = "MEETING_COMPLETED"
    if plan and plan.final_plan:
        stage = "FINAL_PLAN_DRAFT"
    if plan and plan.status == "IN_REVIEW":
        stage = "PENDING_TEACHER_REVIEW"
    elif plan and plan.status == "CHANGES_REQUESTED":
        stage = "REVISION_REQUESTED"
    elif plan and plan.status == "REJECTED":
        stage = "REJECTED"
    elif plan and plan.status == "APPROVED":
        stage = "APPROVED"
        if plan.team_task_id:
            task = await db.get(Task, plan.team_task_id)
            stage = "SCHEDULED" if task and task.status == TaskStatus.DONE else "ASSIGNING_TEAMS"
    return stage


async def workflow_output(
    db: AsyncSession, proposal: CommunityPost, user: User
) -> ProposalWorkflowOut:
    from app.api.community import plan_out

    plan = await db.scalar(
        select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
    )
    audio = None
    if plan and plan.meeting_attachment_id:
        audio = await db.get(ProposalAttachment, plan.meeting_attachment_id)
    stage = await proposal_planning_stage(db, proposal, plan)
    recommendation_count = await proposal_recommendations(db, proposal)
    return ProposalWorkflowOut(
        stage=stage,
        brief_plan=plan.brief_plan if plan else None,
        meeting_audio=attachment_out(audio) if audio else None,
        meeting_transcript=plan.meeting_transcript if plan else None,
        meeting_notes=plan.meeting_notes if plan else None,
        final_plan=plan.final_plan if plan else None,
        plan=plan_out(plan, proposal, user) if plan else None,
        can_manage=can_manage_workflow(proposal, user),
        can_promote=(
            user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD}
            or recommendation_count >= settings.proposal_agenda_recommendation_threshold
        ),
        audio_extensions=sorted(settings.allowed_proposal_audio_extensions),
        audio_max_bytes=min(settings.proposal_audio_max_bytes, settings.max_upload_bytes),
        can_transcribe=bool(
            settings.proposal_ai_enabled
            and (
                (
                    settings.proposal_transcription_provider == "local"
                    and settings.proposal_local_whisper_model.strip()
                )
                or (
                    settings.proposal_transcription_provider == "api"
                    and settings.effective_transcription_api_key
                    and settings.effective_transcription_model
                )
            )
        ),
        can_auto_process=bool(
            settings.proposal_ai_enabled
            and settings.proposal_ai_model.strip()
            and settings.proposal_ai_api_key
        ),
        can_generate_brief=bool(
            settings.proposal_ai_enabled
            and settings.proposal_ai_api_key
            and settings.proposal_ai_model.strip()
        ),
    )


def apply_document_to_plan(plan: CommunityEventPlan, document: dict) -> None:
    for field, value in plan_fields(document).items():
        setattr(plan, field, value)
    dates = [str(value) for value in document.get("operation_dates", []) if str(value)]
    requirements = [
        {
            "name": str(item.get("name", "")).strip(),
            "people_count": int(item.get("people_count", 0)),
            "role_description": str(item.get("role_description", "")).strip(),
            "start_time": str(item.get("start_time") or "").strip() or None,
            "end_time": str(item.get("end_time") or "").strip() or None,
        }
        for item in document.get("team_requirements", [])
        if isinstance(item, dict)
    ]
    if len(dates) != len(set(dates)):
        raise AppError(422, "duplicate_operation_dates", "운영 날짜는 중복될 수 없습니다.")
    if any(
        not item["name"]
        or not item["role_description"]
        or not 1 <= item["people_count"] <= 20
        for item in requirements
    ):
        raise AppError(422, "invalid_team_requirements", "조 이름, 필요 인원, 역할을 확인해 주세요.")
    plan.operation_dates = dates or None
    plan.operation_days = len(dates) or None
    plan.team_requirements = requirements or None
    plan.teams_per_day = len(requirements) or None
    plan.people_per_team = max((item["people_count"] for item in requirements), default=None)
    plan.team_role_description = (
        " / ".join(f"{item['name']}: {item['role_description']}" for item in requirements)
        or None
    )
    plan.final_plan = document
    manager_id = document.get("team_manager_id")
    if manager_id:
        try:
            plan.team_manager_id = uuid.UUID(str(manager_id))
        except ValueError as error:
            raise AppError(422, "invalid_team_manager", "조 편성 담당자를 다시 선택해 주세요.") from error
    else:
        plan.team_manager_id = plan.team_manager_id or plan.author_id
    plan.poster_required = bool(document.get("poster_required", False))


async def version_outputs(
    db: AsyncSession, versions: list[ProposalVersion]
) -> list[ProposalVersionOut]:
    if not versions:
        return []
    user_ids = {item.author_id for item in versions}
    names = dict((await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))).all())
    version_ids = [item.id for item in versions]
    attachments = list(
        (
            await db.scalars(
                select(ProposalAttachment)
                .where(ProposalAttachment.proposal_version_id.in_(version_ids))
                .order_by(ProposalAttachment.created_at)
            )
        ).all()
    )
    by_version: dict[uuid.UUID, list[ProposalAttachmentOut]] = {item.id: [] for item in versions}
    for attachment in attachments:
        by_version[attachment.proposal_version_id].append(attachment_out(attachment))
    return [
        ProposalVersionOut(
            id=item.id,
            version_number=item.version_number,
            title=item.title,
            description=item.description,
            topic=item.topic,
            change_summary=item.change_summary,
            author_id=item.author_id,
            author_name=names.get(item.author_id, "알 수 없음"),
            created_at=item.created_at,
            attachments=by_version[item.id],
        )
        for item in versions
    ]


async def list_output(
    db: AsyncSession, proposal: CommunityPost, user: User
) -> ProposalListOut:
    version = await current_version(db, proposal)
    author_name = (
        "익명"
        if proposal.is_anonymous
        else await db.scalar(select(User.name).where(User.id == proposal.author_id))
    )
    count = await db.scalar(
        select(func.count())
        .select_from(ProposalFeedback)
        .where(
            ProposalFeedback.proposal_version_id == version.id,
            ProposalFeedback.deleted_at.is_(None),
        )
    )
    mine = await db.scalar(
        select(ProposalFeedback.id).where(
            ProposalFeedback.proposal_version_id == version.id,
            ProposalFeedback.author_id == user.id,
            ProposalFeedback.deleted_at.is_(None),
        )
    )
    recommendation_count = await proposal_recommendations(db, proposal)
    recommended_by_me = (
        await db.scalar(
            select(CommunityRecommendation.id).where(
                CommunityRecommendation.post_id == proposal.id,
                CommunityRecommendation.user_id == user.id,
            )
        )
    ) is not None
    feedback_required = is_feedback_required(proposal, recommendation_count)
    required_count, completed_required_count = await required_feedback_progress(
        db, proposal, version
    )
    status = proposal.proposal_status if proposal.proposal_status in VALID_STATUSES else "DISCUSSING"
    planning_stage = await proposal_planning_stage(db, proposal)
    return ProposalListOut(
        id=proposal.id,
        title=version.title,
        description=version.description,
        topic=version.topic,
        status=status,
        planning_stage=planning_stage,
        current_version=version.version_number,
        author_name=author_name or "알 수 없음",
        feedback_count=count or 0,
        has_current_user_feedback=mine is not None,
        recommendation_count=recommendation_count,
        recommended_by_me=recommended_by_me,
        feedback_required=feedback_required,
        required_feedback_recommendation_threshold=(
            settings.proposal_required_feedback_recommendation_threshold
        ),
        is_current_user_feedback_required=(
            feedback_required and user.role in STUDENT_ROLES and mine is None
        ),
        required_feedback_count=required_count,
        completed_required_feedback_count=completed_required_count,
        updated_at=proposal.updated_at,
    )


@router.get("", response_model=list[ProposalListOut])
async def list_proposals(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    proposals = list(
        (
            await db.scalars(
                select(CommunityPost)
                .where(CommunityPost.term_id == user.term_id)
                .order_by(CommunityPost.updated_at.desc())
            )
        ).all()
    )
    versioned_ids = set(
        (await db.scalars(select(ProposalVersion.post_id).where(ProposalVersion.post_id.in_([p.id for p in proposals])))).all()
    ) if proposals else set()
    return [await list_output(db, item, user) for item in proposals if item.id in versioned_ids]


@router.post("", response_model=ProposalDetailOut, status_code=201)
async def create_proposal(
    data: ProposalCreateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    title = data.title.strip()
    description = data.description.strip()
    if not title or not description:
        raise AppError(422, "proposal_content_required", "제안 제목과 설명을 입력해 주세요.")
    proposal = CommunityPost(
        term_id=user.term_id,
        author_id=user.id,
        kind="SUGGESTION",
        title=title,
        content=description,
        is_anonymous=False,
        proposal_status="DISCUSSING",
        proposal_topic=data.topic.strip() if data.topic else None,
        current_proposal_version=1,
    )
    db.add(proposal)
    await db.flush()
    db.add(
        ProposalVersion(
            post_id=proposal.id,
            version_number=1,
            title=title,
            description=description,
            topic=proposal.proposal_topic,
            author_id=user.id,
            change_summary="처음 제안",
        )
    )
    await db.commit()
    return await get_proposal_detail(proposal.id, user, db)


@router.put("/{proposal_id}/recommendation", response_model=ProposalDetailOut)
async def toggle_proposal_recommendation(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    previous_count = await proposal_recommendations(db, proposal)
    existing = await db.scalar(
        select(CommunityRecommendation).where(
            CommunityRecommendation.post_id == proposal.id,
            CommunityRecommendation.user_id == user.id,
        )
    )
    threshold = settings.proposal_required_feedback_recommendation_threshold
    if proposal.proposal_feedback_required_at is None and (
        previous_count >= threshold or (existing is None and previous_count + 1 >= threshold)
    ):
        proposal.proposal_feedback_required_at = datetime.now(UTC)
    if existing:
        await db.delete(existing)
    else:
        db.add(CommunityRecommendation(post_id=proposal.id, user_id=user.id))
    await db.commit()
    current_count = await proposal_recommendations(db, proposal)
    if previous_count < threshold <= current_count:
        version = await current_version(db, proposal)
        recipients = await students_missing_feedback(db, proposal, version)
        await create_notifications(
            db,
            recipients,
            notification_type="PROPOSAL_FEEDBACK_REQUIRED",
            title=f"의견 참여 요청: {proposal.title}",
            content=(
                f"추천 {threshold}개를 받은 제안입니다. 현재 버전을 확인하고 의견을 남겨 주세요. "
                "전원 응답 전에도 다음 단계는 진행할 수 있습니다."
            ),
            target_type="proposal",
            target_id=proposal.id,
        )
    return await get_proposal_detail(proposal.id, user, db)


@router.get("/{proposal_id}", response_model=ProposalDetailOut)
async def get_proposal_detail(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    versions = list(
        (
            await db.scalars(
                select(ProposalVersion)
                .where(ProposalVersion.post_id == proposal.id)
                .order_by(ProposalVersion.version_number.desc())
            )
        ).all()
    )
    if not versions:
        raise AppError(409, "proposal_version_missing", "제안 버전 데이터가 없습니다.")
    version_outs = await version_outputs(db, versions)
    if proposal.is_anonymous:
        for item in version_outs:
            if item.version_number == 1 and item.author_id == proposal.author_id:
                item.author_name = "익명"
    active_version = versions[0]
    feedback_rows = list(
        (
            await db.scalars(
                select(ProposalFeedback)
                .where(
                    ProposalFeedback.post_id == proposal.id,
                    ProposalFeedback.deleted_at.is_(None),
                )
                .order_by(ProposalFeedback.created_at.desc())
            )
        ).all()
    )
    names = dict(
        (
            await db.execute(
                select(User.id, User.name).where(
                    User.id.in_({item.author_id for item in feedback_rows} or {user.id})
                )
            )
        ).all()
    )
    version_numbers = {item.id: item.version_number for item in versions}
    feedback_outs = [
        ProposalFeedbackOut(
            id=item.id,
            version_number=version_numbers[item.proposal_version_id],
            author_id=item.author_id,
            author_name=names.get(item.author_id, "알 수 없음"),
            category=item.category,
            content=item.content,
            is_mine=item.author_id == user.id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in feedback_rows
    ]
    summary = await db.scalar(
        select(ProposalSummary).where(ProposalSummary.proposal_version_id == active_version.id)
    )
    summary_out = (
        ProposalSummaryOut(
            strengths=summary.strengths or [],
            concerns=summary.concerns or [],
            changes=summary.changes or [],
            new_ideas=summary.new_ideas or [],
            open_questions=summary.open_questions or [],
            provider=summary.provider,
            generated_at=summary.generated_at,
        )
        if summary
        else None
    )
    base = await list_output(db, proposal, user)
    return ProposalDetailOut(
        **base.model_dump(),
        current=version_outs[0],
        versions=version_outs,
        feedback=feedback_outs,
        summary=summary_out,
        can_confirm=user.id == proposal.author_id or user.role == Role.TEACHER,
        can_edit=proposal.proposal_status != "CONFIRMED" or user.role == Role.TEACHER,
        can_delete=user.role == Role.TEACHER,
    )


@router.post("/{proposal_id}/versions", response_model=ProposalDetailOut, status_code=201)
async def create_proposal_version(
    proposal_id: uuid.UUID,
    data: ProposalVersionCreateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    if proposal.proposal_status == "CONFIRMED" and user.role != Role.TEACHER:
        raise AppError(409, "proposal_confirmed", "확정된 제안은 새 버전을 만들 수 없습니다.")
    if data.base_version != proposal.current_proposal_version:
        raise AppError(409, "proposal_version_conflict", "다른 사람이 먼저 새 버전을 만들었습니다.")
    next_number = proposal.current_proposal_version + 1
    title = data.title.strip()
    description = data.description.strip()
    change_summary = data.change_summary.strip()
    if not title or not description:
        raise AppError(422, "proposal_content_required", "제안 제목과 설명을 입력해 주세요.")
    if not change_summary:
        raise AppError(422, "proposal_change_summary_required", "변경한 내용을 입력해 주세요.")
    db.add(
        ProposalVersion(
            post_id=proposal.id,
            version_number=next_number,
            title=title,
            description=description,
            topic=data.topic.strip() if data.topic else None,
            change_summary=change_summary,
            author_id=user.id,
        )
    )
    proposal.title = title
    proposal.content = description
    proposal.proposal_topic = data.topic.strip() if data.topic else None
    proposal.current_proposal_version = next_number
    proposal.proposal_status = "RE_REVIEW"
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise AppError(409, "proposal_version_conflict", "다른 사람이 먼저 새 버전을 만들었습니다.") from error
    if is_feedback_required(proposal, await proposal_recommendations(db, proposal)):
        version = await current_version(db, proposal)
        recipient_ids = await students_missing_feedback(db, proposal, version)
        notification_content = (
            "새 버전을 확인하고 의견을 다시 남겨 주세요. "
            "전원 응답 전에도 다음 단계는 진행할 수 있습니다."
        )
    else:
        recipient_ids = set(
            (
                await db.scalars(
                    select(ProposalFeedback.author_id).where(
                        ProposalFeedback.post_id == proposal.id,
                        ProposalFeedback.deleted_at.is_(None),
                        ProposalFeedback.author_id != user.id,
                    )
                )
            ).all()
        )
        notification_content = "제안이 수정되어 다시 의견을 받고 있습니다."
    await create_notifications(
        db,
        recipient_ids,
        notification_type="PROPOSAL_VERSION",
        title=f"새 버전: {title}",
        content=notification_content,
        target_type="proposal",
        target_id=proposal.id,
    )
    return await get_proposal_detail(proposal.id, user, db)


@router.delete("/{proposal_id}", status_code=204)
async def delete_proposal(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    if user.role != Role.TEACHER:
        raise AppError(
            403,
            "proposal_delete_teacher_only",
            "선생님만 제안을 삭제할 수 있습니다.",
        )
    attachment_keys = list(
        (
            await db.scalars(
                select(ProposalAttachment.storage_key)
                .join(
                    ProposalVersion,
                    ProposalAttachment.proposal_version_id == ProposalVersion.id,
                )
                .where(ProposalVersion.post_id == proposal.id)
            )
        ).all()
    )
    await db.execute(
        update(Comment)
        .where(
            Comment.target_type == "COMMUNITY_POST",
            Comment.target_id == proposal.id,
            Comment.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC))
    )
    await db.execute(
        delete(Notification).where(
            Notification.target_type == "proposal",
            Notification.target_id == proposal.id,
        )
    )
    await db.execute(
        delete(SavedItem).where(
            SavedItem.target_type == "proposal",
            SavedItem.target_id == proposal.id,
        )
    )
    await db.delete(proposal)
    await db.commit()
    for key in attachment_keys:
        try:
            storage.path(key).unlink(missing_ok=True)
        except (AppError, OSError):
            # DB deletion is authoritative; a missing/locked local file must not
            # turn an already completed delete into an API failure.
            continue


@router.post("/{proposal_id}/feedback", response_model=ProposalFeedbackOut, status_code=201)
async def create_proposal_feedback(
    proposal_id: uuid.UUID,
    data: ProposalFeedbackIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if proposal.proposal_status == "CONFIRMED":
        raise AppError(409, "proposal_feedback_closed", "확정된 제안에는 의견을 추가할 수 없습니다.")
    version = await current_version(db, proposal)
    if idempotency_key:
        existing = await db.scalar(
            select(ProposalFeedback).where(
                ProposalFeedback.post_id == proposal.id,
                ProposalFeedback.author_id == user.id,
                ProposalFeedback.idempotency_key == idempotency_key[:100],
            )
        )
        if existing:
            return ProposalFeedbackOut(
                id=existing.id,
                version_number=version.version_number,
                author_id=existing.author_id,
                author_name=user.name,
                category=existing.category,
                content=existing.content,
                is_mine=True,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )
    content = data.content.strip()
    if not content:
        raise AppError(422, "proposal_feedback_required", "의견을 입력해 주세요.")
    feedback = ProposalFeedback(
        post_id=proposal.id,
        proposal_version_id=version.id,
        author_id=user.id,
        category=data.category,
        content=content,
        idempotency_key=idempotency_key[:100] if idempotency_key else None,
    )
    db.add(feedback)
    await db.execute(
        delete(ProposalSummary).where(ProposalSummary.proposal_version_id == version.id)
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise AppError(409, "proposal_feedback_duplicate", "이미 처리된 의견 요청입니다.") from error
    await db.refresh(feedback)
    return ProposalFeedbackOut(
        id=feedback.id,
        version_number=version.version_number,
        author_id=user.id,
        author_name=user.name,
        category=feedback.category,
        content=feedback.content,
        is_mine=True,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


@router.patch("/{proposal_id}/feedback/{feedback_id}", response_model=ProposalFeedbackOut)
async def update_proposal_feedback(
    proposal_id: uuid.UUID,
    feedback_id: uuid.UUID,
    data: ProposalFeedbackIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    feedback = await db.scalar(
        select(ProposalFeedback).where(
            ProposalFeedback.id == feedback_id,
            ProposalFeedback.post_id == proposal.id,
            ProposalFeedback.deleted_at.is_(None),
        )
    )
    if not feedback:
        raise AppError(404, "proposal_feedback_not_found", "의견을 찾을 수 없습니다.")
    if feedback.author_id != user.id:
        raise AppError(403, "proposal_feedback_author_only", "내가 작성한 의견만 수정할 수 있습니다.")
    content = data.content.strip()
    if not content:
        raise AppError(422, "proposal_feedback_required", "의견을 입력해 주세요.")
    feedback.category = data.category
    feedback.content = content
    await db.execute(
        delete(ProposalSummary).where(
            ProposalSummary.proposal_version_id == feedback.proposal_version_id
        )
    )
    await db.commit()
    await db.refresh(feedback)
    version_number = await db.scalar(
        select(ProposalVersion.version_number).where(
            ProposalVersion.id == feedback.proposal_version_id
        )
    )
    return ProposalFeedbackOut(
        id=feedback.id,
        version_number=version_number,
        author_id=user.id,
        author_name=user.name,
        category=feedback.category,
        content=feedback.content,
        is_mine=True,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


@router.delete("/{proposal_id}/feedback/{feedback_id}", status_code=204)
async def delete_proposal_feedback(
    proposal_id: uuid.UUID,
    feedback_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    feedback = await db.scalar(
        select(ProposalFeedback).where(
            ProposalFeedback.id == feedback_id,
            ProposalFeedback.post_id == proposal.id,
            ProposalFeedback.deleted_at.is_(None),
        )
    )
    if not feedback:
        raise AppError(404, "proposal_feedback_not_found", "의견을 찾을 수 없습니다.")
    if feedback.author_id != user.id:
        raise AppError(403, "proposal_feedback_author_only", "내가 작성한 의견만 삭제할 수 있습니다.")
    feedback.deleted_at = datetime.now(UTC)
    await db.execute(
        delete(ProposalSummary).where(
            ProposalSummary.proposal_version_id == feedback.proposal_version_id
        )
    )
    await db.commit()


@router.post("/{proposal_id}/summary", response_model=ProposalSummaryOut)
async def generate_proposal_summary(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    version = await current_version(db, proposal)
    feedback = list(
        (
            await db.scalars(
                select(ProposalFeedback).where(
                    ProposalFeedback.proposal_version_id == version.id,
                    ProposalFeedback.deleted_at.is_(None),
                )
            )
        ).all()
    )
    result = await summarize_feedback(
        [{"category": item.category, "content": item.content} for item in feedback]
    )
    summary = await db.scalar(
        select(ProposalSummary).where(ProposalSummary.proposal_version_id == version.id)
    )
    if not summary:
        summary = ProposalSummary(proposal_version_id=version.id)
        db.add(summary)
    summary.strengths = result.strengths
    summary.concerns = result.concerns
    summary.changes = result.changes
    summary.new_ideas = result.new_ideas
    summary.open_questions = result.open_questions
    summary.provider = result.provider
    summary.source_feedback_updated_at = max((item.updated_at for item in feedback), default=None)
    summary.generated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(summary)
    return ProposalSummaryOut(
        strengths=summary.strengths,
        concerns=summary.concerns,
        changes=summary.changes,
        new_ideas=summary.new_ideas,
        open_questions=summary.open_questions,
        provider=summary.provider,
        generated_at=summary.generated_at,
    )


@router.post("/{proposal_id}/confirm", response_model=ProposalDetailOut)
async def confirm_proposal(
    proposal_id: uuid.UUID,
    data: ProposalConfirmIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    if user.id != proposal.author_id and user.role != Role.TEACHER:
        raise AppError(403, "proposal_confirm_forbidden", "제안 작성자 또는 선생님만 확정할 수 있습니다.")
    if data.base_version != proposal.current_proposal_version:
        raise AppError(409, "proposal_version_conflict", "최신 버전을 확인한 뒤 다시 확정해 주세요.")
    proposal.proposal_status = "CONFIRMED"
    await db.commit()
    return await get_proposal_detail(proposal.id, user, db)


@router.get("/{proposal_id}/workflow", response_model=ProposalWorkflowOut)
async def get_proposal_workflow(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/transcribe-meeting-audio", response_model=ProposalWorkflowOut)
async def transcribe_proposal_meeting_audio(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "회의 녹음을 전사할 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not plan.meeting_attachment_id:
        raise AppError(409, "proposal_meeting_audio_required", "회의 녹음을 먼저 올려 주세요.")
    attachment = await db.get(ProposalAttachment, plan.meeting_attachment_id)
    if not attachment:
        raise AppError(404, "proposal_meeting_audio_not_found", "회의 녹음 파일을 찾을 수 없습니다.")
    audio_id = attachment.id
    try:
        transcript = await transcribe_audio(
            storage.path(attachment.storage_key),
            filename=attachment.original_name,
            mime_type=attachment.mime_type,
        )
    except ProposalAIError as error:
        raise AppError(proposal_ai_error_status(error), error.code, str(error)) from error

    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == proposal.id)
        .with_for_update()
    )
    if not plan or plan.meeting_attachment_id != audio_id:
        raise AppError(
            409,
            "proposal_meeting_audio_changed",
            "전사 중 회의 녹음이 변경되었습니다. 새 녹음으로 다시 실행해 주세요.",
        )
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    plan.meeting_transcript = transcript
    plan.meeting_notes = None
    plan.final_plan = None
    plan.transcription_provider = "whisper"
    plan.ai_provider = None
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/generate-plan-from-transcript", response_model=ProposalWorkflowOut)
async def generate_proposal_plan_from_transcript(
    proposal_id: uuid.UUID,
    data: ProposalMeetingNotesIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.api.community import plan_snapshot
    from app.models.entities import CommunityPlanRevision

    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "회의 녹취를 요약할 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not plan.brief_plan:
        raise AppError(409, "proposal_brief_required", "간이 기획서를 먼저 작성해 주세요.")
    stored_transcript = (plan.meeting_transcript or "").strip()
    transcript = data.transcript.strip() or stored_transcript
    if not transcript:
        raise AppError(409, "proposal_transcript_required", "Whisper 전사 결과를 먼저 확인해 주세요.")
    version = await current_version(db, proposal)
    try:
        generated = await generate_plan_json(
            title=version.title,
            brief_plan=plan.brief_plan,
            transcript=transcript,
        )
    except ProposalAIError as error:
        raise AppError(proposal_ai_error_status(error), error.code, str(error)) from error
    processed = assemble_processed_meeting(
        title=version.title, transcript=transcript, generated=generated
    )

    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == proposal.id)
        .with_for_update()
    )
    if not plan or (plan.meeting_transcript or "").strip() != stored_transcript:
        raise AppError(
            409,
            "proposal_transcript_changed",
            "요약 중 회의 녹취가 변경되었습니다. 현재 녹취로 다시 실행해 주세요.",
        )
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    apply_document_to_plan(plan, processed.plan_document)
    plan.meeting_transcript = transcript
    if transcript != stored_transcript:
        plan.transcription_provider = "manual"
    plan.meeting_notes = processed.meeting_notes
    plan.ai_provider = processed.plan_provider
    plan.version += 1
    db.add(
        CommunityPlanRevision(
            plan_id=plan.id,
            version=plan.version,
            editor_id=user.id,
            snapshot=plan_snapshot(plan),
        )
    )
    await db.commit()
    await create_notifications(
        db,
        {proposal.author_id} - {user.id},
        notification_type="PROPOSAL_TRANSCRIPT_SUMMARIZED",
        title="회의 녹취를 바탕으로 기획서가 작성되었습니다",
        content=f"{version.title} 녹취와 자동 작성된 기획서를 확인해 주세요.",
        target_type="proposal",
        target_id=proposal.id,
    )
    return await workflow_output(db, proposal, user)


@router.post(
    "/{proposal_id}/generate-meeting-record-draft",
    response_model=ProposalMeetingRecordDraftOut,
)
async def generate_proposal_meeting_record_draft(
    proposal_id: uuid.UUID,
    data: ProposalMeetingRecordDraftIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "부장 회의록을 만들 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not plan.brief_plan:
        raise AppError(409, "proposal_brief_required", "간이 기획서를 먼저 작성해 주세요.")
    version = await current_version(db, proposal)
    schedule = {
        "date": proposal.meeting_date.isoformat() if proposal.meeting_date else None,
        "time": proposal.meeting_time.isoformat() if proposal.meeting_time else None,
        "time_slot": proposal.meeting_time_slot,
        "timezone": settings.default_timezone,
    }
    try:
        generated = await generate_meeting_record_json(
            proposal_title=version.title,
            brief_plan=plan.brief_plan,
            meeting_schedule=schedule,
            transcript=data.transcript.strip(),
        )
    except ProposalAIError as error:
        raise AppError(proposal_ai_error_status(error), error.code, str(error)) from error
    return ProposalMeetingRecordDraftOut(**generated.model_dump())


@router.post("/{proposal_id}/agenda", response_model=ProposalWorkflowOut)
async def promote_proposal_to_agenda(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    count = await proposal_recommendations(db, proposal)
    if user.role not in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD} and (
        count < settings.proposal_agenda_recommendation_threshold
    ):
        raise AppError(
            403,
            "proposal_agenda_forbidden",
            f"추천 {settings.proposal_agenda_recommendation_threshold}개 이후 안건으로 전환할 수 있습니다.",
        )
    proposal.agenda_at = proposal.agenda_at or datetime.now(UTC)
    proposal.proposal_status = "CONFIRMED"
    proposal.plan_writer_id = proposal.plan_writer_id or proposal.author_id
    plan = await ensure_event_plan(db, proposal, user)
    version = await current_version(db, proposal)
    feedback = list(
        (
            await db.scalars(
                select(ProposalFeedback).where(
                    ProposalFeedback.proposal_version_id == version.id,
                    ProposalFeedback.deleted_at.is_(None),
                )
            )
        ).all()
    )
    result = await summarize_feedback(
        [{"category": item.category, "content": item.content} for item in feedback]
    )
    summary = await db.scalar(
        select(ProposalSummary).where(ProposalSummary.proposal_version_id == version.id)
    )
    if not summary:
        summary = ProposalSummary(proposal_version_id=version.id)
        db.add(summary)
    summary.strengths = result.strengths
    summary.concerns = result.concerns
    summary.changes = result.changes
    summary.new_ideas = result.new_ideas
    summary.open_questions = result.open_questions
    summary.provider = result.provider
    summary.generated_at = datetime.now(UTC)
    fallback = brief_plan_fallback(
        title=version.title,
        description=version.description,
        summary={
            "strengths": result.strengths,
            "concerns": result.concerns,
            "changes": result.changes,
            "new_ideas": result.new_ideas,
            "open_questions": result.open_questions,
        },
    )
    try:
        generated_brief = await generate_brief_plan_json(
            proposal_title=version.title,
            proposal_description=version.description,
            feedback=feedback_prompt_items(feedback),
        )
        plan.brief_plan = generated_brief.model_dump(mode="json")
        plan.ai_provider = "ai"
    except ProposalAIError:
        # Agenda conversion remains usable without an API key or during a provider outage.
        plan.brief_plan = fallback
        plan.ai_provider = "fallback"
    await db.commit()
    manager_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == user.term_id,
                    User.role.in_([Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD]),
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    await create_notifications(
        db,
        manager_ids - {user.id},
        notification_type="PROPOSAL_MEETING_AGENDA",
        title="부장 회의 안건으로 전환되었습니다",
        content=f"{version.title} 안건과 간이 기획서를 확인해 주세요.",
        target_type="proposal",
        target_id=proposal.id,
    )
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/brief/draft", response_model=ProposalWorkflowOut)
async def generate_proposal_brief_draft(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "간이 기획서 초안을 만들 권한이 없습니다.")
    if not proposal.agenda_at:
        raise AppError(409, "proposal_agenda_required", "먼저 부장 회의 안건으로 전환해 주세요.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    version = await current_version(db, proposal)
    feedback = list(
        (
            await db.scalars(
                select(ProposalFeedback).where(
                    ProposalFeedback.proposal_version_id == version.id,
                    ProposalFeedback.deleted_at.is_(None),
                )
            )
        ).all()
    )
    try:
        generated = await generate_brief_plan_json(
            proposal_title=version.title,
            proposal_description=version.description,
            feedback=feedback_prompt_items(feedback),
        )
    except ProposalAIError as error:
        raise AppError(proposal_ai_error_status(error), error.code, str(error)) from error
    plan.brief_plan = generated.model_dump(mode="json")
    plan.ai_provider = "ai"
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.put("/{proposal_id}/brief", response_model=ProposalWorkflowOut)
async def update_proposal_brief(
    proposal_id: uuid.UUID,
    data: ProposalPlanningDocumentIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "이 회의 안건을 정리할 권한이 없습니다.")
    if not proposal.agenda_at:
        raise AppError(409, "proposal_agenda_required", "먼저 부장 회의 안건으로 전환해 주세요.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    plan.brief_plan = data.document
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/meeting-audio", response_model=ProposalWorkflowOut)
async def upload_proposal_meeting_audio(
    proposal_id: uuid.UUID,
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "회의 녹음을 올릴 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    suffix = Path(upload.filename or "").suffix.lower().lstrip(".")
    if suffix not in settings.allowed_proposal_audio_extensions:
        allowed = ", ".join(sorted(settings.allowed_proposal_audio_extensions))
        raise AppError(422, "proposal_audio_type_invalid", f"회의 녹음은 {allowed} 파일만 지원합니다.")
    version = await current_version(db, proposal)
    key, size = await storage.save(upload)
    if size > settings.proposal_audio_max_bytes:
        storage.path(key).unlink(missing_ok=True)
        raise AppError(413, "proposal_audio_too_large", "회의 녹음 파일 크기 제한을 초과했습니다.")
    attachment = ProposalAttachment(
        proposal_version_id=version.id,
        original_name=upload.filename or f"meeting.{suffix}",
        storage_key=key,
        mime_type=upload.content_type or "application/octet-stream",
        size=size,
        purpose="MEETING_AUDIO",
        uploaded_by=user.id,
    )
    db.add(attachment)
    await db.flush()
    plan.meeting_attachment_id = attachment.id
    plan.meeting_transcript = None
    plan.meeting_notes = None
    plan.final_plan = None
    plan.transcription_provider = None
    plan.ai_provider = None
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/process-meeting-audio", response_model=ProposalWorkflowOut)
async def process_proposal_meeting_audio(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.api.community import plan_snapshot
    from app.models.entities import CommunityPlanRevision

    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "회의 녹음을 처리할 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not plan.meeting_attachment_id:
        raise AppError(409, "proposal_meeting_audio_required", "회의 녹음을 먼저 올려 주세요.")
    if not plan.brief_plan:
        raise AppError(409, "proposal_brief_required", "간이 기획서를 먼저 작성해 주세요.")
    attachment = await db.get(ProposalAttachment, plan.meeting_attachment_id)
    if not attachment:
        raise AppError(404, "proposal_meeting_audio_not_found", "회의 녹음 파일을 찾을 수 없습니다.")
    version = await current_version(db, proposal)
    audio_id = attachment.id
    try:
        processed = await process_meeting_audio(
            path=storage.path(attachment.storage_key),
            filename=attachment.original_name,
            mime_type=attachment.mime_type,
            title=version.title,
            brief_plan=plan.brief_plan or {},
        )
    except ProposalAIError as error:
        raise AppError(proposal_ai_error_status(error), error.code, str(error)) from error

    proposal = await get_proposal(db, proposal_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == proposal.id)
        .with_for_update()
    )
    if not plan or plan.meeting_attachment_id != audio_id:
        raise AppError(
            409,
            "proposal_meeting_audio_changed",
            "처리 중 회의 녹음이 변경되었습니다. 새 녹음으로 다시 실행해 주세요.",
        )
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    apply_document_to_plan(plan, processed.plan_document)
    plan.meeting_transcript = processed.transcript
    plan.meeting_notes = processed.meeting_notes
    plan.transcription_provider = processed.transcription_provider
    plan.ai_provider = processed.plan_provider
    plan.version += 1
    db.add(
        CommunityPlanRevision(
            plan_id=plan.id,
            version=plan.version,
            editor_id=user.id,
            snapshot=plan_snapshot(plan),
        )
    )
    await db.commit()
    await create_notifications(
        db,
        {proposal.author_id} - {user.id},
        notification_type="PROPOSAL_AUDIO_PROCESSED",
        title="회의 녹음 처리와 기획서 작성이 완료되었습니다",
        content=f"{version.title} 녹취와 자동 작성된 기획서를 확인해 주세요.",
        target_type="proposal",
        target_id=proposal.id,
    )
    return await workflow_output(db, proposal, user)


@router.put("/{proposal_id}/meeting-notes", response_model=ProposalWorkflowOut)
async def save_proposal_meeting_notes(
    proposal_id: uuid.UUID,
    data: ProposalMeetingNotesIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "회의 내용을 정리할 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not proposal.agenda_at or not plan.brief_plan:
        raise AppError(409, "proposal_brief_required", "간이 기획서를 먼저 작성해 주세요.")
    if not data.transcript.strip() and not (data.manual_notes or "").strip():
        raise AppError(422, "proposal_meeting_notes_required", "녹취 또는 회의 정리를 입력해 주세요.")
    plan.meeting_notes = meeting_notes_fallback(data.transcript, data.manual_notes)
    plan.meeting_transcript = data.transcript.strip() or None
    plan.transcription_provider = "manual"
    plan.ai_provider = "fallback"
    version = await current_version(db, proposal)
    plan.final_plan = final_plan_fallback(
        title=version.title,
        brief=plan.brief_plan or {},
        meeting_notes=plan.meeting_notes,
    )
    apply_document_to_plan(plan, plan.final_plan)
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/final-plan", response_model=ProposalWorkflowOut)
async def generate_proposal_final_plan(
    proposal_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "최종 기획서를 만들 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    if not plan.brief_plan or not plan.meeting_notes:
        raise AppError(409, "proposal_meeting_incomplete", "간이 기획서와 회의 정리를 먼저 완료해 주세요.")
    version = await current_version(db, proposal)
    plan.final_plan = final_plan_fallback(
        title=version.title, brief=plan.brief_plan, meeting_notes=plan.meeting_notes
    )
    apply_document_to_plan(plan, plan.final_plan)
    plan.ai_provider = "fallback"
    await db.commit()
    await create_notifications(
        db,
        {proposal.author_id} - {user.id},
        notification_type="PROPOSAL_FINAL_PLAN_DRAFT",
        title="최종 기획서 초안이 생성되었습니다",
        content=f"{version.title} 회의 내용을 바탕으로 만든 초안을 확인해 주세요.",
        target_type="proposal",
        target_id=proposal.id,
    )
    return await workflow_output(db, proposal, user)


@router.put("/{proposal_id}/final-plan", response_model=ProposalWorkflowOut)
async def update_proposal_final_plan(
    proposal_id: uuid.UUID,
    data: ProposalPlanningDocumentIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.api.community import plan_snapshot
    from app.models.entities import CommunityPlanRevision

    proposal = await get_proposal(db, proposal_id, user)
    if not can_manage_workflow(proposal, user):
        raise AppError(403, "proposal_workflow_forbidden", "최종 기획서를 수정할 권한이 없습니다.")
    plan = await ensure_event_plan(db, proposal, user)
    if plan.status not in EDITABLE_PLAN_STATUSES:
        raise AppError(409, "proposal_plan_locked", "교사 검토 중인 기획서는 수정할 수 없습니다.")
    apply_document_to_plan(plan, data.document)
    manager = await db.scalar(
        select(User).where(
            User.id == plan.team_manager_id,
            User.term_id == user.term_id,
            User.is_active.is_(True),
            User.role != Role.TEACHER,
        )
    )
    if not manager:
        raise AppError(
            422,
            "invalid_team_manager",
            "현재 기수의 활성 학생 임원 중에서 조 편성 담당자를 선택해 주세요.",
        )
    plan.version += 1
    db.add(
        CommunityPlanRevision(
            plan_id=plan.id,
            version=plan.version,
            editor_id=user.id,
            snapshot=plan_snapshot(plan),
        )
    )
    await db.commit()
    return await workflow_output(db, proposal, user)


@router.post("/{proposal_id}/attachments", response_model=ProposalAttachmentOut, status_code=201)
async def upload_proposal_attachment(
    proposal_id: uuid.UUID,
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await get_proposal(db, proposal_id, user)
    version = await current_version(db, proposal)
    key, size = await storage.save(upload)
    attachment = ProposalAttachment(
        proposal_version_id=version.id,
        original_name=upload.filename or "file",
        storage_key=key,
        mime_type=upload.content_type or "application/octet-stream",
        size=size,
        uploaded_by=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment_out(attachment)


@router.get("/attachments/{attachment_id}")
async def download_proposal_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db.scalar(
        select(ProposalAttachment)
        .join(ProposalVersion, ProposalVersion.id == ProposalAttachment.proposal_version_id)
        .join(CommunityPost, CommunityPost.id == ProposalVersion.post_id)
        .where(ProposalAttachment.id == attachment_id, CommunityPost.term_id == user.term_id)
    )
    if not attachment:
        raise AppError(404, "proposal_attachment_not_found", "첨부 파일을 찾을 수 없습니다.")
    return FileResponse(
        storage.path(attachment.storage_key),
        filename=attachment.original_name,
        media_type=attachment.mime_type,
    )
