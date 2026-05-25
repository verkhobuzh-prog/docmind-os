"""Offline AI quality metrics — no LLM calls."""

from __future__ import annotations

import hashlib
import re

_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+")


def prompt_signature(prompt: str) -> str:
    """Stable short hash for prompt regression tests."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def find_unsupported_numbers(answer: str, context: str) -> list[str]:
    """Return numbers in the answer that do not appear in the context."""
    answer_nums = set(_NUMBER_RE.findall(answer))
    context_nums = set(_NUMBER_RE.findall(context))
    return sorted(answer_nums - context_nums)


def faithfulness_score(answer: str, context_chunks: list[str]) -> float:
    """Heuristic share of substantive answer tokens found in context."""
    if not answer.strip():
        return 0.0

    context = " ".join(context_chunks).lower()
    tokens = [token for token in _TOKEN_RE.findall(answer.lower()) if len(token) > 3]
    if not tokens:
        return 1.0

    supported = sum(1 for token in tokens if token in context)
    return round(supported / len(tokens), 4)


def citation_accuracy(answer: str, filenames: list[str]) -> float:
    """Fraction of bracket citations that reference known source filenames."""
    if not filenames:
        return 0.0

    bracket_cites = re.findall(r"\[([^\]]+)\]", answer)
    if not bracket_cites:
        return 0.0

    valid = sum(1 for cite in bracket_cites if any(name in cite for name in filenames))
    return round(valid / len(bracket_cites), 4)
