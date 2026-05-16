"""Lightweight input guardrails for chat (Phase 1 MVP)."""

from __future__ import annotations

import re

BLOCKED_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(your\s+)?(system|safety)",
    r"jailbreak",
    r"how\s+to\s+(make|build)\s+(a\s+)?bomb",
    r"how\s+to\s+hack",
    r"generate\s+malware",
    r"steal\s+(passwords|credentials)",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def is_query_allowed(query: str) -> tuple[bool, str | None]:
    text = query.strip()
    if not text:
        return False, "Query cannot be empty"
    if len(text) > 4000:
        return False, "Query is too long"
    for pattern in COMPILED:
        if pattern.search(text):
            return False, "Query violates content safety policy"
    return True, None
