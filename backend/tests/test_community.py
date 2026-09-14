from datetime import date, time

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.community import (
    assign_community_plan_writer,
    convert_community_post_to_event,
    create_community_comment,
    create_community_plan_suggestion,
    create_community_post,
    delete_community_comment,
    delete_community_post,
    list_community_posts,
    resolve_community_plan_suggestion,
    review_community_plan,
    save_community_event_plan,
    set_community_meeting_schedule,
    set_test_recommendation_count,
    submit_community_plan_for_review,
    toggle_community_recommendation,
    update_community_comment,
    update_community_post,
)
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import (
    Comment,
    CommunityEventPlan,
    CommunityPost,
    CommunityRecommendation,
    Event,
    EventParticipant,
    Notification,
    Role,
    Task,
    TaskAssignee,
    TaskType,
    Term,
    User,
)
from app.schemas import (
    CommunityAgendaScheduleIn,
    CommunityCommentIn,
    CommunityCommentUpdate,
    CommunityEventConversionIn,
    CommunityEventPlanIn,
    CommunityPlanReviewIn,
    CommunityPlanSubmitIn,
    CommunityPlanSuggestionIn,
    CommunityPlanSuggestionResolveIn,
    CommunityPlanWriterIn,
    CommunityPostIn,
    CommunityPostUpdate,
    CommunityRecommendationCountIn,
)


