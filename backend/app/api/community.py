import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user, require_roles
from app.models.entities import (
    Comment,
    CommunityEventPlan,
    CommunityPlanRevision,
    CommunityPlanSuggestion,
    CommunityPost,
    CommunityRecommendation,
    Event,
    ProposalVersion,
    EventParticipant,
    EventType,
    Role,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    User,
)
from app.schemas import (
    CommunityAgendaScheduleIn,
    CommunityCommentIn,
    CommunityCommentOut,
    CommunityCommentUpdate,
    CommunityEventConversionIn,
    CommunityEventPlanIn,
    CommunityEventPlanOut,
    CommunityPlanContributorOut,
    CommunityPlanReviewIn,
    CommunityPlanRevisionOut,
    CommunityPlanSubmitIn,
    CommunityPlanSuggestionIn,
    CommunityPlanSuggestionOut,
    CommunityPlanSuggestionResolveIn,
    CommunityPlanWorkspaceOut,
    CommunityPlanWriterIn,
    CommunityPostIn,
    CommunityPostOut,
    CommunityPostUpdate,
    CommunityRecommendationCountIn,
)
from app.services.notifications import create_notifications

router = APIRouter(prefix="/community", tags=["community"])
event_manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)
COMMUNITY_COMMENT_TARGET = "COMMUNITY_POST"
PLAN_TEXT_FIELDS = {
    "purpose",
    "target_participants",
    "schedule_plan",
    "location_plan",
    "program_plan",
    "role_plan",
    "budget_plan",
    "safety_plan",
}
PLAN_STATUSES_EDITABLE = {"DRAFT", "CHANGES_REQUESTED", "REJECTED"}


def can_edit_plan(post: CommunityPost, plan: CommunityEventPlan, user: User) -> bool:
    return user.role != Role.TEACHER and plan.status in PLAN_STATUSES_EDITABLE


def plan_is_complete(plan: CommunityEventPlan) -> bool:
    required_text = [getattr(plan, field) for field in PLAN_TEXT_FIELDS]
    return bool(
        all(value and value.strip() for value in required_text)
        and plan.operation_dates
        and len(plan.operation_dates) == len(set(plan.operation_dates))
        and plan.team_requirements
        and all(
            item.get("name") and item.get("role_description") and item.get("people_count")
            for item in plan.team_requirements
        )
        and plan.team_manager_id
        and (not plan.poster_required or plan.poster_manager_id)
    )


def plan_snapshot(plan: CommunityEventPlan) -> dict:
    snapshot = {field: getattr(plan, field) for field in PLAN_TEXT_FIELDS}
    snapshot.update(
        operation_days=plan.operation_days,
        operation_dates=plan.operation_dates,
        teams_per_day=plan.teams_per_day,
        people_per_team=plan.people_per_team,
        team_role_description=plan.team_role_description,
        team_requirements=plan.team_requirements,
        team_manager_id=str(plan.team_manager_id) if plan.team_manager_id else None,
        poster_manager_id=str(plan.poster_manager_id) if plan.poster_manager_id else None,
        poster_required=plan.poster_required,
    )
    return snapshot


def plan_out(
    plan: CommunityEventPlan, post: CommunityPost, user: User
) -> CommunityEventPlanOut:
    return CommunityEventPlanOut.model_validate(plan).model_copy(
        update={
            "can_edit": can_edit_plan(post, plan, user),
            "can_submit": (
                plan.author_id == user.id
                and plan.status in PLAN_STATUSES_EDITABLE
                and plan_is_complete(plan)
            ),
            "can_review": user.role == Role.TEACHER and plan.status == "IN_REVIEW",
            "can_convert": (
                user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER}
                and plan.status == "APPROVED"
                and not post.converted_event_id
            ),
        }
    )


def comment_out(comment: Comment, user: User) -> CommunityCommentOut:
    return CommunityCommentOut(
        id=comment.id,
        author_id=None if comment.is_anonymous else user.id,
        author_name="익명" if comment.is_anonymous else user.name,
        content=comment.content,
        is_anonymous=comment.is_anonymous,
        is_mine=True,
        created_at=comment.created_at,
    )


def can_manage_post(post: CommunityPost, user: User) -> bool:
    return post.author_id == user.id or user.role == Role.TEACHER


async def get_owned_comment(
    db: AsyncSession, post: CommunityPost, comment_id: uuid.UUID, user: User
) -> Comment:
    comment = await db.scalar(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.term_id == user.term_id,
            Comment.target_type == COMMUNITY_COMMENT_TARGET,
            Comment.target_id == post.id,
            Comment.deleted_at.is_(None),
        )
    )
    if not comment:
        raise AppError(404, "community_comment_not_found", "의견을 찾을 수 없습니다.")
    if comment.author_id != user.id:
        raise AppError(403, "community_comment_author_only", "내가 작성한 의견만 수정할 수 있습니다.")
    return comment


async def get_post(
    db: AsyncSession, post_id: uuid.UUID, user: User, *, for_update: bool = False
) -> CommunityPost:
    statement = select(CommunityPost).where(
        CommunityPost.id == post_id, CommunityPost.term_id == user.term_id
    )
    if for_update:
        statement = statement.with_for_update()
    post = await db.scalar(statement)
    if not post:
        raise AppError(404, "community_post_not_found", "게시글을 찾을 수 없습니다.")
    return post


