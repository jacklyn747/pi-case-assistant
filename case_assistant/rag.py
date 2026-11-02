"""Retrieve, answer with citations, and log.

Retrieval is scoped: a question asked inside matter M-1001 can see firm policy,
public statutes and M-1001's files, and nothing from any other client.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import ChatModel, Embedder

SYSTEM_PROMPT = """You are a case assistant for a personal injury law firm.
Answer only from the numbered sources provided. Cite every claim with its source
number in square brackets, like [2]. If the sources don't answer the question,
say so plainly and suggest what document would. Do not give legal advice to
clients; you support the firm's staff. Keep answers short and practical."""


@dataclass
class Source:
    number: int
    id: str
    source: str
    section: str
    scope: str
    matter_id: str
    text: str


@dataclass
class Answer:
    text: str
    sources: list[Source]


def scope_filter(matter_id: str | None) -> dict:
    shared = [{"scope": "firm"}, {"scope": "statute"}]
    if matter_id:
        return {"$or": shared + [{"matter_id": matter_id}]}
    return {"$or": shared}


def retrieve(collection, embedder: Embedder, question: str, matter_id: str | None, k: int) -> list[Source]:
    result = collection.query(
        query_embeddings=embedder.embed([question]),
        n_results=k,
        where=scope_filter(matter_id),
    )
    sources = []
    for i, (cid, doc, meta) in enumerate(
        zip(result["ids"][0], result["documents"][0], result["metadatas"][0]), start=1
    ):
        sources.append(Source(i, cid, meta["source"], meta["section"], meta["scope"], meta["matter_id"], doc))
    return sources


def build_prompt(question: str, sources: list[Source]) -> str:
    blocks = [f"[{s.number}] ({s.source} / {s.section})\n{s.text}" for s in sources]
    return "Sources:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}"


def answer(collection, embedder: Embedder, chat: ChatModel, question: str, matter_id: str | None, k: int = 4) -> Answer:
    sources = retrieve(collection, embedder, question, matter_id, k)
    if not sources:
        return Answer("I couldn't find anything in the firm's files for that.", [])
    return Answer(chat.complete(SYSTEM_PROMPT, build_prompt(question, sources)), sources)
