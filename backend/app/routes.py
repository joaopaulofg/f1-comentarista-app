import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import CommentaryResponse, DriverResult, Race
from app.services.ollama_client import (
    OllamaClientError,
    generate_commentary,
    stream_commentary,
)
from app.services.openf1_client import (
    OpenF1ClientError,
    fetch_drivers,
    fetch_recent_races,
    fetch_session,
    fetch_session_results,
)

router = APIRouter(prefix="/races", tags=["races"])


def _result_position(row: dict) -> int:
    position = row.get("position")
    return position if isinstance(position, int) else 999


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _build_commentary_context(
    session_key: int,
) -> tuple[CommentaryResponse, str, str]:
    try:
        session, results = await asyncio.gather(
            fetch_session(session_key),
            fetch_session_results(session_key),
        )
    except OpenF1ClientError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar dados da OpenF1",
        ) from exc

    if not session:
        raise HTTPException(status_code=404, detail="Corrida não encontrada")

    if not results:
        raise HTTPException(status_code=404, detail="Resultado da corrida não encontrado")

    try:
        drivers = await fetch_drivers(session_key)
    except OpenF1ClientError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar dados complementares da OpenF1",
        ) from exc

    driver_map = {d.get("driver_number"): d for d in drivers}

    ordered = sorted(results, key=_result_position)

    full_results: list[DriverResult] = []
    for row in ordered:
        number = row.get("driver_number")
        drv = driver_map.get(number, {})
        full_results.append(
            DriverResult(
                position=_result_position(row),
                driver_number=number,
                full_name=drv.get("full_name", f"Driver {number}"),
                team_name=drv.get("team_name"),
                points=row.get("points"),
            )
        )

    podium = full_results[:3]
    top10 = full_results[:10]

    podium_text = "\n".join(
        [f"{d.position}º - {d.full_name} ({d.team_name or 'Equipe N/A'})" for d in podium]
    )
    top10_text = "\n".join(
        [f"{d.position}º - {d.full_name} ({d.team_name or 'Equipe N/A'})" for d in top10]
    )

    race_title = (
        session.get("meeting_name")
        or f"Grande Prêmio de {session.get('country_name', 'local indefinido')}"
    )

    response = CommentaryResponse(
        session_key=session_key,
        race_title=race_title,
        podium=podium,
        full_results=top10,
        commentary="",
    )
    return response, podium_text, top10_text


@router.get("/recent", response_model=list[Race])
async def get_recent_races(limit: int = 10):
    try:
        sessions = await fetch_recent_races(limit)
    except OpenF1ClientError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar corridas na OpenF1",
        ) from exc

    races = []
    for s in sessions:
        races.append(
            Race(
                session_key=s["session_key"],
                meeting_name=s.get("meeting_name", "Grande Prêmio"),
                country_name=s.get("country_name", "N/A"),
                circuit_short_name=s.get("circuit_short_name", "N/A"),
                date_start=s.get("date_start", ""),
                year=s.get("year", 0),
            )
        )
    return races


@router.get("/{session_key}/commentary", response_model=CommentaryResponse)
async def get_race_commentary(session_key: int):
    response, podium_text, top10_text = await _build_commentary_context(session_key)

    try:
        commentary = await generate_commentary(response.race_title, podium_text, top10_text)
    except OllamaClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return response.model_copy(update={"commentary": commentary})


@router.get("/{session_key}/commentary/stream")
async def stream_race_commentary(session_key: int):
    response, podium_text, top10_text = await _build_commentary_context(session_key)
    metadata = response.model_copy(update={"commentary": ""})
    race_title = response.race_title

    async def event_stream() -> AsyncIterator[str]:
        yield _format_sse("metadata", metadata.model_dump())

        try:
            async for chunk in stream_commentary(race_title, podium_text, top10_text):
                yield _format_sse("chunk", {"text": chunk})
        except OllamaClientError as exc:
            yield _format_sse("app-error", {"detail": str(exc)})
            return

        yield _format_sse("done", {"ok": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