async def recommendation_count(db: AsyncSession, post: CommunityPost) -> int:
    actual = (
        await db.scalar(
            select(func.count())
            .select_from(CommunityRecommendation)
            .where(CommunityRecommendation.post_id == post.id)
        )
        or 0
    )
    return actual + post.test_recommendation_bonus


async def promote_to_agenda(db: AsyncSession, post: CommunityPost) -> bool:
    if (
        post.agenda_at
        or await recommendation_count(db, post)
        < settings.proposal_agenda_recommendation_threshold
    ):
        return False
    post.agenda_at = datetime.now(UTC)
    return True


async def notify_agenda_managers(db: AsyncSession, post: CommunityPost) -> None:
    recipient_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == post.term_id,
                    User.is_active.is_(True),
                    User.role.in_([Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD]),
                )
            )
        ).all()
    )
    if recipient_ids:
        await create_notifications(
            db,
            recipient_ids,
            notification_type="COMMUNITY_AGENDA_PROMOTED",
            title="새 부장회의 안건이 등록되었습니다",
            content=(
                f"{post.title} 아이디어가 추천 "
                f"{settings.proposal_agenda_recommendation_threshold}개를 받아 회의 안건으로 등록되었습니다."
            ),
            target_type="community",
            target_id=post.id,
        )


async def serialize_posts(
    db: AsyncSession, posts: list[CommunityPost], user: User
) -> list[CommunityPostOut]:
    if not posts:
        return []

    post_ids = [post.id for post in posts]
    author_ids = {post.author_id for post in posts if not post.is_anonymous}
    author_ids.update(post.plan_writer_id for post in posts if post.plan_writer_id)
    author_names = (
        dict((await db.execute(select(User.id, User.name).where(User.id.in_(author_ids)))).all())
        if author_ids
        else {}
    )
    teacher_author_ids = (
        set(
            (
                await db.scalars(
                    select(User.id).where(
                        User.id.in_(author_ids),
                        User.role == Role.TEACHER,
                    )
                )
            ).all()
        )
        if author_ids
        else set()
    )
    recommendation_counts = dict(
        (
            await db.execute(
                select(CommunityRecommendation.post_id, func.count())
                .where(CommunityRecommendation.post_id.in_(post_ids))
                .group_by(CommunityRecommendation.post_id)
            )
        ).all()
    )
    my_recommendations = set(
        (
            await db.scalars(
                select(CommunityRecommendation.post_id).where(
                    CommunityRecommendation.post_id.in_(post_ids),
                    CommunityRecommendation.user_id == user.id,
                )
            )
        ).all()
    )
    plans = list(
        (
            await db.scalars(
                select(CommunityEventPlan).where(CommunityEventPlan.post_id.in_(post_ids))
            )
        ).all()
    )
    plans_by_post = {plan.post_id: plan for plan in plans}
    comments = list(
        (
            await db.scalars(
                select(Comment)
                .where(
                    Comment.term_id == user.term_id,
                    Comment.target_type == COMMUNITY_COMMENT_TARGET,
                    Comment.target_id.in_(post_ids),
                    Comment.deleted_at.is_(None),
                )
                .order_by(Comment.created_at, Comment.id)
            )
        ).all()
    )
    comment_author_ids = {comment.author_id for comment in comments}
    comment_author_names = (
        dict(
            (
                await db.execute(
                    select(User.id, User.name).where(User.id.in_(comment_author_ids))
                )
            ).all()
        )
        if comment_author_ids
        else {}
    )
    comments_by_post: dict[uuid.UUID, list[CommunityCommentOut]] = {
        post_id: [] for post_id in post_ids
    }
    for comment in comments:
        comments_by_post[comment.target_id].append(
            CommunityCommentOut(
                id=comment.id,
                author_id=None if comment.is_anonymous else comment.author_id,
                author_name=(
                    "익명"
                    if comment.is_anonymous
                    else comment_author_names.get(comment.author_id, "알 수 없음")
                ),
                content=comment.content,
                is_anonymous=comment.is_anonymous,
                is_mine=comment.author_id == user.id,
                created_at=comment.created_at,
            )
        )

    return [
        CommunityPostOut(
            id=post.id,
            kind=post.kind,
            title=post.title,
            content=post.content,
            author_id=None if post.is_anonymous else post.author_id,
            author_name="익명" if post.is_anonymous else author_names.get(post.author_id, "알 수 없음"),
            is_anonymous=post.is_anonymous,
            is_mine=post.author_id == user.id,
            created_at=post.created_at,
            updated_at=post.updated_at,
            comment_count=len(comments_by_post[post.id]),
            comments=comments_by_post[post.id],
            recommendation_count=(
                recommendation_counts.get(post.id, 0) + post.test_recommendation_bonus
            ),
            recommended_by_me=post.id in my_recommendations,
            test_recommendation_bonus=post.test_recommendation_bonus,
            agenda_at=post.agenda_at,
            plan_writer_id=post.plan_writer_id,
            plan_writer_name=author_names.get(post.plan_writer_id) if post.plan_writer_id else None,
            meeting_date=post.meeting_date,
            meeting_time_slot=post.meeting_time_slot,
            meeting_time=post.meeting_time,
            can_assign_plan_writer=(
                post.agenda_at is not None
                and not post.converted_event_id
                and (
                    post.id not in plans_by_post
                    or plans_by_post[post.id].status in PLAN_STATUSES_EDITABLE
                )
                and user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER}
            ),
            can_schedule_meeting=(
                post.agenda_at is not None
                and not post.converted_event_id
                and user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER}
            ),
            can_write_plan=(
                can_edit_plan(post, plans_by_post[post.id], user)
                if post.id in plans_by_post
                else (
                    user.role != Role.TEACHER
                    and (
                        user.id == (post.plan_writer_id or post.author_id)
                        or (post.plan_writer_id is None and post.author_id in teacher_author_ids)
                    )
                    and recommendation_counts.get(post.id, 0)
                    + post.test_recommendation_bonus
                    >= settings.proposal_agenda_recommendation_threshold
                )
            ),
            plan=(
                plan_out(plans_by_post[post.id], post, user)
                if post.id in plans_by_post
                else None
            ),
            converted_event_id=post.converted_event_id,
            converted_at=post.converted_at,
        )
        for post in posts
    ]


