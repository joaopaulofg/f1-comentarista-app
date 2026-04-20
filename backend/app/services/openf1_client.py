import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx

OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
OPENF1_TIMEOUT_SECONDS = 20.0
OPENF1_RETRY_DELAYS_SECONDS = (0.5, 1.0)


class OpenF1ClientError(RuntimeError):
    pass


def _parse_openf1_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def _get_collection(
    endpoint: str, params: dict[str, Any] | list[tuple[str, Any]]
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=OPENF1_TIMEOUT_SECONDS) as client:
        response: httpx.Response | None = None

        for attempt, retry_delay in enumerate((0.0, *OPENF1_RETRY_DELAYS_SECONDS), start=1):
            if retry_delay:
                await asyncio.sleep(retry_delay)

            try:
                response = await client.get(f"{OPENF1_BASE_URL}/{endpoint}", params=params)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt <= len(OPENF1_RETRY_DELAYS_SECONDS):
                    continue
                raise OpenF1ClientError(f"Falha ao consultar OpenF1 em {endpoint}") from exc
            except httpx.HTTPError as exc:
                raise OpenF1ClientError(f"Falha ao consultar OpenF1 em {endpoint}") from exc

        if response is None:
            raise OpenF1ClientError(f"Falha ao consultar OpenF1 em {endpoint}")

    data = response.json()
    if isinstance(data, dict) and data.get("detail") == "No results found.":
        return []

    if not isinstance(data, list):
        raise OpenF1ClientError(f"Resposta inesperada da OpenF1 em {endpoint}")

    return data


def _build_race_display_name(
    session: dict[str, Any], meeting: dict[str, Any] | None = None
) -> str:
    if meeting and meeting.get("meeting_name"):
        return str(meeting["meeting_name"])

    country_name = session.get("country_name")
    if country_name:
        return f"Grande Prêmio de {country_name}"

    circuit_short_name = session.get("circuit_short_name")
    if circuit_short_name:
        return f"Grande Prêmio em {circuit_short_name}"

    return "Grande Prêmio"


async def fetch_meetings(meeting_keys: list[int]) -> list[dict[str, Any]]:
    if not meeting_keys:
        return []

    params = [("meeting_key", meeting_key) for meeting_key in meeting_keys]
    return await _get_collection("meetings", params)


async def fetch_session(session_key: int) -> dict[str, Any] | None:
    sessions = await _get_collection("sessions", {"session_key": session_key})
    if not sessions:
        return None
    return sessions[0]


async def fetch_meeting(meeting_key: int) -> dict[str, Any] | None:
    meetings = await _get_collection("meetings", {"meeting_key": meeting_key})
    if not meetings:
        return None
    return meetings[0]


async def fetch_recent_races(limit: int = 10) -> list[dict[str, Any]]:
    """Busca corridas concluídas, excluindo sprints e sessões canceladas."""
    sessions = await _get_collection(
        "sessions",
        {
            "session_type": "Race",
            "session_name": "Race",
            "is_cancelled": "false",
        },
    )

    now = datetime.now(timezone.utc)
    completed_sessions = [
        session
        for session in sessions
        if (session_end := _parse_openf1_datetime(session.get("date_end"))) is not None
        and session_end <= now
    ]

    sessions_sorted = sorted(
        completed_sessions,
        key=lambda s: s.get("date_start", ""),
        reverse=True,
    )
    recent_sessions = sessions_sorted[:limit]

    meeting_keys = sorted({
        int(session["meeting_key"])
        for session in recent_sessions
        if session.get("meeting_key") is not None
    })
    meetings = await fetch_meetings(meeting_keys)
    meetings_by_key = {meeting.get("meeting_key"): meeting for meeting in meetings}

    enriched_sessions: list[dict[str, Any]] = []
    for session in recent_sessions:
        meeting = meetings_by_key.get(session.get("meeting_key"))
        enriched_sessions.append(
            {
                **session,
                "meeting_name": _build_race_display_name(session, meeting),
                "meeting_official_name": meeting.get("meeting_official_name") if meeting else None,
            }
        )

    return enriched_sessions


async def fetch_session_results(session_key: int) -> list[dict[str, Any]]:
    return await _get_collection("session_result", {"session_key": session_key})


async def fetch_drivers(session_key: int) -> list[dict[str, Any]]:
    return await _get_collection("drivers", {"session_key": session_key})
