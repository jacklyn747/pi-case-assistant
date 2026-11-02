"""Mask personal and health identifiers before text is shown or logged.

Redaction is applied to source excerpts on screen and to everything written to
the audit log. The model itself still reads the full text locally, because it
never leaves the machine.
"""
from __future__ import annotations

import re
from collections import Counter

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("DOB", re.compile(r"(?i)\b(DOB|date of birth)\s*[:\-]?\s*\d{1,2}/\d{1,2}/\d{2,4}")),
    ("PHONE", re.compile(r"(?<!\d)(\(\d{3}\)\s?|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("MRN", re.compile(r"(?i)\b(MRN|medical record (no\.?|number))\s*[:#]?\s*[A-Z0-9-]{4,}")),
    ("CLAIM", re.compile(r"(?i)\b(claim|policy)\s*(no\.?|number|#)\s*[:#]?\s*[A-Z0-9-]{5,}")),
]


def redact(text: str) -> tuple[str, Counter]:
    counts: Counter = Counter()
    for label, pattern in PATTERNS:
        def _sub(match: re.Match[str], label: str = label) -> str:
            counts[label] += 1
            return f"[{label} REDACTED]"
        text = pattern.sub(_sub, text)
    return text, counts