@router.get("", response_model=list[CommunityPostOut])
async def list_community_posts(
    sort: str = "popular",
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if sort not in {"popular", "recent"}:
        raise AppError(422, "invalid_community_sort", "추천순 또는 최신순을 선택해 주세요.")
    posts = list(
        (
            await db.scalars(
                select(CommunityPost)
                .where(CommunityPost.term_id == user.term_id)
                .order_by(CommunityPost.created_at.desc())
            )
        ).all()
    )
    serialized = await serialize_posts(db, posts, user)
    if sort == "popular":
        serialized.sort(
            key=lambda post: (
                post.agenda_at is not None,
                post.recommendation_count,
                post.created_at,
            ),
            reverse=True,
        )
    else:
        serialized.sort(
            key=lambda post: (post.agenda_at is not None, post.created_at), reverse=True
        )
    return serialized


@router.post("", response_model=CommunityPostOut, status_code=201)
async def create_community_post(
    data: CommunityPostIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    title = data.title.strip()
    content = data.content.strip()
    if not title:
        raise AppError(422, "community_title_required", "행사 아이디어를 입력해 주세요.")
    if len(content) < 10:
        raise AppError(
            422,
            "community_overview_required",
            "행사 목적과 진행 모습을 알 수 있도록 전체 개요를 10자 이상 적어 주세요.",
        )

    post = CommunityPost(
        term_id=user.term_id,
        author_id=user.id,
        kind="SUGGESTION",
        title=title,
        content=content,
        is_anonymous=data.is_anonymous,
    )
    db.add(post)
    await db.flush()
    db.add(
        ProposalVersion(
            post_id=post.id,
            version_number=1,
            title=title,
            description=content,
            change_summary="기존 아이디어 게시판에서 작성됨",
            author_id=user.id,
        )
    )
    await db.commit()
    await db.refresh(post)
    return (await serialize_posts(db, [post], user))[0]


@router.patch("/{post_id}", response_model=CommunityPostOut)
async def update_community_post(
    post_id: uuid.UUID,
    data: CommunityPostUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user, for_update=True)
    if not can_manage_post(post, user):
        raise AppError(403, "community_post_edit_forbidden", "이 게시물을 수정할 권한이 없습니다.")
    title = data.title.strip()
    content = data.content.strip()
    if not title or len(content) < 10:
        raise AppError(422, "community_post_incomplete", "제목과 10자 이상의 행사 개요가 필요합니다.")
    post.title = title
    post.content = content
    post.is_anonymous = data.is_anonymous
    await db.commit()
    await db.refresh(post)
    return (await serialize_posts(db, [post], user))[0]


@router.delete("/{post_id}", status_code=204)
async def delete_community_post(
    post_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    post = await get_post(db, post_id, user)
    if not can_manage_post(post, user):
        raise AppError(403, "community_post_delete_forbidden", "이 게시물을 삭제할 권한이 없습니다.")
    await db.execute(
        update(Comment)
        .where(
            Comment.target_type == COMMUNITY_COMMENT_TARGET,
            Comment.target_id == post.id,
            Comment.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC))
    )
    await db.execute(
        delete(CommunityRecommendation).where(CommunityRecommendation.post_id == post.id)
    )
    await db.execute(delete(CommunityEventPlan).where(CommunityEventPlan.post_id == post.id))
    await db.delete(post)
    await db.commit()


@router.post(
    "/{post_id}/comments",
    response_model=CommunityCommentOut,
    status_code=201,
)
async def create_community_comment(
    post_id: uuid.UUID,
    data: CommunityCommentIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user)
    content = data.content.strip()
    if not content:
        raise AppError(422, "community_comment_required", "의견을 입력해 주세요.")

    created_at = datetime.now(UTC)
    comment = Comment(
        term_id=user.term_id,
        target_type=COMMUNITY_COMMENT_TARGET,
        target_id=post.id,
        author_id=user.id,
        parent_id=None,
        content=content,
        is_anonymous=data.is_anonymous,
        deleted_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment_out(comment, user)


@router.patch(
    "/{post_id}/comments/{comment_id}",
    response_model=CommunityCommentOut,
)
async def update_community_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    data: CommunityCommentUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user)
    comment = await get_owned_comment(db, post, comment_id, user)
    content = data.content.strip()
    if not content:
        raise AppError(422, "community_comment_required", "의견을 입력해 주세요.")
    comment.content = content
    comment.is_anonymous = data.is_anonymous
    await db.commit()
    await db.refresh(comment)
    return comment_out(comment, user)


@router.delete("/{post_id}/comments/{comment_id}", status_code=204)
async def delete_community_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    post = await get_post(db, post_id, user)
    comment = await get_owned_comment(db, post, comment_id, user)
    comment.deleted_at = datetime.now(UTC)
    await db.commit()


@router.put("/{post_id}/plan-writer", response_model=CommunityPostOut)
async def assign_community_plan_writer(
    post_id: uuid.UUID,
    data: CommunityPlanWriterIn,
    actor: User = Depends(event_manager),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, actor, for_update=True)
    if not post.agenda_at:
        raise AppError(409, "community_agenda_required", "부장회의 안건의 작성자만 지정할 수 있습니다.")
    if post.converted_event_id:
        raise AppError(409, "community_event_already_started", "이미 행사로 전환된 안건입니다.")
    writer = await db.scalar(
        select(User).where(
            User.id == data.writer_id,
            User.term_id == actor.term_id,
            User.is_active.is_(True),
            User.role.in_([Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD]),
        )
    )
    if not writer:
        raise AppError(
            422,
            "community_plan_writer_invalid",
            "현재 기수의 부장단 또는 회장단 중에서 작성자를 선택해 주세요.",
        )
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == post.id)
        .with_for_update()
    )
    if plan and plan.status not in PLAN_STATUSES_EDITABLE:
        raise AppError(409, "community_plan_writer_locked", "검토 중이거나 승인된 기획서의 작성자는 바꿀 수 없습니다.")
    post.plan_writer_id = writer.id
    if plan:
        plan.author_id = writer.id
    await db.commit()
    await create_notifications(
        db,
        {writer.id},
        notification_type="COMMUNITY_PLAN_WRITER_ASSIGNED",
        title="부장회의 기획서 작성을 맡아 주세요",
        content=f"{post.title} 안건의 회의 내용을 지정된 양식에 정리해 주세요.",
        target_type="community",
        target_id=post.id,
    )
    await db.refresh(post)
    return (await serialize_posts(db, [post], actor))[0]


