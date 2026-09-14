import json

import httpx
import pytest

from app.core.config import settings
from app.services.proposal_audio_ai import (
    ProposalAIError,
    generate_brief_plan_json,
    generate_meeting_record_json,
    process_meeting_audio,
    transcribe_audio,
)


class QueuedResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class RejectedResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.payload = payload

    def raise_for_status(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/audio/transcriptions")
        response = httpx.Response(self.status_code, request=request, json=self.payload)
        raise httpx.HTTPStatusError("rejected", request=request, response=response)

    def json(self):
        return self.payload


class QueuedClient:
    responses: list[QueuedResponse] = []
    requests: list[tuple[str, dict]] = []

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url: str, **kwargs):
        self.requests.append((url, kwargs))
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def use_api_transcription_by_default(monkeypatch):
    monkeypatch.setattr(settings, "proposal_transcription_provider", "api")


@pytest.fixture(autouse=True)
def use_openai_responses_base(monkeypatch):
    monkeypatch.setattr(settings, "proposal_ai_base_url", "https://api.openai.com/v1")


def generated_plan_payload() -> dict:
    return {
        "meeting_summary": "9월 18일 점심시간에 체육관에서 안전 캠페인을 진행하기로 했다.",
        "decisions": ["9월 18일에 진행한다.", "안내조와 안전조를 운영한다."],
        "unresolved": ["세부 준비물 가격은 추가 확인이 필요하다."],
        "purpose": "교내 안전 수칙을 알린다.",
        "target_participants": "전교생",
        "schedule_plan": "2026년 9월 18일 점심시간",
        "location_plan": "체육관",
        "program_plan": "안전 퀴즈와 체험 부스를 운영한다.",
        "role_plan": "안내조는 동선을 안내하고 안전조는 체험 부스를 관리한다.",
        "budget_plan": "준비물 가격은 추가 확인",
        "safety_plan": "입구와 출구 동선을 분리한다.",
        "operation_dates": ["2026-09-18"],
        "team_requirements": [
            {"name": "안내조", "people_count": 2, "role_description": "참여 동선 안내"},
            {"name": "안전조", "people_count": 3, "role_description": "체험 부스 안전 관리"},
        ],
    }


def generated_brief_payload() -> dict:
    return {
        "title": "안전 캠페인 최신안",
        "background": "체험형 안전 캠페인을 열자는 제안이다.",
        "purpose": "학생들이 안전 수칙을 쉽게 익히게 한다.",
        "main_suggestions": ["안전 퀴즈를 운영한다."],
        "opinion_summary": {
            "supporting_points": ["체험형 방식이 좋다."],
            "concerns": ["점심시간 혼잡이 걱정된다."],
            "changes": ["동선을 나눠야 한다."],
        },
        "expected_date": "",
        "expected_location": "체육관",
        "expected_participants": "전교생",
        "expected_operation": "안전 퀴즈와 체험 부스를 운영한다.",
        "alternatives": ["학년별로 시간을 나눈다."],
        "decision_items": ["진행 날짜를 정해야 한다."],
    }


@pytest.mark.asyncio
async def test_latest_proposal_and_feedback_generate_strict_brief_json(monkeypatch):
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "proposal_transcription_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [
        QueuedResponse({"output_text": json.dumps(generated_brief_payload(), ensure_ascii=False)})
    ]

    brief = await generate_brief_plan_json(
        proposal_title="안전 캠페인 최신안",
        proposal_description="체험형 안전 캠페인으로 내용을 수정했다.",
        feedback=[{"category": "CONCERN", "content": "점심시간 혼잡이 걱정된다."}],
    )

    request = QueuedClient.requests[0][1]["json"]
    source = request["input"][1]["content"][0]["text"]
    assert brief.expected_location == "체육관"
    assert request["text"]["format"]["name"] == "studentflow_brief_plan"
    assert request["text"]["format"]["strict"] is True
    assert "체험형 안전 캠페인으로 내용을 수정했다." in source
    assert "점심시간 혼잡이 걱정된다." in source


