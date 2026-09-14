from datetime import date
import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.proposals import (
    confirm_proposal,
    create_proposal,
    create_proposal_feedback,
    create_proposal_version,
    delete_proposal,
    delete_proposal_feedback,
    generate_proposal_summary,
    generate_proposal_plan_from_transcript,
    generate_proposal_meeting_record_draft,
    get_proposal_detail,
    promote_proposal_to_agenda,
    process_proposal_meeting_audio,
    save_proposal_meeting_notes,
    transcribe_proposal_meeting_audio,
    toggle_proposal_recommendation,
    update_proposal_feedback,
)
from app.core.database import Base
from app.core.errors import AppError
from app.core.config import Settings, settings
from app.models.entities import (
    CommunityPost,
    CommunityEventPlan,
    CommunityPlanRevision,
    Notification,
    ProposalAttachment,
    ProposalFeedback,
    ProposalSummary,
    ProposalVersion,
    Role,
    Term,
    User,
)
from app.services.proposal_audio_ai import GeneratedMeetingRecord, GeneratedPlan, ProcessedMeeting
from app.services.proposal_planning import (
    extract_meeting_logistics,
    final_plan_fallback,
    meeting_notes_fallback,
)
from app.services.proposal_summary import summarize_feedback
from app.schemas import (
    ProposalConfirmIn,
    ProposalCreateIn,
    ProposalFeedbackIn,
    ProposalMeetingNotesIn,
    ProposalMeetingRecordDraftIn,
    ProposalVersionCreateIn,
)


async def proposal_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    term = Term(
        name="2026 학생회",
        starts_on=date(2026, 3, 1),
        ends_on=date(2027, 2, 28),
        is_current=True,
    )
    session.add(term)
    await session.flush()
    author = User(
        email="proposal-author@example.com",
        name="제안자",
        password_hash="unused",
        role=Role.MEMBER,
        term_id=term.id,
        is_active=True,
    )
    peer = User(
        email="proposal-peer@example.com",
        name="동료",
        password_hash="unused",
        role=Role.DEPARTMENT_HEAD,
        term_id=term.id,
        is_active=True,
    )
    teacher = User(
        email="proposal-teacher@example.com",
        name="선생님",
        password_hash="unused",
        role=Role.TEACHER,
        term_id=term.id,
        is_active=True,
    )
    session.add_all([author, peer, teacher])
    await session.commit()
    return engine, session, author, peer, teacher


