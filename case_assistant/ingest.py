"""Load the knowledge base, split it into chunks and index it on local disk.

Folder layout decides who can see what:
  knowledge_base/firm/            firm policies, visible in every matter
  knowledge_base/statutes/        public law, visible in every matter
  knowledge_base/matters/<ID>/    one client matter, visible only inside that matter
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from .models import Embedder

COLLECTION = "case_files"


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    section: str
    scope: str
    matter_id: str


def open_collection(chroma_dir: Path):
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False),  # no usage data leaves the machine
    )
    return client, client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def _scope_for(path: Path, root: Path) -> tuple[str, str]:
    parts = path.relative_to(root).parts
    if parts[0] == "matters" and len(parts) > 2:
        return "matter", parts[1]
    if parts[0] == "statutes":
        return "statute", ""
    return "firm", ""


def split_document(text: str, max_chars: int = 900, overlap: int = 150) -> list[tuple[str, str]]:
    """Split on markdown headings, then pack paragraphs into chunks of max_chars."""
    sections: list[tuple[str, str]] = []
    heading, buf = "Overview", []
    for line in text.splitlines():
        match = re.match(r"^#{1,4}\s+(.*)", line)
        if match:
            if "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = match.group(1).strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))

    chunks: list[tuple[str, str]] = []
    for heading, body in sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        current = ""
        for para in paragraphs:
            if current and len(current) + len(para) + 2 > max_chars:
                chunks.append((heading, current))
                current = current[-overlap:] + "\n\n" + para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current:
            chunks.append((heading, current))
    return chunks


def load_chunks(knowledge_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(knowledge_dir.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"} or path.name.lower() == "readme.md":
            continue
        scope, matter_id = _scope_for(path, knowledge_dir)
        rel = path.relative_to(knowledge_dir).as_posix()
        for i, (section, text) in enumerate(split_document(path.read_text(encoding="utf-8"))):
            chunks.append(Chunk(f"{rel}#{i}", text, rel, section, scope, matter_id))
    return chunks


def build_index(knowledge_dir: Path, chroma_dir: Path, embedder: Embedder, batch: int = 32) -> int:
    client, collection = open_collection(chroma_dir)
    client.delete_collection(COLLECTION)
    _, collection = open_collection(chroma_dir)
    chunks = load_chunks(knowledge_dir)
    for start in range(0, len(chunks), batch):
        part = chunks[start : start + batch]
        collection.add(
            ids=[c.id for c in part],
            documents=[c.text for c in part],
            embeddings=embedder.embed([c.text for c in part]),
            metadatas=[
                {"source": c.source, "section": c.section, "scope": c.scope, "matter_id": c.matter_id}
                for c in part
            ],
        )
    return len(chunks)


def list_matters(knowledge_dir: Path) -> list[str]:
    matters = knowledge_dir / "matters"
    return sorted(p.name for p in matters.iterdir() if p.is_dir()) if matters.exists() else []
