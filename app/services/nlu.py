import re
from typing import Dict, Optional, Tuple

from . import water_data_service as wds

_INTENT_KEYWORDS = {
    "forecast": ["forecast", "predict", "prediction", "next year", "future", "projection", "trend"],
    "advisory": ["crop", "advisory", "farming", "which crop", "irrigation", "sow", "cultivat", "grow"],
    "list_critical": ["list", "which district", "over-exploited district", "critical zone", "worst", "rank"],
    "compare": [" vs ", " versus ", "compare", "difference between"],
    "greeting": ["hello", "hi ", "hey", "namaste", "good morning", "good afternoon"],
    "help": ["what can you do", "help me", "capabilities", "how do i use"],
    "status": ["status", "condition", "how is", "level", "situation", "category", "safe", "critical",
               "over-exploited", "over exploited", "semi-critical", "water table", "groundwater"],
}


def _detect_intent(message: str) -> str:
    msg = f" {message.lower()} "
    for intent in ["forecast", "advisory", "list_critical", "compare", "greeting", "help", "status"]:
        for kw in _INTENT_KEYWORDS[intent]:
            if kw in msg:
                return intent
    return "general"


def _extract_location(message: str) -> Dict[str, Optional[str]]:
    msg_lower = message.lower()
    found_state = None
    found_district = None

    # Longest names first so "Bengaluru Rural" wins over a looser partial match
    states = sorted(wds.list_states(), key=len, reverse=True)
    for s in states:
        if s.lower() in msg_lower:
            found_state = s
            break

    districts = sorted(wds.list_districts(), key=len, reverse=True)
    for d in districts:
        if re.search(rf"\b{re.escape(d.lower())}\b", msg_lower):
            found_district = d
            break

    return {"state": found_state, "district": found_district}


def parse(message: str) -> Tuple[str, Dict[str, Optional[str]]]:
    """Returns (intent, entities) for a raw user message."""
    intent = _detect_intent(message)
    entities = _extract_location(message)
    return intent, entities