@pytest.mark.asyncio
async def test_openrouter_uses_chat_completions_structured_output(monkeypatch):
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "proposal_ai_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [
        QueuedResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(generated_brief_payload(), ensure_ascii=False)
                        }
                    }
                ]
            }
        )
    ]

    brief = await generate_brief_plan_json(
        proposal_title="안전 캠페인 최신안",
        proposal_description="체험형 안전 캠페인으로 내용을 수정했다.",
        feedback=[{"category": "CONCERN", "content": "점심시간 혼잡이 걱정된다."}],
    )

    url, request = QueuedClient.requests[0]
    payload = request["json"]
    assert url.endswith("/chat/completions")
    assert payload["response_format"]["json_schema"]["name"] == "studentflow_brief_plan"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["provider"]["require_parameters"] is True
    assert payload["plugins"] == [{"id": "response-healing"}]
    assert brief.expected_location == "체육관"


@pytest.mark.asyncio
async def test_large_audio_is_transcribed_in_order_with_context(monkeypatch, tmp_path):
    original = tmp_path / "long.m4a"
    original.write_bytes(b"large-audio")
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    chunk_one = chunk_dir / "chunk-000.mp3"
    chunk_two = chunk_dir / "chunk-001.mp3"
    chunk_one.write_bytes(b"first")
    chunk_two.write_bytes(b"second")

    async def fake_split(_path):
        return [chunk_one, chunk_two]

    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "proposal_transcription_chunk_max_bytes", 1)
    monkeypatch.setattr("app.services.proposal_audio_ai._split_audio", fake_split)
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [QueuedResponse({"text": "첫 구간"}), QueuedResponse({"text": "둘째 구간"})]

    transcript = await transcribe_audio(original, filename="long.m4a", mime_type="audio/mp4")

    assert transcript == "첫 구간\n둘째 구간"
    assert QueuedClient.requests[1][1]["data"]["prompt"] == "첫 구간"


@pytest.mark.asyncio
async def test_local_whisper_transcribes_without_external_api(monkeypatch, tmp_path):
    audio_path = tmp_path / "meeting.m4a"
    audio_path.write_bytes(b"local-audio")
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_transcription_provider", "local")
    monkeypatch.setattr(settings, "proposal_local_whisper_model", "small")
    monkeypatch.setattr(
        "app.services.proposal_audio_ai._transcribe_local_sync",
        lambda path: "학생회 로컬 전사 결과" if path == audio_path else "",
    )

    transcript = await transcribe_audio(
        audio_path, filename="meeting.m4a", mime_type="audio/mp4"
    )

    assert transcript == "학생회 로컬 전사 결과"


@pytest.mark.asyncio
async def test_whisper_transcription_and_structured_plan_are_chained(monkeypatch, tmp_path):
    audio_path = tmp_path / "meeting.mp3"
    audio_path.write_bytes(b"fake-audio")
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "proposal_transcription_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [
        QueuedResponse({"text": "9월 18일 점심시간에 안전 캠페인을 진행합시다."}),
        QueuedResponse({"output_text": json.dumps(generated_plan_payload(), ensure_ascii=False)}),
    ]

    processed = await process_meeting_audio(
        path=audio_path,
        filename="meeting.mp3",
        mime_type="audio/mpeg",
        title="안전 캠페인",
        brief_plan={"purpose": "안전 수칙 안내"},
    )

    assert processed.transcript.startswith("9월 18일")
    assert processed.meeting_notes["source"] == "whisper_llm"
    assert processed.plan_document["operation_dates"] == ["2026-09-18"]
    assert processed.plan_document["team_requirements"][0]["people_count"] == 2
    assert QueuedClient.requests[0][0].endswith("/audio/transcriptions")
    assert QueuedClient.requests[0][1]["data"]["model"] == "whisper-1"
    assert QueuedClient.requests[1][0].endswith("/responses")
    assert QueuedClient.requests[1][1]["json"]["text"]["format"]["strict"] is True
    assert "configured-for-test" not in str(QueuedClient.requests[1][1]["json"])


