"""Download official Texas statute chapters into knowledge_base/statutes/official/.

This is the only network request in the project, and it fetches public law.
Run it once, then rebuild the index from the app's sidebar.

    python scripts/fetch_statutes.py
"""
from __future__ import annotations

import html
import re
import sys
import urllib.request
from pathlib import Path

CHAPTERS = {
    "CP.16": "Limitations",
    "CP.33": "Proportionate Responsibility",
    "CP.41": "Damages",
    "CP.101": "Tort Claims (governmental units)",
}
BASE = "https://statutes.capitol.texas.gov/docs/cp/htm/{code}.htm"
OUT = Path(__file__).resolve().parent.parent / "knowledge_base" / "statutes" / "official"


def to_text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style).*?</\1>", "", page)
    page = re.sub(r"(?i)<br\s*/?>|</p>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", "", page))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for code, title in CHAPTERS.items():
        url = BASE.format(code=code.lower())
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                page = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            print(f"Could not fetch {url}: {exc}", file=sys.stderr)
            continue
        text = to_text(page)
        if "Sec. " not in text:
            print(
                f"{url} returned no statute text (the site may now load it with JavaScript). "
                "Save the chapter from your browser into knowledge_base/statutes/official/ instead.",
                file=sys.stderr,
            )
            continue
        target = OUT / f"{code.replace('.', '_')}.md"
        target.write_text(f"# Tex. Civ. Prac. & Rem. Code ch. {code.split('.')[1]}: {title}\n\nSource: {url}\n\n{text}\n", encoding="utf-8")
        print(f"Saved {target.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
