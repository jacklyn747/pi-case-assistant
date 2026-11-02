"""Build docs/index.html, the in-browser demo, from knowledge_base/.

The demo embeds the same fictional documents the app indexes, split the same
way, so what visitors search is the real knowledge base.

    python scripts/build_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from case_assistant.ingest import load_chunks  # noqa: E402

TEMPLATE = ROOT / "scripts" / "demo_template.html"
OUT = ROOT / "docs" / "index.html"


def doc_name(source: str) -> str:
    stem = Path(source).stem.replace("_", " ")
    if stem.startswith("texas pi"):
        return "Texas PI quick reference"
    stem = stem.replace(" sop", " SOP")
    return stem[:1].upper() + stem[1:]


def main() -> None:
    chunks = load_chunks(ROOT / "knowledge_base")
    data = [
        {
            "id": c.id,
            "doc": doc_name(c.source),
            "section": c.section,
            "scope": c.scope,
            "matter": c.matter_id,
            "text": c.text,
        }
        for c in chunks
    ]
    html = TEMPLATE.read_text().replace("/*__KB__*/[]", json.dumps(data, ensure_ascii=False))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    (OUT.parent / ".nojekyll").write_text("")
    print(f"Wrote {OUT} with {len(data)} passages")


if __name__ == "__main__":
    main()
