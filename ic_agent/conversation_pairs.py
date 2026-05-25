"""Deterministic prompt-response lookup for known training conversation pairs."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


_PAIRS_FILE = Path(__file__).resolve().parents[1] / "training_data" / "conversations.jsonl"


def _normalize_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[?!.,;:]+$", "", value)
    return value


@lru_cache(maxsize=1)
def _load_pairs() -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not _PAIRS_FILE.exists():
        return pairs

    for raw_line in _PAIRS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        prompt = _normalize_text(str(row.get("prompt", "") or ""))
        response = str(row.get("response", "") or "").strip()
        if prompt and response:
            pairs[prompt] = response

    return pairs


def get_known_response(user_input: str) -> str | None:
    """Return a deterministic response when prompt exactly matches known pairs."""
    key = _normalize_text(user_input)
    if not key:
        return None
    return _load_pairs().get(key)