@router.put("/{post_id}/meeting-schedule", response_model=CommunityPostOut)
async def set_community_meeting_schedule(
    post_id: uuid.UUID,
    data: CommunityAgendaScheduleIn,
    actor: User = Depends(event_manager),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, actor, for_update=True)
    if not post.agenda_at:
        raise AppError(409, "community_agenda_required", "부장회의 안건의 일정만 정할 수 있습니다.")
    if post.converted_event_id:
        raise AppError(409, "community_event_already_started", "이미 행사로 전환된 안건입니다.")

    post.meeting_date = data.meeting_date
    post.meeting_time_slot = data.meeting_time_slot
    post.meeting_time = data.meeting_time
    await db.commit()

    slot_name = {
        "MORNING": "아침시간",
        "LUNCH": "점심시간",
        "AFTER_SCHOOL": "방과후",
    }[data.meeting_time_slot]
    exact_time = data.meeting_time.strftime(" %H:%M") if data.meeting_time else ""
    recipient_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == post.term_id,
                    User.is_active.is_(True),
                    User.role.in_([Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD]),
                )
            )
        ).all()
    )
    await create_notifications(
        db,
        recipient_ids,
        notification_type="COMMUNITY_MEETING_SCHEDULED",
        title="부장회의 일정이 정해졌습니다",
        content=(
            f"{post.title} 안건 회의: {data.meeting_date.strftime('%Y년 %m월 %d일')} "
            f"{slot_name}{exact_time}"
        ),
        target_type="community",
        target_id=post.id,
    )
    await db.refresh(post)
    return (await serialize_posts(db, [post], actor))[0]


