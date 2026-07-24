import logging
from typing import List, Optional

import httpx

from ..config import settings

logger = logging.getLogger("ingres_ai.llm")


class LLMServiceError(Exception):
    """Raised when the live LLM call fails; caught in the router to fall
    back to an offline templated reply rather than a 500."""


SYSTEM_PROMPT = """You are INGRES-AI, a virtual assistant for the Central Ground Water Board \
(CGWB), Ministry of Jal Shakti, built on top of the INGRES (India Ground Water Resource \
Estimation System) portal. You help farmers, gram panchayat officials, and field researchers \
understand groundwater data in plain, non-technical language.

Rules you always follow:
- Base your answer ONLY on the DATA CONTEXT given below. If it doesn't cover what's asked, say so \
honestly rather than inventing numbers.
- Explain technical terms simply the first time you use them (e.g. "Over-Exploited" means more \
water is being withdrawn each year than is naturally recharged).
- Keep answers concise and conversational — this is a chat assistant, not a report.
- When CROP ADVISORY CONTEXT is provided, you may weave it in naturally, but always frame it as \
general guidance and suggest confirming specifics with a local agriculture extension officer.
- If asked something unrelated to water, groundwater, or agriculture, politely redirect to what \
you can help with.

DATA CONTEXT (JSON records matched to this query):
{data_context}

CROP ADVISORY CONTEXT (only relevant if the user is asking about farming/crops):
{crop_context}
"""


def _format_records_for_prompt(records: List[dict], max_records: int = 12) -> str:
    if not records:
        return "No matching groundwater records were found for this query."
    trimmed = records[:max_records]
    lines = []
    for r in trimmed:
        lines.append(
            f"- {r.get('block')}, {r.get('district')}, {r.get('state')} | year={r.get('year')} | "
            f"category={r.get('category')} | stage_of_extraction={r.get('stage_of_extraction_percent')}% | "
            f"pre_monsoon_level={r.get('pre_monsoon_level_mbgl')} mbgl | "
            f"post_monsoon_level={r.get('post_monsoon_level_mbgl')} mbgl | rainfall={r.get('rainfall_mm')} mm"
        )
    suffix = "" if len(records) <= max_records else f"\n(+ {len(records) - max_records} more matching rows omitted for brevity)"
    return "\n".join(lines) + suffix


def _build_system_prompt(records: List[dict], crop_tips: Optional[List[str]]) -> str:
    data_context = _format_records_for_prompt(records)
    crop_context = "\n".join(f"- {tip}" for tip in crop_tips) if crop_tips else "Not applicable to this query."
    return SYSTEM_PROMPT.format(data_context=data_context, crop_context=crop_context)


def offline_fallback_reply(user_message: str, records: List[dict]) -> str:
    """A clear, honest, data-grounded reply used when no LLM is configured or
    the live call fails — the endpoint still returns something useful instead
    of an empty/broken chat bubble."""
    if not records:
        return (
            "I couldn't find matching groundwater records for that, and the AI model isn't "
            "reachable right now either. Try naming a specific state or district (e.g. "
            "\"status in Wardha\"), or check back shortly."
        )

    latest_by_block = {}
    for r in records:
        key = r["block"]
        if key not in latest_by_block or r["year"] > latest_by_block[key]["year"]:
            latest_by_block[key] = r

    lines = ["(AI model unavailable right now — here's a direct summary of the matching data:)"]
    for rec in list(latest_by_block.values())[:5]:
        lines.append(
            f"- {rec['block']} ({rec['district']}, {rec['state']}), {rec['year']}: "
            f"{rec['category']} — stage of extraction {rec['stage_of_extraction_percent']}%, "
            f"post-monsoon level {rec['post_monsoon_level_mbgl']} m below ground."
        )
    return "\n".join(lines)


async def generate_reply(
    user_message: str,
    history: List[dict],
    records: List[dict],
    crop_tips: Optional[List[str]] = None,
) -> str:
    """Calls the AI model with the API key configured in settings and returns
    the generated text. Raises LLMServiceError on failure — callers should
    catch this and use `offline_fallback_reply` instead of propagating a 500
    to the frontend."""
    if not settings.GROQ_API_KEY:
        raise LLMServiceError("GROQ_API_KEY is not set")

    messages = [{"role": "system", "content": _build_system_prompt(records, crop_tips)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{settings.GROQ_BASE_URL.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("LLM API returned an error: %s %s", exc.response.status_code, exc.response.text[:300])
        raise LLMServiceError(f"LLM API error {exc.response.status_code}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM API call failed: %s", exc)
        raise LLMServiceError(str(exc)) from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMServiceError(f"Unexpected LLM response shape: {data}") from exc