@pytest.mark.asyncio
async def test_proposal_feedback_is_typed_idempotent_and_scoped_to_version():
    engine, db, author, peer, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="조용한 휴게 공간", description="점심시간에 쉴 공간을 만들자."),
            author,
            db,
        )
        first = await create_proposal_feedback(
            proposal.id,
            ProposalFeedbackIn(category="STRENGTH", content="학생들이 잠깐 쉴 수 있어요."),
            "same-request",
            peer,
            db,
        )
        duplicate = await create_proposal_feedback(
            proposal.id,
            ProposalFeedbackIn(category="STRENGTH", content="다른 본문이어도 재전송입니다."),
            "same-request",
            peer,
            db,
        )
        assert duplicate.id == first.id
        assert await db.scalar(select(func.count()).select_from(ProposalFeedback)) == 1

        revised = await create_proposal_version(
            proposal.id,
            ProposalVersionCreateIn(
                title="예약하는 조용한 휴게 공간",
                description="점심시간에 예약제로 운영하고 중앙 통로를 비워 둔다.",
                change_summary="예약 방식과 통로 기준 추가",
                base_version=1,
            ),
            author,
            db,
        )
        second = await create_proposal_feedback(
            proposal.id,
            ProposalFeedbackIn(category="CONCERN", content="예약을 못 한 학생은 이용하기 어려워요."),
            "v2-request",
            peer,
            db,
        )
        detail = await get_proposal_detail(proposal.id, peer, db)
        assert revised.current_version == 2
        assert first.version_number == 1
        assert second.version_number == 2
        assert {item.version_number for item in detail.feedback} == {1, 2}

        with pytest.raises(AppError) as conflict:
            await create_proposal_version(
                proposal.id,
                ProposalVersionCreateIn(
                    title="충돌 버전",
                    description="오래된 화면에서 저장한 내용",
                    change_summary="충돌",
                    base_version=1,
                ),
                peer,
                db,
            )
        assert conflict.value.code == "proposal_version_conflict"
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_feedback_updates_and_deletes_invalidate_fallback_summary_and_permissions():
    engine, db, author, peer, teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="교내 교환함", description="사용하지 않는 학용품을 교환하자."),
            author,
            db,
        )
        feedback = await create_proposal_feedback(
            proposal.id,
            ProposalFeedbackIn(category="NEW_IDEA", content="QR로 물품 목록을 확인해요."),
            None,
            peer,
            db,
        )
        summary = await generate_proposal_summary(proposal.id, author, db)
        assert summary.provider == "fallback"
        assert summary.new_ideas == ["QR로 물품 목록을 확인해요."]

        with pytest.raises(AppError) as forbidden:
            await update_proposal_feedback(
                proposal.id,
                feedback.id,
                ProposalFeedbackIn(category="CHANGE", content="장소를 바꿔요."),
                author,
                db,
            )
        assert forbidden.value.code == "proposal_feedback_author_only"

        await update_proposal_feedback(
            proposal.id,
            feedback.id,
            ProposalFeedbackIn(category="CHANGE", content="분실물 보관함 옆으로 장소를 바꿔요."),
            peer,
            db,
        )
        assert await db.scalar(select(func.count()).select_from(ProposalSummary)) == 0
        updated_summary = await generate_proposal_summary(proposal.id, peer, db)
        assert updated_summary.changes == ["분실물 보관함 옆으로 장소를 바꿔요."]

        await delete_proposal_feedback(proposal.id, feedback.id, peer, db)
        final_summary = await generate_proposal_summary(proposal.id, author, db)
        assert final_summary.changes == []

        with pytest.raises(AppError) as confirm_forbidden:
            await confirm_proposal(
                proposal.id, ProposalConfirmIn(base_version=1), peer, db
            )
        assert confirm_forbidden.value.code == "proposal_confirm_forbidden"
        confirmed = await confirm_proposal(
            proposal.id, ProposalConfirmIn(base_version=1), teacher, db
        )
        assert confirmed.status == "CONFIRMED"
    finally:
        await db.close()
        await engine.dispose()


def test_feedback_category_validation():
    with pytest.raises(ValidationError):
        ProposalFeedbackIn(category="LIKE", content="잘했어요")


