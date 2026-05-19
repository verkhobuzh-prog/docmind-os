"""Generate human-friendly invite codes."""

from __future__ import annotations

import secrets
import string

_ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code(length: int = 10) -> str:
    """e.g. DM-A3K9X2M7P1 — avoids ambiguous 0/O."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"DM-{body}"
