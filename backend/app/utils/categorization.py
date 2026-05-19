"""Rule-based document categorization (subject + type) for pilot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentCategory:
    subject: str
    document_type: str
    confidence: float
    method: str = "rules"


# Ukrainian school subjects — keyword → subject label
SUBJECT_KEYWORDS: list[tuple[str, str]] = [
    (r"алгебр|algebra", "Алгебра"),
    (r"геометр|geometry", "Геометрія"),
    (r"фізик|physics", "Фізика"),
    (r"хімі|chemistry", "Хімія"),
    (r"біолог|biology", "Біологія"),
    (r"істор|history", "Історія України"),
    (r"українськ|мова|літератур", "Українська мова"),
    (r"інформат|program|python|код", "Інформатика"),
    (r"англій|english", "Англійська мова"),
    (r"математ|math", "Математика"),
]

TYPE_KEYWORDS: list[tuple[str, str]] = [
    (r"дз|домашн|homework|завдан", "homework"),
    (r"контроль|тест|quiz|exam|іспит|залік", "exam"),
    (r"лекц|lecture|конспект|notes", "lecture_notes"),
    (r"підруч|textbook|посібник", "reference"),
    (r"лаб|laborator|лаборатор", "lab"),
    (r"реферат|essay|курсова|диплом", "assignment"),
]


def is_rag_ingestible(mime_type: str) -> bool:
    """Text documents go through parse/chunk/embed; media are catalog-only."""
    mime = (mime_type or "").lower()
    if mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/"):
        return False
    return True


def categorize_document(
    *,
    filename: str,
    mime_type: str,
    title: Optional[str] = None,
) -> DocumentCategory:
    text = f"{filename} {title or ''}".lower()
    mime = (mime_type or "").lower()

    if mime.startswith("image/"):
        return DocumentCategory("Медіа", "photo", 0.9, "mime")
    if mime.startswith("video/"):
        return DocumentCategory("Медіа", "video", 0.9, "mime")
    if mime.startswith("audio/"):
        return DocumentCategory("Медіа", "audio", 0.85, "mime")

    subject = "Інше"
    for pattern, label in SUBJECT_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            subject = label
            break

    doc_type = "other"
    for pattern, label in TYPE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            doc_type = label
            break

    if doc_type == "other" and mime == "application/pdf":
        doc_type = "document"

    confidence = 0.7 if subject != "Інше" or doc_type != "other" else 0.4
    return DocumentCategory(subject, doc_type, confidence, "rules")