def test_openrouter_environment_names_configure_proposal_ai():
    configured = Settings(
        OPENROUTER_API_KEY="test-key",
        OPENROUTER_BASE_URL="https://openrouter.example/api/v1",
        OPENROUTER_MODEL="provider/test-model",
    )
    assert configured.proposal_ai_api_key == "test-key"
    assert configured.proposal_ai_base_url == "https://openrouter.example/api/v1"
    assert configured.proposal_ai_model == "provider/test-model"


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    response: FakeResponse | None = None
    error: Exception | None = None
    request_kwargs: dict | None = None

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *_args, **_kwargs):
        self.__class__.request_kwargs = _kwargs
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.mark.asyncio
async def test_ai_summary_handles_success_malformed_timeout_and_feedback_counts(monkeypatch):
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", None)
    empty = await summarize_feedback([])
    one = await summarize_feedback([{"category": "STRENGTH", "content": "실행하기 쉬워요."}])
    many = await summarize_feedback([
        {"category": "STRENGTH", "content": "실행하기 쉬워요."},
        {"category": "CONCERN", "content": "담당자 확인이 필요해요."},
        {"category": "NEW_IDEA", "content": "점검표를 추가해요."},
    ])
    assert empty.strengths == []
    assert one.strengths == ["실행하기 쉬워요."]
    assert many.open_questions == ["담당자 확인이 필요해요."]

    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured")
    monkeypatch.setattr(settings, "proposal_ai_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "proposal_ai_model", "provider/test-model:free")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    FakeClient.error = None
    FakeClient.response = FakeResponse({
        "choices": [{"message": {"content": "```json\n" + json.dumps({
            "strengths": ["명확함"], "concerns": [], "changes": ["일정 보완"],
            "newIdeas": [], "openQuestions": ["담당자는 누구인가요?"],
        }, ensure_ascii=False) + "\n```"}}]
    })
    success = await summarize_feedback([{"category": "CHANGE", "content": "일정을 보완해요."}])
    assert success.provider == "ai"
    assert success.changes == ["일정 보완"]
    request = FakeClient.request_kwargs
    assert request is not None
    assert "의견 문장을 그대로 나열하지 말고" in request["json"]["messages"][0]["content"]
    assert request["json"]["response_format"] == {"type": "json_object"}

    FakeClient.response = FakeResponse({"choices": [{"message": {"content": "not-json"}}]})
    malformed = await summarize_feedback([{"category": "CHANGE", "content": "일정을 보완해요."}])
    assert malformed.provider == "fallback"
    assert malformed.changes == ["일정을 보완해요."]

    FakeClient.error = httpx.ReadTimeout("summary timeout")
    timeout = await summarize_feedback([{"category": "CONCERN", "content": "시간이 필요해요."}])
    assert timeout.provider == "fallback"
    assert timeout.concerns == ["시간이 필요해요."]


@pytest.mark.asyncio
async def test_agenda_transition_reuses_event_plan_and_creates_grounded_brief(monkeypatch):
    engine, db, author, head, _teacher = await proposal_fixture()
    try:
        monkeypatch.setattr(settings, "proposal_ai_enabled", False)
        proposal = await create_proposal(
            ProposalCreateIn(title="아침 음악 방송", description="등교 시간에 신청곡을 재생하자."),
            author,
            db,
        )
        await create_proposal_feedback(
            proposal.id,
            ProposalFeedbackIn(category="CONCERN", content="방송 음량 확인이 필요해요."),
            "agenda-feedback",
            head,
            db,
        )

        workflow = await promote_proposal_to_agenda(proposal.id, head, db)

        plan = await db.scalar(
            select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
        )
        assert workflow.stage == "MEETING_AGENDA"
        assert workflow.brief_plan["title"] == "아침 음악 방송"
        assert workflow.brief_plan["opinion_summary"]["concerns"] == [
            "방송 음량 확인이 필요해요."
        ]
        assert plan is not None
        assert plan.poster_required is False
        assert plan.author_id == author.id
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_audio_processing_endpoint_fills_existing_plan_and_records_revision(
    monkeypatch, tmp_path
):
    engine, db, author, head, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="안전 캠페인", description="체험형 안전 캠페인을 열자."),
            author,
            db,
        )
        await promote_proposal_to_agenda(proposal.id, head, db)
        version = await db.scalar(
            select(ProposalVersion).where(ProposalVersion.post_id == proposal.id)
        )
        plan = await db.scalar(
            select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
        )
        attachment = ProposalAttachment(
            proposal_version_id=version.id,
            original_name="meeting.mp3",
            storage_key="test/meeting.mp3",
            mime_type="audio/mpeg",
            size=10,
            purpose="MEETING_AUDIO",
            uploaded_by=head.id,
        )
        db.add(attachment)
        await db.flush()
        plan.meeting_attachment_id = attachment.id
        await db.commit()
        audio_path = tmp_path / "meeting.mp3"
        audio_path.write_bytes(b"fake-audio")

        async def fake_process_meeting_audio(**_kwargs):
            return ProcessedMeeting(
                transcript="9월 18일 점심시간에 진행하기로 결정했다.",
                meeting_notes={
                    "summary": "일정과 조 구성을 정했다.",
                    "decisions": ["9월 18일 진행"],
                    "unresolved": [],
                    "source": "whisper_llm",
                },
                plan_document={"title": "안전 캠페인", **generated_plan_for_endpoint()},
                transcription_provider="whisper",
                plan_provider="ai",
            )

        monkeypatch.setattr("app.api.proposals.storage.path", lambda _key: audio_path)
        monkeypatch.setattr(
            "app.api.proposals.process_meeting_audio", fake_process_meeting_audio
        )

        workflow = await process_proposal_meeting_audio(proposal.id, head, db)
        await db.refresh(plan)

        assert workflow.stage == "FINAL_PLAN_DRAFT"
        assert workflow.meeting_transcript.startswith("9월 18일")
        assert plan.purpose == "교내 안전 수칙을 알린다."
        assert plan.operation_dates == ["2026-09-18"]
        assert plan.team_requirements[0]["name"] == "안내조"
        assert plan.transcription_provider == "whisper"
        assert plan.ai_provider == "ai"
        assert plan.version == 2
        assert await db.scalar(
            select(func.count()).select_from(CommunityPlanRevision)
        ) == 1
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_whisper_preview_is_saved_before_separate_plan_generation(monkeypatch, tmp_path):
    engine, db, author, head, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="안전 캠페인", description="체험형 안전 캠페인을 열자."),
            author,
            db,
        )
        await promote_proposal_to_agenda(proposal.id, head, db)
        version = await db.scalar(
            select(ProposalVersion).where(ProposalVersion.post_id == proposal.id)
        )
        plan = await db.scalar(
            select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
        )
        attachment = ProposalAttachment(
            proposal_version_id=version.id,
            original_name="meeting.mp3",
            storage_key="test/preview.mp3",
            mime_type="audio/mpeg",
            size=10,
            purpose="MEETING_AUDIO",
            uploaded_by=head.id,
        )
        db.add(attachment)
        await db.flush()
        plan.meeting_attachment_id = attachment.id
        await db.commit()
        audio_path = tmp_path / "meeting.mp3"
        audio_path.write_bytes(b"fake-audio")

        async def fake_transcribe_audio(*_args, **_kwargs):
            return "Whisper가 인식한 요약 전 원문입니다."

        async def fake_generate_plan_json(**_kwargs):
            return GeneratedPlan.model_validate(generated_plan_for_endpoint())

        monkeypatch.setattr("app.api.proposals.storage.path", lambda _key: audio_path)
        monkeypatch.setattr("app.api.proposals.transcribe_audio", fake_transcribe_audio)
        monkeypatch.setattr(
            "app.api.proposals.generate_plan_json", fake_generate_plan_json
        )

        preview = await transcribe_proposal_meeting_audio(proposal.id, head, db)
        await db.refresh(plan)
        assert preview.meeting_transcript == "Whisper가 인식한 요약 전 원문입니다."
        assert preview.meeting_notes is None
        assert preview.final_plan is None
        assert plan.transcription_provider == "whisper"

        generated = await generate_proposal_plan_from_transcript(
            proposal.id,
            ProposalMeetingNotesIn(
                transcript="사람이 확인하고 오탈자를 고친 전사 원문입니다.",
                manual_notes=None,
            ),
            head,
            db,
        )
        await db.refresh(plan)
        assert generated.stage == "FINAL_PLAN_DRAFT"
        assert plan.meeting_transcript == "사람이 확인하고 오탈자를 고친 전사 원문입니다."
        assert plan.transcription_provider == "manual"
        assert plan.meeting_notes["source"] == "whisper_llm"
        assert plan.final_plan["purpose"] == "교내 안전 수칙을 알린다."
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_transcript_generates_existing_meeting_record_form_json(monkeypatch):
    engine, db, author, head, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="안전 캠페인", description="안전 캠페인을 열자."),
            author,
            db,
        )
        await promote_proposal_to_agenda(proposal.id, head, db)
        received: dict = {}

        async def fake_generate_meeting_record_json(**kwargs):
            received.update(kwargs)
            return GeneratedMeetingRecord(
                title="안전 캠페인 부장 회의",
                held_at=None,
                location="학생회실",
                summary="일정과 운영 방법을 논의했다.",
                decisions="9월 18일에 진행한다.",
                next_actions="안내 문구를 준비한다.",
            )

        monkeypatch.setattr(
            "app.api.proposals.generate_meeting_record_json",
            fake_generate_meeting_record_json,
        )
        draft = await generate_proposal_meeting_record_draft(
            proposal.id,
            ProposalMeetingRecordDraftIn(transcript="회의 음성인식 원문"),
            head,
            db,
        )

        assert draft.title == "안전 캠페인 부장 회의"
        assert draft.decisions == "9월 18일에 진행한다."
        assert received["transcript"] == "회의 음성인식 원문"
        assert received["brief_plan"]["title"] == "안전 캠페인"
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_manual_meeting_result_does_not_require_audio_or_ai():
    engine, db, author, head, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="점심시간 캠페인", description="질서 캠페인을 진행하자."),
            author,
            db,
        )
        await promote_proposal_to_agenda(proposal.id, head, db)

        workflow = await save_proposal_meeting_notes(
            proposal.id,
            ProposalMeetingNotesIn(
                transcript="",
                manual_notes="9월 셋째 주에 진행한다.\n안내 문구는 다음 회의에서 정한다.",
            ),
            head,
            db,
        )
        plan = await db.scalar(
            select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id)
        )

        assert workflow.stage == "MEETING_COMPLETED"
        assert workflow.meeting_audio is None
        assert plan.meeting_notes["source"] == "manual_notes"
        assert plan.transcription_provider == "manual"
        assert plan.ai_provider == "fallback"
    finally:
        await db.close()
        await engine.dispose()


