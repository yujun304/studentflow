import json
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import settings

SUMMARY_KEYS = ("strengths", "concerns", "changes", "newIdeas", "openQuestions")
CATEGORY_TO_KEY = {
    "STRENGTH": "strengths",
    "CONCERN": "concerns",
    "CHANGE": "changes",
    "NEW_IDEA": "newIdeas",
}


@dataclass(frozen=True)
class SummaryResult:
    strengths: list[str]
    concerns: list[str]
    changes: list[str]
    new_ideas: list[str]
    open_questions: list[str]
    provider: str


def fallback_summary(feedback: list[dict[str, str]]) -> SummaryResult:
    grouped: dict[str, list[str]] = {key: [] for key in SUMMARY_KEYS}
    for item in feedback:
        key = CATEGORY_TO_KEY.get(item["category"])
        content = item["content"].strip()
        if key and content and content not in grouped[key]:
            grouped[key].append(content)
    concerns_and_changes = grouped["concerns"] + grouped["changes"]
    open_questions = [
        value for value in concerns_and_changes if "?" in value or "까요" in value or "필요" in value
    ][:5]
    limit = settings.proposal_summary_max_items
    return SummaryResult(
        strengths=grouped["strengths"][:limit],
        concerns=grouped["concerns"][:limit],
        changes=grouped["changes"][:limit],
        new_ideas=grouped["newIdeas"][:limit],
        open_questions=open_questions,
        provider="fallback",
    )


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][
        : settings.proposal_summary_max_items
    ]


def _summary_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            key: {"type": "array", "items": {"type": "string"}} for key in SUMMARY_KEYS
        },
        "required": list(SUMMARY_KEYS),
        "additionalProperties": False,
    }


def _parse_summary_json(raw: str) -> dict[str, object]:
    cleaned = raw.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict) or set(parsed) != set(SUMMARY_KEYS):
        raise ValueError("summary output does not match the required keys")
    if any(not isinstance(parsed[key], list) for key in SUMMARY_KEYS):
        raise ValueError("summary output values must be arrays")
    return parsed


async def summarize_feedback(feedback: list[dict[str, str]]) -> SummaryResult:
    if not settings.proposal_ai_enabled or not settings.proposal_ai_api_key:
        return fallback_summary(feedback)

    safe_feedback = [
        {"category": item["category"], "content": item["content"]} for item in feedback
    ]
    prompt = (
        "학생회 제안에 달린 여러 의견을 정리하세요. 의견 문장을 그대로 나열하지 말고, "
        "의미가 겹치는 의견은 하나의 간결한 핵심 문장으로 합치세요. 서로 다른 관점은 "
        "빠뜨리지 말고 분리해서 유지하며, 원문에 없는 판단이나 결론은 추가하지 마세요. "
        "strengths에는 좋은 점, concerns에는 걱정되는 점, changes에는 바꾸고 싶은 점, "
        "newIdeas에는 새로운 아이디어, openQuestions에는 추가 확인이나 논의가 필요한 쟁점을 "
        "담으세요. 각 항목은 요약된 문장 배열이어야 합니다. 반드시 다섯 키를 모두 포함한 "
        "JSON 객체만 출력하고 마크다운 코드 블록이나 설명을 붙이지 마세요.\n"
        + json.dumps(safe_feedback, ensure_ascii=False)
    )
    try:
        base_url = settings.proposal_ai_base_url.rstrip("/")
        is_openrouter = urlparse(base_url).netloc.endswith("openrouter.ai")
        schema = _summary_schema()
        if is_openrouter:
            response_format: dict[str, object]
            if settings.proposal_ai_model.endswith(":free"):
                response_format = {"type": "json_object"}
            else:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "proposal_feedback_summary",
                        "strict": True,
                        "schema": schema,
                    },
                }
            endpoint = f"{base_url}/chat/completions"
            request_body = {
                "model": settings.proposal_ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": response_format,
            }
        else:
            endpoint = f"{base_url}/responses"
            request_body = {
                "model": settings.proposal_ai_model,
                "input": prompt,
                "store": False,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "proposal_feedback_summary",
                        "strict": True,
                        "schema": schema,
                    }
                },
            }
        async with httpx.AsyncClient(timeout=settings.proposal_ai_timeout_seconds) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {settings.proposal_ai_api_key}"},
                json=request_body,
            )
            response.raise_for_status()
            payload = response.json()
            if is_openrouter:
                raw = payload["choices"][0]["message"]["content"]
            else:
                raw = next(
                    content["text"]
                    for output in payload["output"]
                    for content in output.get("content", [])
                    if content.get("type") == "output_text"
                )
            parsed = _parse_summary_json(raw)
        return SummaryResult(
            strengths=_clean_list(parsed.get("strengths")),
            concerns=_clean_list(parsed.get("concerns")),
            changes=_clean_list(parsed.get("changes")),
            new_ideas=_clean_list(parsed.get("newIdeas")),
            open_questions=_clean_list(parsed.get("openQuestions")),
            provider="ai",
        )
    except (httpx.HTTPError, KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError):
        return fallback_summary(feedback)
