from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

PLAN_TEXT_FIELDS = (
    "purpose",
    "target_participants",
    "schedule_plan",
    "location_plan",
    "program_plan",
    "role_plan",
    "budget_plan",
    "safety_plan",
)


def brief_plan_fallback(
    *, title: str, description: str, summary: dict[str, list[str]]
) -> dict[str, Any]:
    """Create an editable meeting brief using only supplied source material."""
    return {
        "title": title,
        "background": description,
        "purpose": "",
        "main_suggestions": summary.get("strengths", []) + summary.get("new_ideas", []),
        "opinion_summary": {
            "supporting_points": summary.get("strengths", []),
            "concerns": summary.get("concerns", []),
            "changes": summary.get("changes", []),
        },
        "expected_date": "",
        "expected_location": "",
        "expected_participants": "",
        "expected_operation": "",
        "alternatives": summary.get("new_ideas", []),
        "decision_items": summary.get("open_questions", []),
    }


def meeting_notes_fallback(transcript: str, manual_notes: str | None = None) -> dict[str, Any]:
    source = (manual_notes or transcript).strip()
    lines = [line.strip(" -\t") for line in source.splitlines() if line.strip()]
    logistics = extract_meeting_logistics("\n".join(value for value in [transcript, manual_notes] if value))
    return {
        "summary": "\n".join(lines[:8]),
        "decisions": [],
        "unresolved": lines[:8] if lines else ["회의 녹취 또는 회의 정리를 입력한 뒤 확인이 필요합니다."],
        "source": "manual_notes" if manual_notes else "transcript",
        **logistics,
    }


def final_plan_fallback(
    *, title: str, brief: dict[str, Any], meeting_notes: dict[str, Any]
) -> dict[str, Any]:
    """Merge known values without inventing dates, staffing, budget, or decisions."""
    return {
        "title": title,
        "purpose": str(brief.get("purpose") or ""),
        "target_participants": str(brief.get("expected_participants") or ""),
        "schedule_plan": str(brief.get("expected_date") or ""),
        "location_plan": str(brief.get("expected_location") or ""),
        "program_plan": str(brief.get("expected_operation") or ""),
        "role_plan": "",
        "budget_plan": "",
        "safety_plan": "",
        "preparation_plan": "",
        "emergency_plan": "",
        "operation_dates": list(meeting_notes.get("operation_dates") or []),
        "team_requirements": list(meeting_notes.get("team_requirements") or []),
        "decisions": list(meeting_notes.get("decisions") or []),
        "unresolved": list(meeting_notes.get("unresolved") or []),
    }


def plan_fields(document: dict[str, Any]) -> dict[str, Any]:
    return {field: str(document.get(field) or "").strip() or None for field in PLAN_TEXT_FIELDS}


def extract_meeting_logistics(source: str, *, default_year: int | None = None) -> dict[str, Any]:
    """Extract only explicitly stated dates, time ranges, teams, and headcounts."""
    year = default_year or datetime.now(UTC).year
    dates: list[str] = []
    for match in re.finditer(r"(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일", source):
        try:
            parsed = date(int(match.group(1) or year), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        value = parsed.isoformat()
        if value not in dates:
            dates.append(value)

    times = [
        (f"{int(match.group(1)):02d}:{int(match.group(2)):02d}", f"{int(match.group(3)):02d}:{int(match.group(4)):02d}")
        for match in re.finditer(r"(\d{1,2})\s*:\s*(\d{2})\s*(?:~|～|부터|-)\s*(\d{1,2})\s*:\s*(\d{2})", source)
    ]
    teams: list[tuple[str, int]] = []
    team_source = re.sub(
        r"(?:(?:\d{4})\s*년\s*)?\d{1,2}\s*월\s*\d{1,2}\s*일(?:에)?",
        " ",
        source,
    )
    paired = re.search(r"([가-힣A-Za-z0-9 ]{1,20}조)\s*(?:와|과|·|,)\s*([가-힣A-Za-z0-9 ]{1,20}조)(?:가|이)?\s*각각\s*(\d+)\s*명", team_source)
    if paired:
        teams.extend([(paired.group(1).strip(), int(paired.group(3))), (paired.group(2).strip(), int(paired.group(3)))])
    else:
        for match in re.finditer(r"([가-힣A-Za-z0-9 ]{1,20}조)(?:는|은|가|이)?\s*(\d+)\s*명", team_source):
            item = (match.group(1).strip(), int(match.group(2)))
            if item not in teams:
                teams.append(item)

    requirements = []
    for index, (name, people_count) in enumerate(teams):
        start_time, end_time = times[index] if index < len(times) else (None, None)
        requirements.append({
            "name": name,
            "people_count": people_count,
            "role_description": f"{name} 운영",
            "start_time": start_time,
            "end_time": end_time,
        })
    return {"operation_dates": dates, "team_requirements": requirements}