def generated_plan_for_endpoint() -> dict:
    return {
        "meeting_summary": "일정과 조 구성을 정했다.",
        "decisions": ["9월 18일 진행"],
        "unresolved": [],
        "purpose": "교내 안전 수칙을 알린다.",
        "target_participants": "전교생",
        "schedule_plan": "2026년 9월 18일 점심시간",
        "location_plan": "체육관",
        "program_plan": "안전 퀴즈를 운영한다.",
        "role_plan": "안내조가 동선을 안내한다.",
        "budget_plan": "",
        "safety_plan": "출입 동선을 분리한다.",
        "operation_dates": ["2026-09-18"],
        "team_requirements": [
            {"name": "안내조", "people_count": 2, "role_description": "동선 안내"}
        ],
    }


def test_meeting_and_final_fallback_never_invent_decisions_or_execution_values():
    notes = meeting_notes_fallback(
        "운영 시간은 추후 확인\n안전 담당자를 다시 정하기",
        None,
    )
    final = final_plan_fallback(
        title="안전 캠페인",
        brief={"purpose": "안전 수칙을 알린다."},
        meeting_notes=notes,
    )

    assert notes["decisions"] == []
    assert notes["unresolved"] == ["운영 시간은 추후 확인", "안전 담당자를 다시 정하기"]
    assert final["operation_dates"] == []
    assert final["team_requirements"] == []
    assert final["budget_plan"] == ""