@router.put(
    "/{post_id}/plan",
    response_model=CommunityEventPlanOut,
)
async def save_community_event_plan(
    post_id: uuid.UUID,
    data: CommunityEventPlanIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == post.id)
        .with_for_update()
    )
    if plan:
        if not can_edit_plan(post, plan, user):
            if plan.status == "IN_REVIEW":
                message = "선생님 검토 중에는 기획서를 수정할 수 없습니다."
            elif plan.status == "APPROVED":
                message = "승인된 기획서는 수정할 수 없습니다."
            else:
                message = "현재 상태에서는 기획서를 수정할 수 없습니다."
            raise AppError(403, "community_plan_edit_locked", message)
        if data.base_version is None or data.base_version != plan.version:
            raise AppError(
                409,
                "community_plan_version_conflict",
                "다른 사람이 먼저 수정했습니다. 최신 기획서를 다시 열어 주세요.",
            )
    else:
        if user.role == Role.TEACHER:
            raise AppError(
                403,
                "community_plan_students_only",
                "학생 임원이 공동 기획서 작성을 시작하고 선생님은 최종 승인합니다.",
            )
        plan_writer_id = post.plan_writer_id
        if plan_writer_id is None:
            post_author_role = await db.scalar(
                select(User.role).where(User.id == post.author_id)
            )
            plan_writer_id = user.id if post_author_role == Role.TEACHER else post.author_id
        if user.id != plan_writer_id:
            raise AppError(
                403,
                "community_plan_writer_only",
                "부장회의에서 지정된 작성자가 기획서 작성을 시작할 수 있습니다.",
            )
        if (
            await recommendation_count(db, post)
            < settings.proposal_agenda_recommendation_threshold
        ):
            raise AppError(
                403,
                "community_plan_locked",
                (
                    f"추천 {settings.proposal_agenda_recommendation_threshold}개를 받으면 "
                    "공동 기획서 작성을 시작할 수 있습니다."
                ),
            )
        plan = CommunityEventPlan(
            post_id=post.id,
            author_id=plan_writer_id,
            status="DRAFT",
            version=1,
        )
        db.add(plan)
        await db.flush()

    values = data.model_dump(exclude={"base_version"}, exclude_unset=True)
    values = {
        key: (value.strip() or None) if isinstance(value, str) else value
        for key, value in values.items()
    }
    if "operation_dates" in values and values["operation_dates"] is not None:
        values["operation_dates"] = [value.isoformat() for value in values["operation_dates"]]
        values["operation_days"] = len(values["operation_dates"])
    if "team_requirements" in values and values["team_requirements"] is not None:
        values["team_requirements"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in values["team_requirements"]
        ]

    manager_ids = {
        value
        for key, value in values.items()
        if key in {"team_manager_id", "poster_manager_id"} and value is not None
    }
    if manager_ids:
        valid_manager_ids = set(
            (
                await db.scalars(
                    select(User.id).where(
                        User.id.in_(manager_ids),
                        User.term_id == user.term_id,
                        User.is_active.is_(True),
                        User.role != Role.TEACHER,
                    )
                )
            ).all()
        )
        if valid_manager_ids != manager_ids:
            raise AppError(
                422,
                "community_plan_invalid_manager",
                "현재 학생회 임원 중에서 담당자를 선택해 주세요.",
            )

    for key, value in values.items():
        setattr(plan, key, value)
    if data.base_version is not None:
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
    await db.refresh(plan)
    return plan_out(plan, post, user)


async def serialize_plan_workspace(
    db: AsyncSession, post: CommunityPost, plan: CommunityEventPlan, user: User
) -> CommunityPlanWorkspaceOut:
    revisions = list(
        (
            await db.scalars(
                select(CommunityPlanRevision)
                .where(CommunityPlanRevision.plan_id == plan.id)
                .order_by(CommunityPlanRevision.version.desc())
            )
        ).all()
    )
    suggestions = list(
        (
            await db.scalars(
                select(CommunityPlanSuggestion)
                .where(CommunityPlanSuggestion.plan_id == plan.id)
                .order_by(CommunityPlanSuggestion.created_at.desc())
            )
        ).all()
    )
    user_ids = {plan.author_id}
    user_ids.update(revision.editor_id for revision in revisions)
    user_ids.update(suggestion.author_id for suggestion in suggestions)
    names = dict(
        (
            await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
        ).all()
    )
    contributor_ids = [plan.author_id]
    contributor_ids.extend(
        revision.editor_id
        for revision in reversed(revisions)
        if revision.editor_id not in contributor_ids
    )
    return CommunityPlanWorkspaceOut(
        plan=plan_out(plan, post, user),
        contributors=[
            CommunityPlanContributorOut(user_id=user_id, name=names.get(user_id, "알 수 없음"))
            for user_id in contributor_ids
        ],
        suggestions=[
            CommunityPlanSuggestionOut(
                id=suggestion.id,
                section=suggestion.section,
                proposed_content=suggestion.proposed_content,
                reason=suggestion.reason,
                status=suggestion.status,
                author_id=suggestion.author_id,
                author_name=names.get(suggestion.author_id, "알 수 없음"),
                resolved_by=suggestion.resolved_by,
                resolved_at=suggestion.resolved_at,
                created_at=suggestion.created_at,
            )
            for suggestion in suggestions
        ],
        revisions=[
            CommunityPlanRevisionOut(
                id=revision.id,
                version=revision.version,
                editor_id=revision.editor_id,
                editor_name=names.get(revision.editor_id, "알 수 없음"),
                created_at=revision.created_at,
            )
            for revision in revisions
        ],
    )


@router.get("/{post_id}/plan", response_model=CommunityPlanWorkspaceOut)
async def get_community_plan_workspace(
    post_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user)
    plan = await db.scalar(
        select(CommunityEventPlan).where(CommunityEventPlan.post_id == post.id)
    )
    if not plan:
        raise AppError(404, "community_plan_not_found", "공동 기획서를 찾을 수 없습니다.")
    return await serialize_plan_workspace(db, post, plan, user)


