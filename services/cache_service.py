"""Reusable in-memory cache utilities for quiz and chat result caching."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

QUIZ_CACHE_TTL_HOURS = 24
DIAGRAM_CACHE_TTL_DAYS = 30
DEFAULT_CACHE_TTL_HOURS = 24

_CACHE_STORAGE: dict[str, dict[str, Any]] = {}
_SESSION_MEMORY_CACHE: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _normalize_cache_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def make_quiz_cache_key(document_text: str, question_type: str, num_questions: int) -> str:
    normalized_document = _normalize_cache_text(document_text)
    return _hash_key(f"quiz:{question_type}:{num_questions}:{normalized_document}")


def make_chat_cache_key(question: str, document_context: str) -> str:
    normalized_question = _normalize_cache_text(question)
    normalized_context = _normalize_cache_text(document_context)
    return _hash_key(f"chat:{normalized_question}:{normalized_context}")


def make_diagram_cache_key(image_bytes: bytes) -> str:
    image_digest = hashlib.sha256(image_bytes).hexdigest()
    return _hash_key(f"diagram:{image_digest}")


def _is_expired(entry: dict[str, Any]) -> bool:
    expires_at = entry.get("expires_at")
    return expires_at is not None and _now() >= expires_at


def _cleanup_cache(cache: dict[str, dict[str, Any]], key: str) -> None:
    entry = cache.get(key)
    if entry is None:
        return
    if _is_expired(entry):
        cache.pop(key, None)


def get_cache_value(key: str) -> Any | None:
    _cleanup_cache(_SESSION_MEMORY_CACHE, key)
    if key in _SESSION_MEMORY_CACHE:
        logger.info("[CACHE HIT] Session")
        return _SESSION_MEMORY_CACHE[key]["value"]

    _cleanup_cache(_CACHE_STORAGE, key)
    entry = _CACHE_STORAGE.get(key)
    if entry is not None:
        logger.info("[CACHE HIT] Persistent")
        return entry["value"]

    return None


def set_cache_value(key: str, value: Any, ttl_hours: int = DEFAULT_CACHE_TTL_HOURS) -> None:
    expires_at = _now() + ttl_hours * 3600 if ttl_hours is not None else None
    entry = {
        "value": value,
        "created_at": _now(),
        "expires_at": expires_at,
    }
    _CACHE_STORAGE[key] = entry
    _SESSION_MEMORY_CACHE[key] = entry.copy()


def delete_expired_cache_entry(key: str) -> None:
    _cleanup_cache(_SESSION_MEMORY_CACHE, key)
    _cleanup_cache(_CACHE_STORAGE, key)


def clear_cache() -> None:
    _CACHE_STORAGE.clear()
    _SESSION_MEMORY_CACHE.clear()
