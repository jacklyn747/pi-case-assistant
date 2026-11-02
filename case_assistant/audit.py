"""Append-only audit log kept on local disk.

Each question records who asked, which matter, which sources were used and
which model answered. Questions are redacted before they are written.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .redact import redact


def log_question(
    path: Path,
    *,
    user: str,
    matter_id: str | None,
    question: str,
    source_ids: list[str],
    model: str,
) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_question, _ = redact(question)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": user,
        "matter_id": matter_id or "firm-only",
        "question": clean_question,
        "sources": source_ids,
        "model": model,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def read_log(path: Path, limit: int = 200) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(line) for line in reversed(lines) if line.strip()]