@router.post(
    "/{post_id}/plan/suggestions",
    response_model=CommunityPlanSuggestionOut,
    status_code=201,
)
async def create_community_plan_suggestion(
    post_id: uuid.UUID,
    data: CommunityPlanSuggestionIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user)
    plan = await db.scalar(
        select(CommunityEventPlan).where(CommunityEventPlan.post_id == post.id)
    )
    if not plan:
        raise AppError(404, "community_plan_not_found", "공동 기획서를 찾을 수 없습니다.")
    if not can_edit_plan(post, plan, user):
        raise AppError(
            403,
            "community_plan_suggestion_locked",
            "현재는 새 수정 제안을 남길 수 없습니다.",
        )
    suggestion = CommunityPlanSuggestion(
        plan_id=plan.id,
        author_id=user.id,
        section=data.section,
        proposed_content=data.proposed_content.strip(),
        reason=data.reason.strip() if data.reason else None,
        status="OPEN",
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return CommunityPlanSuggestionOut(
        id=suggestion.id,
        section=suggestion.section,
        proposed_content=suggestion.proposed_content,
        reason=suggestion.reason,
        status="OPEN",
        author_id=user.id,
        author_name=user.name,
        created_at=suggestion.created_at,
    )


@router.put(
    "/{post_id}/plan/suggestions/{suggestion_id}",
    response_model=CommunityPlanWorkspaceOut,
)
async def resolve_community_plan_suggestion(
    post_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    data: CommunityPlanSuggestionResolveIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == post.id)
        .with_for_update()
    )
    if not plan:
        raise AppError(404, "community_plan_not_found", "공동 기획서를 찾을 수 없습니다.")
    if plan.author_id != user.id:
        raise AppError(
            403,
            "community_plan_suggestion_resolve_author_only",
            "공동 기획서를 시작한 학생이 수정 제안을 최종 정리할 수 있습니다.",
        )
    if plan.status not in PLAN_STATUSES_EDITABLE:
        raise AppError(409, "community_plan_not_editable", "현재 기획서를 수정할 수 없습니다.")
    if data.base_version != plan.version:
        raise AppError(
            409,
            "community_plan_version_conflict",
            "다른 사람이 먼저 수정했습니다. 최신 기획서를 다시 열어 주세요.",
        )
    suggestion = await db.scalar(
        select(CommunityPlanSuggestion).where(
            CommunityPlanSuggestion.id == suggestion_id,
            CommunityPlanSuggestion.plan_id == plan.id,
        )
    )
    if not suggestion:
        raise AppError(404, "community_plan_suggestion_not_found", "수정 제안을 찾을 수 없습니다.")
    if suggestion.status != "OPEN":
        raise AppError(409, "community_plan_suggestion_resolved", "이미 처리한 수정 제안입니다.")

    suggestion.status = "ADOPTED" if data.action == "ADOPT" else "REJECTED"
    suggestion.resolved_by = user.id
    suggestion.resolved_at = datetime.now(UTC)
    if data.action == "ADOPT":
        setattr(plan, suggestion.section, suggestion.proposed_content)
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
    await db.refresh(plan)
    return await serialize_plan_workspace(db, post, plan, user)


@router.post("/{post_id}/plan/submit", response_model=CommunityEventPlanOut)
async def submit_community_plan_for_review(
    post_id: uuid.UUID,
    data: CommunityPlanSubmitIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == post.id)
        .with_for_update()
    )
    if not plan:
        raise AppError(404, "community_plan_not_found", "공동 기획서를 찾을 수 없습니다.")
    if plan.author_id != user.id:
        raise AppError(
            403,
            "community_plan_submit_author_only",
            "공동 기획서를 시작한 학생이 선생님께 최종 승인을 요청할 수 있습니다.",
        )
    if plan.status not in PLAN_STATUSES_EDITABLE:
        raise AppError(409, "community_plan_not_submittable", "현재 승인 요청을 보낼 수 없습니다.")
    if data.base_version != plan.version:
        raise AppError(
            409,
            "community_plan_version_conflict",
            "다른 사람이 먼저 수정했습니다. 최신 기획서를 다시 열어 주세요.",
        )
    if not plan_is_complete(plan):
        raise AppError(422, "community_plan_incomplete", "기획서의 모든 항목과 담당자를 작성해 주세요.")

    plan.status = "IN_REVIEW"
    plan.submitted_at = datetime.now(UTC)
    plan.submitted_by = user.id
    plan.review_note = None
    await db.commit()
    await db.refresh(plan)
    teacher_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == user.term_id,
                    User.role == Role.TEACHER,
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    if teacher_ids:
        await create_notifications(
            db,
            teacher_ids,
            notification_type="COMMUNITY_PLAN_REVIEW_REQUESTED",
            title="행사 기획서 승인 요청이 도착했습니다",
            content=f"{post.title} 공동 기획서를 검토해 주세요.",
            target_type="community",
            target_id=post.id,
        )
    return plan_out(plan, post, user)