def test_meeting_logistics_extracts_date_times_and_required_people():
    logistics = extract_meeting_logistics(
        "9월 25일에 등교조와 하교조가 각각 3명씩 맡는다. "
        "등교는 07:40~08:30, 하교는 15:20~16:20 운영한다.",
        default_year=2026,
    )

    assert logistics["operation_dates"] == ["2026-09-25"]
    assert logistics["team_requirements"] == [
        {
            "name": "등교조",
            "people_count": 3,
            "role_description": "등교조 운영",
            "start_time": "07:40",
            "end_time": "08:30",
        },
        {
            "name": "하교조",
            "people_count": 3,
            "role_description": "하교조 운영",
            "start_time": "15:20",
            "end_time": "16:20",
        },
    ]


@pytest.mark.asyncio
async def test_proposal_recommendation_is_visible_and_toggleable():
    engine, db, author, peer, _teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="우산 대여", description="비 오는 날 공용 우산을 빌려주자."),
            author,
            db,
        )
        recommended = await toggle_proposal_recommendation(proposal.id, peer, db)
        assert recommended.recommendation_count == 1
        assert recommended.recommended_by_me is True
        removed = await toggle_proposal_recommendation(proposal.id, peer, db)
        assert removed.recommendation_count == 0
        assert removed.recommended_by_me is False
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_feedback_request_does_not_block_agenda_before_every_student_responds():
    engine, db, author, peer, teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="교내 우산 대여", description="공용 우산 대여함을 운영하자."),
            author,
            db,
        )
        post = await db.get(CommunityPost, proposal.id)
        assert post is not None
        post.test_recommendation_bonus = 12
        await db.commit()

        required = await toggle_proposal_recommendation(proposal.id, peer, db)
        assert required.recommendation_count == 13
        assert required.feedback_required is True
        assert required.required_feedback_recommendation_threshold == 13
        assert required.required_feedback_count == 2
        assert required.completed_required_feedback_count == 0
        assert required.is_current_user_feedback_required is True

        notified_ids = set(
            (
                await db.scalars(
                    select(Notification.user_id).where(
                        Notification.type == "PROPOSAL_FEEDBACK_REQUIRED",
                        Notification.target_id == proposal.id,
                    )
                )
            ).all()
        )
        assert notified_ids == {author.id, peer.id}
        assert teacher.id not in notified_ids

        still_required = await toggle_proposal_recommendation(proposal.id, peer, db)
        assert still_required.recommendation_count == 12
        assert still_required.feedback_required is True

        workflow = await promote_proposal_to_agenda(proposal.id, author, db)
        assert workflow.stage == "MEETING_AGENDA"

        advanced = await get_proposal_detail(proposal.id, author, db)
        assert advanced.status == "CONFIRMED"
        assert advanced.completed_required_feedback_count == 0
    finally:
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_teacher_can_edit_confirmed_proposal_and_delete_any_proposal():
    engine, db, author, peer, teacher = await proposal_fixture()
    try:
        proposal = await create_proposal(
            ProposalCreateIn(title="급식 의견함", description="급식 의견을 정기적으로 모으자."),
            author,
            db,
        )
        confirmed = await confirm_proposal(
            proposal.id, ProposalConfirmIn(base_version=1), teacher, db
        )
        assert confirmed.status == "CONFIRMED"
        assert confirmed.can_edit is True
        assert confirmed.can_delete is True

        revised = await create_proposal_version(
            proposal.id,
            ProposalVersionCreateIn(
                title="급식 의견함 운영",
                description="급식 의견을 매달 정기적으로 모으자.",
                base_version=1,
                change_summary="교사가 운영 주기를 명확히 함",
            ),
            teacher,
            db,
        )
        assert revised.current_version == 2
        assert revised.status == "RE_REVIEW"

        with pytest.raises(AppError) as forbidden:
            await delete_proposal(proposal.id, peer, db)
        assert forbidden.value.code == "proposal_delete_teacher_only"

        await delete_proposal(proposal.id, teacher, db)
        with pytest.raises(AppError) as missing:
            await get_proposal_detail(proposal.id, teacher, db)
        assert missing.value.code == "proposal_not_found"
    finally:
        await db.close()
        await engine.dispose()