@pytest.mark.asyncio
async def test_invalid_llm_json_is_rejected_without_partial_plan(monkeypatch, tmp_path):
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"fake-audio")
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [
        QueuedResponse({"text": "회의 내용"}),
        QueuedResponse({"output_text": "not-json"}),
    ]

    with pytest.raises(ProposalAIError) as error:
        await process_meeting_audio(
            path=audio_path,
            filename="meeting.wav",
            mime_type="audio/wav",
            title="안전 캠페인",
            brief_plan={"purpose": "안전 수칙 안내"},
        )

    assert error.value.code == "proposal_plan_generation_failed"


@pytest.mark.asyncio
async def test_missing_ai_configuration_stops_before_reading_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "proposal_ai_enabled", False)
    monkeypatch.setattr(settings, "proposal_ai_api_key", None)

    with pytest.raises(ProposalAIError) as error:
        await process_meeting_audio(
            path=tmp_path / "missing.mp3",
            filename="missing.mp3",
            mime_type="audio/mpeg",
            title="안전 캠페인",
            brief_plan={},
        )

    assert error.value.code == "proposal_ai_disabled"


@pytest.mark.asyncio
async def test_transcription_credit_error_is_explained(monkeypatch, tmp_path):
    audio_path = tmp_path / "meeting.mp3"
    audio_path.write_bytes(b"fake-audio")
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "proposal_ai_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "proposal_transcription_api_key", None)
    monkeypatch.setattr(settings, "proposal_transcription_base_url", None)
    monkeypatch.setattr(settings, "proposal_transcription_model", "whisper-1")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [RejectedResponse(402, {"error": {"message": "balance required"}})]

    with pytest.raises(ProposalAIError) as error:
        await transcribe_audio(audio_path, filename="meeting.mp3", mime_type="audio/mpeg")

    assert error.value.code == "proposal_transcription_balance_required"
    assert "잔액" in str(error.value)
    assert QueuedClient.requests[0][1]["data"]["model"] == "openai/whisper-1"


@pytest.mark.asyncio
async def test_meeting_record_prompt_sends_transcript_with_strict_existing_form_schema(
    monkeypatch,
):
    monkeypatch.setattr(settings, "proposal_ai_enabled", True)
    monkeypatch.setattr(settings, "proposal_ai_api_key", "configured-for-test")
    monkeypatch.setattr(httpx, "AsyncClient", QueuedClient)
    QueuedClient.requests = []
    QueuedClient.responses = [
        QueuedResponse(
            {
                "output_text": json.dumps(
                    {
                        "title": "9월 안전 캠페인 부장 회의",
                        "held_at": "2026-09-10T16:00:00+09:00",
                        "location": "학생회실",
                        "summary": "안전 캠페인의 일정과 운영 방식을 논의했다.",
                        "decisions": "9월 18일 점심시간에 진행한다.",
                        "next_actions": "안내 문구 초안을 다음 회의 전까지 준비한다.",
                    },
                    ensure_ascii=False,
                )
            }
        )
    ]

    generated = await generate_meeting_record_json(
        proposal_title="안전 캠페인",
        brief_plan={"purpose": "안전 수칙 안내"},
        meeting_schedule={"date": "2026-09-10", "time": "16:00:00"},
        transcript="9월 18일 점심시간에 진행하기로 합의했습니다.",
    )

    request = QueuedClient.requests[0][1]["json"]
    assert generated.location == "학생회실"
    assert generated.held_at.isoformat() == "2026-09-10T16:00:00+09:00"
    assert request["input"][0]["role"] == "developer"
    assert request["input"][1]["role"] == "user"
    assert "9월 18일 점심시간" in request["input"][1]["content"][0]["text"]
    assert request["text"]["format"]["strict"] is True
    assert request["text"]["format"]["name"] == "studentflow_department_meeting_record"