@pytest.mark.asyncio
async def test_event_seed_board_supports_anonymity_stars_ranking_and_event_conversion():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="2026 학생회",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        author = User(
            email="author@example.com",
            name="민준",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        voter = User(
            email="voter@example.com",
            name="서연",
            password_hash="unused",
            role=Role.DEPARTMENT_HEAD,
            term_id=term.id,
        )
        teacher = User(
            email="teacher@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        db.add_all([author, voter, teacher])
        await db.commit()

        anonymous = await create_community_post(
            CommunityPostIn(
                title="점심시간 보물찾기",
                content="운동장과 도서관에 단서를 숨기면 재미있을 것 같아요.",
                is_anonymous=True,
            ),
            author,
            db,
        )
        named = await create_community_post(
            CommunityPostIn(
                title="우산 빌려주기 행사",
                content="비 오는 날 학생회가 우산을 빌려주고 반납을 관리해요.",
                is_anonymous=False,
            ),
            voter,
            db,
        )
        assert anonymous.author_id is None
        assert anonymous.author_name == "익명"
        assert anonymous.is_mine is True
        assert named.author_name == "서연"
        assert named.content.startswith("비 오는 날")

        first_comment = await create_community_comment(
            anonymous.id,
            CommunityCommentIn(content="  단서를 학년별 난이도로 나누면 좋겠어요.  "),
            voter,
            db,
        )
        second_comment = await create_community_comment(
            anonymous.id,
            CommunityCommentIn(content="도서관 담당 선생님께 먼저 여쭤볼게요."),
            author,
            db,
        )
        assert first_comment.author_name == "서연"
        assert first_comment.content == "단서를 학년별 난이도로 나누면 좋겠어요."
        assert second_comment.author_name == "민준"

        edited_comment = await update_community_comment(
            anonymous.id,
            first_comment.id,
            CommunityCommentUpdate(
                content="학년별로 단서 난이도를 나누면 좋겠어요.",
                is_anonymous=True,
            ),
            voter,
            db,
        )
        assert edited_comment.author_name == "익명"
        assert edited_comment.author_id is None
        await delete_community_comment(anonymous.id, second_comment.id, author, db)

        with pytest.raises(AppError) as comment_error:
            await create_community_comment(
                anonymous.id,
                CommunityCommentIn(content="   "),
                voter,
                db,
            )
        assert comment_error.value.status == 422

        starred = await toggle_community_recommendation(anonymous.id, voter, db)
        assert starred.recommendation_count == 1
        assert starred.recommended_by_me is True

        popular = await list_community_posts("popular", voter, db)
        assert [post.id for post in popular] == [anonymous.id, named.id]
        assert popular[0].author_id is None
        assert popular[0].is_mine is False
        assert popular[0].comment_count == 1
        assert [comment.author_name for comment in popular[0].comments] == ["익명"]
        comment_count = await db.scalar(
            select(func.count()).select_from(Comment).where(Comment.deleted_at.is_(None))
        )
        assert comment_count == 1

        unstarred = await toggle_community_recommendation(anonymous.id, voter, db)
        assert unstarred.recommendation_count == 0
        count = await db.scalar(select(func.count()).select_from(CommunityRecommendation))
        assert count == 0

        boosted = await set_test_recommendation_count(
            anonymous.id,
            CommunityRecommendationCountIn(count=10),
            teacher,
            db,
        )
        assert boosted.recommendation_count == 10
        assert boosted.test_recommendation_bonus == 10
        assert boosted.agenda_at is not None

        assigned_writer = await assign_community_plan_writer(
            anonymous.id,
            CommunityPlanWriterIn(writer_id=voter.id),
            teacher,
            db,
        )
        assert assigned_writer.plan_writer_id == voter.id
        assert assigned_writer.plan_writer_name == voter.name
        assert await db.scalar(
            select(Notification.id).where(
                Notification.user_id == voter.id,
                Notification.type == "COMMUNITY_PLAN_WRITER_ASSIGNED",
            )
        )
        scheduled = await set_community_meeting_schedule(
            anonymous.id,
            CommunityAgendaScheduleIn(
                meeting_date=date(2026, 9, 3),
                meeting_time_slot="MORNING",
                meeting_time=time(8, 10),
            ),
            teacher,
            db,
        )
        assert scheduled.meeting_date == date(2026, 9, 3)
        assert scheduled.meeting_time_slot == "MORNING"
        assert scheduled.meeting_time == time(8, 10)
        assert await db.scalar(
            select(Notification.id).where(
                Notification.user_id == voter.id,
                Notification.type == "COMMUNITY_MEETING_SCHEDULED",
            )
        )
        lowered = await set_test_recommendation_count(
            anonymous.id,
            CommunityRecommendationCountIn(count=0),
            teacher,
            db,
        )
        assert lowered.recommendation_count == 0
        assert lowered.agenda_at is not None

        edited_named = await update_community_post(
            named.id,
            CommunityPostUpdate(
                title="우산 공유 행사",
                content="비 오는 날 학생회가 우산 대여와 반납을 관리합니다.",
                is_anonymous=False,
            ),
            teacher,
            db,
        )
        assert edited_named.title == "우산 공유 행사"
        await delete_community_post(named.id, teacher, db)
        assert await db.get(CommunityPost, named.id) is None

        db.add(
            CommunityEventPlan(
                post_id=anonymous.id,
                author_id=voter.id,
                purpose="학생들이 함께 즐기는 점심시간을 만든다.",
                target_participants="전교생",
                schedule_plan="10월 16일 점심시간",
                location_plan="본관과 운동장",
                program_plan="학년별 단서를 찾아 마지막 장소에 모인다.",
                role_plan="조 편성 담당은 참가자를 나누고 포스터 담당은 홍보물을 만든다.",
                budget_plan="인쇄비 3만 원",
                safety_plan="층별 안전 담당자를 둔다.",
                operation_days=2,
                operation_dates=["2026-10-16", "2026-10-17"],
                teams_per_day=2,
                people_per_team=3,
                team_role_description="참가자 확인과 이동 안내",
                team_requirements=[
                    {"name": "안내조", "people_count": 2, "role_description": "정문 안내"},
                    {"name": "안전조", "people_count": 3, "role_description": "이동 안전 확인"},
                ],
                team_manager_id=voter.id,
                poster_manager_id=author.id,
                status="APPROVED",
            )
        )
        await db.commit()

        converted = await convert_community_post_to_event(
            anonymous.id,
            CommunityEventConversionIn(
                event_date=date(2026, 10, 16),
                location="본관과 운동장",
            ),
            teacher,
            db,
        )
        assert converted.converted_event_id is not None
        event = await db.get(Event, converted.converted_event_id)
        assert event is not None
        assert event.title == "점심시간 보물찾기"
        assert event.manager_id == teacher.id
        participant_count = await db.scalar(
            select(func.count())
            .select_from(EventParticipant)
            .where(EventParticipant.event_id == event.id)
        )
        assert participant_count == 3
        tasks = list((await db.scalars(select(Task).where(Task.event_id == event.id))).all())
        assert {task.type for task in tasks} == {
            TaskType.TEAM_FORMATION,
            TaskType.SUBMISSION,
        }
        team_task = next(task for task in tasks if task.type == TaskType.TEAM_FORMATION)
        assert team_task.operation_days == 2
        assert team_task.operation_dates == ["2026-10-16", "2026-10-17"]
        assert team_task.teams_per_day == 2
        assert team_task.people_per_team == 3
        assert team_task.team_role_description == "참가자 확인과 이동 안내"
        assert team_task.team_requirements[1]["people_count"] == 3
        assignees = set(
            (
                await db.scalars(
                    select(TaskAssignee.user_id).where(
                        TaskAssignee.task_id.in_([task.id for task in tasks])
                    )
                )
            ).all()
        )
        assert assignees == {author.id, voter.id}
        notification_types = set((await db.scalars(select(Notification.type))).all())
        assert {"TEAM_FORMATION_ASSIGNED", "POSTER_ASSIGNED"}.issubset(notification_types)

        with pytest.raises(AppError) as error:
            await convert_community_post_to_event(
                anonymous.id,
                CommunityEventConversionIn(event_date=date(2026, 10, 17)),
                teacher,
                db,
            )
        assert error.value.status == 409

    await engine.dispose()


@pytest.mark.asyncio
async def test_comments_support_anonymity_and_ten_recommendations_unlock_author_plan():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="2027 학생회",
            starts_on=date(2027, 1, 1),
            ends_on=date(2027, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        author = User(
            email="plan-author@example.com",
            name="지민",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        commenter = User(
            email="plan-commenter@example.com",
            name="하준",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        teacher = User(
            email="plan-teacher@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        voters = [
            User(
                email=f"plan-voter-{index}@example.com",
                name=f"추천인 {index}",
                password_hash="unused",
                role=Role.MEMBER,
                term_id=term.id,
            )
            for index in range(10)
        ]
        db.add_all([author, commenter, teacher, *voters])
        await db.commit()

        post = await create_community_post(
            CommunityPostIn(
                title="학교 축제 미션 투어",
                content="축제 날 교실별 미션을 수행하고 마지막 장소에 함께 모여요.",
                is_anonymous=True,
            ),
            author,
            db,
        )
        anonymous_comment = await create_community_comment(
            post.id,
            CommunityCommentIn(content="교실마다 다른 미션을 두면 좋겠어요.", is_anonymous=True),
            commenter,
            db,
        )
        named_comment = await create_community_comment(
            post.id,
            CommunityCommentIn(content="방송부와 협업할 수 있어요.", is_anonymous=False),
            author,
            db,
        )
        assert anonymous_comment.author_id is None
        assert anonymous_comment.author_name == "익명"
        assert anonymous_comment.is_anonymous is True
        assert anonymous_comment.is_mine is True
        assert named_comment.author_id == author.id
        assert named_comment.author_name == "지민"

        plan_data = CommunityEventPlanIn(
            purpose="학생들이 학년을 넘어 협력할 기회를 만든다.",
            target_participants="전교생",
            schedule_plan="축제일 10:00부터 12:00까지",
            location_plan="본관 교실과 운동장",
            program_plan="조별로 교실 미션을 수행하고 마지막에 운동장에 모인다.",
            role_plan="기획팀은 미션, 홍보팀은 포스터, 안전팀은 동선을 담당한다.",
            budget_plan="인쇄비와 미션 재료비 8만 원",
            safety_plan="계단 이동 인원을 제한하고 층별 안전 담당자를 배치한다.",
            operation_days=2,
            operation_dates=[date(2026, 10, 16), date(2026, 10, 17)],
            teams_per_day=3,
            people_per_team=4,
            team_role_description="교실 미션 안내와 이동 안전 확인",
            team_requirements=[
                {"name": "미션조", "people_count": 4, "role_description": "교실 미션 안내"},
                {"name": "안전조", "people_count": 2, "role_description": "이동 안전 확인"},
            ],
            team_manager_id=commenter.id,
            poster_manager_id=author.id,
        )
        with pytest.raises(AppError) as locked_error:
            await save_community_event_plan(post.id, plan_data, author, db)
        assert locked_error.value.status == 403

        for voter in voters:
            await toggle_community_recommendation(post.id, voter, db)

        saved_plan = await save_community_event_plan(post.id, plan_data, author, db)
        assert saved_plan.author_id == author.id
        assert saved_plan.target_participants == "전교생"
        assert saved_plan.status == "DRAFT"
        assert saved_plan.version == 1
        assert "proposal_deadline" not in type(saved_plan).model_fields
        plan_count = await db.scalar(select(func.count()).select_from(CommunityEventPlan))
        assert plan_count == 1
        assert await db.scalar(select(func.count()).select_from(Task)) == 0
        with pytest.raises(AppError) as approval_required:
            await convert_community_post_to_event(
                post.id,
                CommunityEventConversionIn(event_date=date(2026, 10, 16)),
                teacher,
                db,
            )
        assert approval_required.value.code == "community_plan_approval_required"

        author_view = (await list_community_posts("popular", author, db))[0]
        assert author_view.recommendation_count == 10
        assert author_view.can_write_plan is True
        assert author_view.plan is not None
        assert author_view.comments[0].author_id is None
        assert author_view.comments[0].author_name == "익명"
        assert author_view.comments[0].is_mine is False
        assert author_view.comments[1].is_mine is True

        commenter_view = (await list_community_posts("popular", commenter, db))[0]
        assert commenter_view.can_write_plan is True
        assert commenter_view.plan is not None
        collaborator_update = plan_data.model_copy(
            update={
                "base_version": saved_plan.version,
                "purpose": "학생들이 학년을 넘어 함께 협력하는 축제를 만든다.",
            }
        )
        collaborated = await save_community_event_plan(
            post.id, collaborator_update, commenter, db
        )
        assert collaborated.version == 2
        assert collaborated.purpose == "학생들이 학년을 넘어 함께 협력하는 축제를 만든다."

        suggestion = await create_community_plan_suggestion(
            post.id,
            CommunityPlanSuggestionIn(
                section="safety_plan",
                proposed_content="계단 이동 인원을 제한하고 층별 안전 담당자와 비상 연락망을 둔다.",
                reason="비상 상황 연락 방법이 필요해요.",
            ),
            commenter,
            db,
        )
        workspace = await resolve_community_plan_suggestion(
            post.id,
            suggestion.id,
            CommunityPlanSuggestionResolveIn(
                action="ADOPT", base_version=collaborated.version
            ),
            author,
            db,
        )
        assert workspace.plan.version == 3
        assert workspace.suggestions[0].status == "ADOPTED"
        assert {item.name for item in workspace.contributors} == {"지민", "하준"}

        submitted = await submit_community_plan_for_review(
            post.id,
            CommunityPlanSubmitIn(base_version=workspace.plan.version),
            author,
            db,
        )
        assert submitted.status == "IN_REVIEW"
        assert submitted.can_edit is False

        rejected = await review_community_plan(
            post.id,
            CommunityPlanReviewIn(
                action="REJECT", note="운영 근거를 보완해 다시 제출해 주세요."
            ),
            teacher,
            db,
        )
        assert rejected.status == "REJECTED"
        await submit_community_plan_for_review(
            post.id,
            CommunityPlanSubmitIn(base_version=rejected.version),
            author,
            db,
        )

        changes_requested = await review_community_plan(
            post.id,
            CommunityPlanReviewIn(
                action="REQUEST_CHANGES", note="우천 시 실내 대체 장소를 적어 주세요."
            ),
            teacher,
            db,
        )
        assert changes_requested.status == "CHANGES_REQUESTED"
        assert changes_requested.review_note == "우천 시 실내 대체 장소를 적어 주세요."

        revised = await save_community_event_plan(
            post.id,
            plan_data.model_copy(
                update={
                    "base_version": changes_requested.version,
                    "location_plan": "본관 교실과 운동장, 우천 시 체육관",
                }
            ),
            commenter,
            db,
        )
        resubmitted = await submit_community_plan_for_review(
            post.id,
            CommunityPlanSubmitIn(base_version=revised.version),
            author,
            db,
        )
        approved = await review_community_plan(
            post.id,
            CommunityPlanReviewIn(action="APPROVE"),
            teacher,
            db,
        )
        assert resubmitted.status == "IN_REVIEW"
        assert approved.status == "APPROVED"
        assert approved.can_convert is False
        stored_post = await db.get(CommunityPost, post.id)
        assert stored_post is not None
        assert stored_post.converted_event_id is not None
        event = await db.get(Event, stored_post.converted_event_id)
        assert event is not None
        assert event.event_date == date(2026, 10, 16)
        assert event.location == "본관 교실과 운동장, 우천 시 체육관"
        assert "학생들이 학년을 넘어 협력" in (event.description or "")
        event_tasks = list(
            (await db.scalars(select(Task).where(Task.event_id == event.id))).all()
        )
        assert {task.type for task in event_tasks} == {
            TaskType.TEAM_FORMATION,
            TaskType.SUBMISSION,
        }
        team_task = next(task for task in event_tasks if task.type == TaskType.TEAM_FORMATION)
        assert team_task.operation_dates == ["2026-10-16", "2026-10-17"]
        assert await db.scalar(
            select(TaskAssignee.id).where(
                TaskAssignee.task_id == team_task.id,
                TaskAssignee.user_id == commenter.id,
            )
        )

    await engine.dispose()


@pytest.mark.asyncio
async def test_any_student_can_start_plan_for_teacher_post_after_ten_recommendations():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="2028 학생회",
            starts_on=date(2028, 1, 1),
            ends_on=date(2028, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="teacher-post@example.com",
            name="테스트 관리자",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        student = User(
            email="student-planner@example.com",
            name="공동 기획 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, student])
        await db.commit()

        post = await create_community_post(
            CommunityPostIn(
                title="거북이 보호 행사",
                content="학교 주변 생태를 조사하고 보호 방법을 함께 알립니다.",
            ),
            teacher,
            db,
        )
        await set_test_recommendation_count(
            post.id, CommunityRecommendationCountIn(count=10), teacher, db
        )

        student_view = (await list_community_posts("popular", student, db))[0]
        assert student_view.can_write_plan is True
        started = await save_community_event_plan(
            post.id,
            CommunityEventPlanIn(purpose="학생들이 생태 보호 방법을 배운다."),
            student,
            db,
        )
        assert started.author_id == student.id
        assert started.can_edit is True

        teacher_view = (await list_community_posts("popular", teacher, db))[0]
        assert teacher_view.can_write_plan is False
        assert teacher_view.plan is not None
        assert teacher_view.plan.can_review is False

    await engine.dispose()
