"""
routers/chat.py
================
POST /api/v1/chat — the single endpoint the chat UI needs.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from ..schemas import ChatRequest, ChatResponse
from ..services import crop_advisory, llm_service, nlu, water_data_service
from ..services.memory import memory

logger = logging.getLogger("ingres_ai.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or memory.new_session()

    intent, entities = nlu.parse(payload.message)

    records, source = await water_data_service.get_groundwater_data(
        state=entities.get("state"),
        district=entities.get("district"),
    )

    chart = water_data_service.build_chart(records, intent)
    crop_tips = crop_advisory.get_advisory(records) if intent in ("advisory", "status", "forecast") else None

    history = memory.get_history(session_id)

    llm_status = "ok"
    try:
        reply = await llm_service.generate_reply(payload.message, history, records, crop_tips)
    except llm_service.LLMServiceError as exc:
        logger.info("Falling back to offline reply: %s", exc)
        reply = llm_service.offline_fallback_reply(payload.message, records)
        llm_status = f"offline_fallback ({exc})"

    memory.add_turn(session_id, payload.message, reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        intent=intent,
        entities=entities,
        records=water_data_service.to_year_records(records[:20]),
        chart=water_data_service.to_chart_model(chart),
        crop_advisory=crop_tips,
        data_source=source,
        llm_status=llm_status,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/reset")
def reset_session(session_id: str):
    """Clears a session's conversation history (does not delete anything —
    there's no DB — just drops the in-memory turns)."""
    existed = memory.clear_session(session_id)
    return {"status": "reset", "session_id": session_id, "existed": existed}
