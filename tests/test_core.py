from datetime import date
from pathlib import Path

import pytest

from case_assistant.audit import log_question, read_log
from case_assistant.config import RemoteEndpointError, Settings, enforce_local, is_local_host
from case_assistant.deadlines import personal_injury_deadlines
from case_assistant.ingest import build_index, list_matters, load_chunks, open_collection
from case_assistant.models import FakeChat, FakeEmbedder
from case_assistant.rag import answer, retrieve
from case_assistant.redact import redact

KB = Path(__file__).resolve().parent.parent / "knowledge_base"


# ---------- redaction ----------
def test_redacts_identifiers():
    text = "DOB: 04/12/1987. SSN 000-12-3456. Phone (713) 555-0142. dana@example.com. MRN BUC-55021. claim number LSM-2026-448812"
    out, counts = redact(text)
    for secret in ["000-12-3456", "04/12/1987", "555-0142", "dana@example.com", "BUC-55021", "LSM-2026-448812"]:
        assert secret not in out
    assert set(counts) == {"SSN", "DOB", "PHONE", "EMAIL", "MRN", "CLAIM"}


def test_leaves_ordinary_dates_alone():
    out, counts = redact("Incident on 03/18/2026 at 5:40 p.m.")
    assert "03/18/2026" in out and not counts


# ---------- deadlines ----------
def test_two_year_deadline():
    res = personal_injury_deadlines(date(2026, 3, 18))[0]
    assert res.due == date(2028, 3, 20)  # 03/18/2028 is a Saturday, rolls to Monday
    assert "16.003" in res.basis


def test_minor_tolling():
    res = personal_injury_deadlines(date(2026, 1, 9), client_birthdate=date(2010, 6, 1))[0]
    assert res.due == date(2030, 6, 3)  # 18th birthday 06/01/2028 + 2 years = Saturday, rolls to Monday
    assert any("16.001" in n for n in res.notes)


def test_government_notice():
    results = personal_injury_deadlines(date(2026, 1, 9), government_defendant=True)
    notice = [r for r in results if "governmental" in r.label][0]
    assert notice.due == date(2026, 7, 9)


def test_leap_day():
    assert personal_injury_deadlines(date(2028, 2, 29))[0].due == date(2030, 2, 28)


# ---------- local-only guard ----------
def _settings(host, allow=False):
    return Settings(host, "m", "e", KB, Path("/tmp/x"), allow, 4)


def test_local_hosts_allowed():
    assert is_local_host("http://127.0.0.1:11434")
    assert is_local_host("http://localhost:11434")
    assert is_local_host("http://192.168.1.20:11434")
    enforce_local(_settings("http://127.0.0.1:11434"))


def test_public_host_refused():
    with pytest.raises(RemoteEndpointError):
        enforce_local(_settings("http://8.8.8.8:11434"))


def test_remote_override():
    enforce_local(_settings("http://8.8.8.8:11434", allow=True))


# ---------- ingestion and scoping ----------
@pytest.fixture(scope="module")
def index(tmp_path_factory):
    path = tmp_path_factory.mktemp("index")
    embedder = FakeEmbedder()
    build_index(KB, path, embedder)
    _, collection = open_collection(path)
    return collection, embedder


def test_chunks_are_scoped():
    chunks = load_chunks(KB)
    assert {c.scope for c in chunks} == {"firm", "matter", "statute"}
    assert {c.matter_id for c in chunks if c.scope == "matter"} == {"M-1001", "M-1002"}
    assert not any(c.source.endswith("README.md") for c in chunks)


def test_lists_matters():
    assert list_matters(KB) == ["M-1001", "M-1002"]


def test_matter_isolation(index):
    collection, embedder = index
    sources = retrieve(collection, embedder, "slip and fall grocery cooler video", "M-1001", k=8)
    assert sources
    assert all(s.matter_id in ("", "M-1001") for s in sources), "M-1002 leaked into M-1001"


def test_firm_only_sees_no_client_files(index):
    collection, embedder = index
    sources = retrieve(collection, embedder, "Dana Whitfield rear-end collision", None, k=8)
    assert all(s.scope in ("firm", "statute") for s in sources)


def test_relevant_matter_file_found(index):
    collection, embedder = index
    sources = retrieve(collection, embedder, "surveillance video maintenance records preservation", "M-1002", k=4)
    assert any(s.matter_id == "M-1002" for s in sources)


def test_answer_returns_cited_sources(index):
    collection, embedder = index
    result = answer(collection, embedder, FakeChat(), "When do we request medical records?", None, k=3)
    assert result.sources and "[1]" in result.text


# ---------- audit ----------
def test_audit_log_redacts(tmp_path):
    path = tmp_path / "audit.jsonl"
    log_question(path, user="paralegal1", matter_id="M-1001", question="What's the status for SSN 000-12-3456?", source_ids=["a#0"], model="m")
    entry = read_log(path)[0]
    assert "000-12-3456" not in entry["question"]
    assert entry["matter_id"] == "M-1001" and entry["user"] == "paralegal1"
