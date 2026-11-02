"""Streamlit interface for the local case assistant.

    streamlit run app.py

Set CA_DEMO=1 to run with built-in stand-in models (no Ollama needed) for a
screen-only walkthrough. Demo answers are canned; retrieval, redaction,
scoping, deadlines and the audit log all run for real.
"""
from __future__ import annotations

import getpass
import os
from datetime import date

import streamlit as st

from case_assistant.audit import log_question, read_log
from case_assistant.config import RemoteEndpointError, enforce_local, load_settings
from case_assistant.deadlines import personal_injury_deadlines
from case_assistant.ingest import build_index, list_matters, open_collection
from case_assistant.models import FakeChat, FakeEmbedder, OllamaChat, OllamaEmbedder
from case_assistant.rag import answer
from case_assistant.redact import redact

st.set_page_config(page_title="Case Assistant", page_icon="⚖️", layout="wide")

settings = load_settings()
DEMO = os.getenv("CA_DEMO") == "1"

try:
    enforce_local(settings)
except RemoteEndpointError as err:
    st.error(str(err))
    st.stop()


@st.cache_resource
def models():
    if DEMO:
        return FakeEmbedder(), FakeChat()
    return (
        OllamaEmbedder(settings.ollama_host, settings.embed_model),
        OllamaChat(settings.ollama_host, settings.chat_model),
    )


embedder, chat = models()
_, collection = open_collection(settings.chroma_dir)
user = os.getenv("CA_USER") or getpass.getuser()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Case Assistant")
    st.caption("Harlow & Reyes Injury Law · fictional demo firm")

    matters = list_matters(settings.knowledge_dir)
    choice = st.selectbox(
        "Matter",
        ["Firm policies only"] + matters,
        help="Questions can only see firm policy, public statutes and the selected matter's files.",
    )
    matter_id = None if choice == "Firm policies only" else choice

    st.markdown("#### Where your data lives")
    st.markdown(
        f"""
- **Model:** `{chat.name}` on `{settings.ollama_host}`
- **Search index:** `{settings.chroma_dir}`
- **Audit log:** `{settings.audit_path}`
- **Usage tracking:** off
- **Outside AI providers:** none
"""
    )
    if DEMO:
        st.warning("Demo mode: stand-in models, canned answers.")

    if st.button("Rebuild index", use_container_width=True):
        with st.spinner("Reading and indexing the knowledge base on this machine..."):
            count = build_index(settings.knowledge_dir, settings.chroma_dir, embedder)
        st.success(f"Indexed {count} passages.")

if collection.count() == 0:
    with st.spinner("First run: building the local index..."):
        build_index(settings.knowledge_dir, settings.chroma_dir, embedder)
    _, collection = open_collection(settings.chroma_dir)

# ---------- Main ----------
st.markdown("## Ask the firm's files")
st.caption("Answers come only from firm documents, cite their sources, and never leave this machine. Not legal advice.")

ask_tab, deadline_tab, audit_tab = st.tabs(["Ask", "Deadlines", "Audit log"])

with ask_tab:
    question = st.chat_input(
        f"Ask about {matter_id}" if matter_id else "Ask about firm procedures or Texas PI rules"
    )
    if question:
        with st.chat_message("user"):
            st.write(redact(question)[0])
        with st.chat_message("assistant"):
            with st.spinner("Searching the firm's files..."):
                result = answer(collection, embedder, chat, question, matter_id, settings.top_k)
            st.write(result.text)
            with st.expander(f"Sources ({len(result.sources)}), identifiers redacted"):
                for src in result.sources:
                    shown, counts = redact(src.text)
                    tag = src.matter_id or src.scope
                    st.markdown(f"**[{src.number}] {src.source}** · {src.section} · `{tag}`")
                    st.text(shown)
                    if counts:
                        st.caption("Redacted: " + ", ".join(f"{k} ×{v}" for k, v in counts.items()))
        log_question(
            settings.audit_path,
            user=user,
            matter_id=matter_id,
            question=question,
            source_ids=[s.id for s in result.sources],
            model=chat.name,
        )

with deadline_tab:
    st.markdown("#### Texas personal injury deadlines")
    st.caption("Plain date math, not AI. Always verify against the statutes and the facts.")
    c1, c2 = st.columns(2)
    incident = c1.date_input("Incident date", value=date.today(), format="MM/DD/YYYY")
    minor = c2.checkbox("Client was under 18 on the incident date")
    birthdate = c2.date_input("Client birthdate", value=date(2010, 1, 1), format="MM/DD/YYYY") if minor else None
    gov = st.checkbox("A city, county or state agency may be responsible")
    for res in personal_injury_deadlines(incident, birthdate, gov):
        days = (res.due - date.today()).days
        st.markdown(f"**{res.label}:** {res.due:%B %d, %Y} ({days} days from today)")
        st.caption(res.basis)
        for note in res.notes:
            st.caption(f"• {note}")

with audit_tab:
    st.markdown("#### Who asked what")
    st.caption("Stored on this machine. Questions are redacted before they're written.")
    entries = read_log(settings.audit_path)
    if entries:
        st.dataframe(entries, use_container_width=True, hide_index=True)
    else:
        st.write("No questions logged yet.")
