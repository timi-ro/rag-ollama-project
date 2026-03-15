import os
import time
from typing import Optional

CACHE_TTL_SECONDS = int(os.getenv("CHAT_CACHE_TTL", "300"))   # 5 min default
MAX_CACHE_ENTRIES = int(os.getenv("CHAT_CACHE_MAX", "500"))

# key: (site_id, question_text) → {answer, sources, ts}
_cache: dict = {}


def _evict():
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["ts"] > CACHE_TTL_SECONDS]
    for k in expired:
        del _cache[k]
    # Drop oldest entries if still over limit
    if len(_cache) > MAX_CACHE_ENTRIES:
        oldest = sorted(_cache, key=lambda k: _cache[k]["ts"])[: len(_cache) - MAX_CACHE_ENTRIES]
        for k in oldest:
            del _cache[k]


def get_cached(site_id: int, question: str) -> Optional[dict]:
    key = (site_id, question)
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return {"answer": entry["answer"], "sources": entry["sources"]}


def set_cached(site_id: int, question: str, answer: str, sources: list):
    _evict()
    _cache[(site_id, question)] = {"answer": answer, "sources": sources, "ts": time.time()}