@router.post("/{post_id}/plan/review", response_model=CommunityEventPlanOut)
async def review_community_plan(
    post_id: uuid.UUID,
    data: CommunityPlanReviewIn,
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, teacher, for_update=True)
    plan = await db.scalar(
        select(CommunityEventPlan)
        .where(CommunityEventPlan.post_id == post.id)
        .with_for_update()
    )
    if not plan or plan.status != "IN_REVIEW":
        raise AppError(409, "community_plan_not_in_review", "승인 대기 중인 기획서가 아닙니다.")
    note = data.note.strip() if data.note else None
    if data.action in {"REQUEST_CHANGES", "REJECT"} and not note:
        raise AppError(422, "community_plan_review_note_required", "수정할 내용을 적어 주세요.")

    if data.action == "APPROVE":
        plan.status = "APPROVED"
        plan.approved_at = datetime.now(UTC)
        plan.approved_by = teacher.id
        notification_type = "COMMUNITY_PLAN_APPROVED"
        title = "행사 기획서가 승인되었습니다"
    elif data.action == "REQUEST_CHANGES":
        plan.status = "CHANGES_REQUESTED"
        plan.approved_at = None
        plan.approved_by = None
        notification_type = "COMMUNITY_PLAN_CHANGES_REQUESTED"
        title = "행사 기획서 수정 요청이 도착했습니다"
    else:
        plan.status = "REJECTED"
        plan.approved_at = None
        plan.approved_by = None
        notification_type = "COMMUNITY_PLAN_REJECTED"
        title = "행사 기획서가 반려되었습니다"
    plan.review_note = note
    await db.commit()
    await db.refresh(plan)

    if data.action == "APPROVE" and not post.converted_event_id:
        first_operation_date = plan.operation_dates[0]
        event_date = (
            first_operation_date
            if isinstance(first_operation_date, date)
            else date.fromisoformat(str(first_operation_date))
        )
        await convert_community_post_to_event(
            post.id,
            CommunityEventConversionIn(
                event_date=event_date,
                location=(plan.location_plan or "")[:200] or None,
            ),
            teacher,
            db,
        )

    contributor_ids = set(
        (
            await db.scalars(
                select(CommunityPlanRevision.editor_id).where(
                    CommunityPlanRevision.plan_id == plan.id
                )
            )
        ).all()
    )
    contributor_ids.add(plan.author_id)
    await create_notifications(
        db,
        contributor_ids,
        notification_type=notification_type,
        title=title,
        content=note or f"{post.title} 기획서 검토가 끝났습니다.",
        target_type="community",
        target_id=post.id,
    )
    return plan_out(plan, post, teacher)


@router.put("/{post_id}/recommendation", response_model=CommunityPostOut)
async def toggle_community_recommendation(
    post_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, user)
    recommendation = await db.scalar(
        select(CommunityRecommendation).where(
            CommunityRecommendation.post_id == post.id,
            CommunityRecommendation.user_id == user.id,
        )
    )
    if recommendation:
        await db.execute(
            delete(CommunityRecommendation).where(
                CommunityRecommendation.id == recommendation.id
            )
        )
    else:
        db.add(CommunityRecommendation(post_id=post.id, user_id=user.id))
    await db.flush()
    promoted = await promote_to_agenda(db, post)
    await db.commit()
    if promoted:
        await notify_agenda_managers(db, post)
        await db.refresh(post)
    return (await serialize_posts(db, [post], user))[0]


