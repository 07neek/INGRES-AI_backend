"""
memory.py
"""

import time
import uuid
from threading import Lock
from typing import Dict, List

from ..config import settings


class SessionMemory:
    def __init__(self, max_turns: int, ttl_minutes: int):
        self._store: Dict[str, dict] = {}
        self._lock = Lock()
        self.max_turns = max_turns
        self.ttl_seconds = ttl_minutes * 60

    def new_session(self) -> str:
        return str(uuid.uuid4())

    def get_history(self, session_id: str) -> List[dict]:
        with self._lock:
            self._evict_expired()
            session = self._store.get(session_id)
            return list(session["turns"]) if session else []

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        with self._lock:
            session = self._store.setdefault(session_id, {"turns": [], "last_seen": time.time()})
            session["turns"].append({"role": "user", "content": user_msg})
            session["turns"].append({"role": "assistant", "content": assistant_msg})
            # Keep only the last N turns (N user+assistant pairs)
            session["turns"] = session["turns"][-(self.max_turns * 2):]
            session["last_seen"] = time.time()

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._store.items() if now - s["last_seen"] > self.ttl_seconds]
        for sid in expired:
            del self._store[sid]

    def clear_session(self, session_id: str) -> bool:
        """Drops a session's history. Returns True if a session existed."""
        with self._lock:
            return self._store.pop(session_id, None) is not None

    def active_session_count(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._store)


memory = SessionMemory(max_turns=settings.MAX_HISTORY_TURNS, ttl_minutes=settings.SESSION_TTL_MINUTES)