@router.put("/{post_id}/test-recommendation-count", response_model=CommunityPostOut)
async def set_test_recommendation_count(
    post_id: uuid.UUID,
    data: CommunityRecommendationCountIn,
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    if settings.app_env.lower() in {"production", "prod"}:
        raise AppError(404, "not_found", "요청한 기능을 찾을 수 없습니다.")
    post = await get_post(db, post_id, teacher, for_update=True)
    actual_count = (
        await db.scalar(
            select(func.count())
            .select_from(CommunityRecommendation)
            .where(CommunityRecommendation.post_id == post.id)
        )
        or 0
    )
    post.test_recommendation_bonus = max(0, data.count - actual_count)
    promoted = await promote_to_agenda(db, post)
    await db.commit()
    if promoted:
        await notify_agenda_managers(db, post)
    await db.refresh(post)
    return (await serialize_posts(db, [post], teacher))[0]


@router.post("/{post_id}/convert-to-event", response_model=CommunityPostOut)
async def convert_community_post_to_event(
    post_id: uuid.UUID,
    data: CommunityEventConversionIn,
    actor: User = Depends(event_manager),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, actor, for_update=True)
    if post.converted_event_id:
        raise AppError(409, "community_post_already_converted", "이미 행사로 전환된 아이디어입니다.")
    if data.starts_at and data.ends_at and data.ends_at <= data.starts_at:
        raise AppError(422, "invalid_event_time", "종료 시간은 시작 시간보다 늦어야 합니다.")

    plan = await db.scalar(
        select(CommunityEventPlan).where(CommunityEventPlan.post_id == post.id)
    )
    if not plan or plan.status != "APPROVED":
        raise AppError(
            409,
            "community_plan_approval_required",
            "담당 선생님이 승인한 기획서만 행사로 전환할 수 있습니다.",
        )
    if (
        not plan.team_manager_id
        or (plan.poster_required and not plan.poster_manager_id)
        or not plan.operation_days
        or not plan.operation_dates
        or not plan.teams_per_day
        or not plan.people_per_team
        or not plan.team_role_description
        or not plan.team_requirements
    ):
        raise AppError(
            409,
            "community_plan_required",
            "상세 기획서와 조 편성 인원·역할, 담당자를 먼저 정해 주세요.",
        )

    participant_ids = list(
        (
            await db.scalars(
                select(User.id).where(
                    User.term_id == actor.term_id,
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    event = Event(
        term_id=actor.term_id,
        title=post.title,
        type=EventType.EVENT,
        description="\n\n".join(
            value
            for value in [
                f"행사 목적\n{plan.purpose}" if plan.purpose else None,
                (
                    f"참여 대상\n{plan.target_participants}"
                    if plan.target_participants
                    else None
                ),
                f"진행 일정\n{plan.schedule_plan}" if plan.schedule_plan else None,
                f"세부 프로그램\n{plan.program_plan}" if plan.program_plan else None,
                f"역할 분담\n{plan.role_plan}" if plan.role_plan else None,
                f"예산과 준비물\n{plan.budget_plan}" if plan.budget_plan else None,
                f"안전 계획\n{plan.safety_plan}" if plan.safety_plan else None,
            ]
            if value
        )
        or post.content
        or None,
        location=data.location.strip() if data.location else None,
        event_date=data.event_date,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        department_id=actor.department_id if actor.role == Role.DEPARTMENT_HEAD else None,
        manager_id=actor.id,
        status="PLANNED",
    )
    db.add(event)
    await db.flush()
    db.add_all(
        [EventParticipant(event_id=event.id, user_id=user_id) for user_id in participant_ids]
    )
    local_zone = ZoneInfo(settings.default_timezone)
    team_task = await db.get(Task, plan.team_task_id) if plan.team_task_id else None
    if not team_task:
        team_task = Task(
        term_id=actor.term_id,
        event_id=event.id,
        title=f"{post.title} 조 편성",
        description=(
            "기획서에 맞춰 참가 인원을 조로 나누고 활동 날짜를 정해 주세요.\n\n"
            f"역할 계획\n{plan.role_plan}"
        ),
        type=TaskType.TEAM_FORMATION,
        status=TaskStatus.TODO,
        due_at=datetime.combine(
            data.event_date - timedelta(days=7), time(18, 0), tzinfo=local_zone
        ),
        operation_days=plan.operation_days,
        teams_per_day=plan.teams_per_day,
        people_per_team=plan.people_per_team,
        team_role_description=plan.team_role_description,
        team_requirements=plan.team_requirements,
        operation_dates=plan.operation_dates,
        created_by=actor.id,
        )
        db.add(team_task)
        await db.flush()
        plan.team_task_id = team_task.id
    team_task.event_id = event.id
    team_task.due_at = datetime.combine(
        data.event_date - timedelta(days=7), time(18, 0), tzinfo=local_zone
    )
    team_task.created_by = actor.id
    poster_task = None
    if plan.poster_required:
        poster_task = await db.get(Task, plan.poster_task_id) if plan.poster_task_id else None
        if not poster_task:
            poster_task = Task(
                term_id=actor.term_id,
                event_id=event.id,
                title=f"{post.title} 포스터 제출",
                description=(
                    "행사 포스터를 완성해 파일로 제출해 주세요. 제출한 파일은 담당 선생님도 확인합니다.\n\n"
                    f"행사 목적\n{plan.purpose}\n\n세부 프로그램\n{plan.program_plan}"
                ),
                type=TaskType.SUBMISSION,
                status=TaskStatus.TODO,
                due_at=datetime.combine(
                    data.event_date - timedelta(days=10), time(18, 0), tzinfo=local_zone
                ),
                created_by=actor.id,
            )
            db.add(poster_task)
            await db.flush()
            plan.poster_task_id = poster_task.id
        poster_task.event_id = event.id
        poster_task.due_at = datetime.combine(
            data.event_date - timedelta(days=10), time(18, 0), tzinfo=local_zone
        )
        poster_task.created_by = actor.id
    await db.execute(delete(TaskAssignee).where(TaskAssignee.task_id == team_task.id))
    db.add(TaskAssignee(task_id=team_task.id, user_id=plan.team_manager_id))
    if poster_task:
        await db.execute(delete(TaskAssignee).where(TaskAssignee.task_id == poster_task.id))
        db.add(TaskAssignee(task_id=poster_task.id, user_id=plan.poster_manager_id))
    post.converted_event_id = event.id
    post.converted_at = datetime.now(UTC)
    post.converted_by = actor.id
    await db.commit()
    await db.refresh(post)
    await create_notifications(
        db,
        {plan.team_manager_id},
        notification_type="TEAM_FORMATION_ASSIGNED",
        title="행사 조 편성을 맡아 주세요",
        content=f"{post.title} 참가 인원의 조를 편성하고 활동 일정을 정해 주세요.",
        target_type="task",
        target_id=team_task.id,
    )
    if poster_task:
        await create_notifications(
            db,
            {plan.poster_manager_id},
            notification_type="POSTER_ASSIGNED",
            title="행사 포스터 제작을 맡아 주세요",
            content=f"{post.title} 포스터를 완성해 플랫폼에 제출해 주세요.",
            target_type="task",
            target_id=poster_task.id,
        )
    return (await serialize_posts(db, [post], actor))[0]
