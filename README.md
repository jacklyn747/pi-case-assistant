# Case Assistant

A private AI assistant for a personal injury law firm that runs entirely on the firm's own hardware. Staff ask questions in plain English and get answers drawn only from the firm's procedures, public Texas law and the client file they're working on, with every answer citing its sources.

No client data goes to an outside AI company. The model, the search index and the audit log all live on the machine it runs on.

**[Try the live demo →](https://jacklyn747.github.io/pi-case-assistant/)** It runs entirely in your browser.

> Everything in `knowledge_base/` is fictional: the firm, the clients, the identifiers and the medical details. Not legal advice.

## Why it exists

Personal injury firms run on paperwork: intake notes, medical records, billing ledgers, insurer letters, deadlines. Staff lose hours hunting through files and re-asking the same procedural questions. Public AI chat tools would help, but pasting medical records and Social Security numbers into them is a confidentiality risk most firms can't accept.

This project shows the alternative: the convenience of AI, with the data staying where it belongs.

## What it does

| Feature | What it means for the firm |
|---|---|
| **Runs locally** | The language model and embeddings run in [Ollama](https://ollama.com) on firm hardware. The app refuses to start if pointed at a server outside the firm's network. |
| **Answers with citations** | Every answer cites the document and section it came from. If the files don't cover it, it says so. |
| **Matter-level privacy** | A question asked inside one client's matter can see firm policy, public law and that client's files, and nothing from any other client. |
| **Redaction** | Social Security numbers, birthdates, phone numbers, emails, medical record numbers and claim numbers are masked on screen and in the logs. |
| **Audit log** | Every question is logged locally with who asked, which matter and which documents were used. |
| **Deadline calculator** | Texas filing deadlines from plain date math, not AI, including minor tolling, weekend rollover and governmental notice. |
| **No tracking** | Usage reporting in Streamlit and ChromaDB is switched off. |

## Run it

1. Install [Ollama](https://ollama.com) and pull the two models:

   ```bash
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text
   ```

2. Install and start the app:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

   It opens at `http://127.0.0.1:8501` and builds its index on first run.

**Just looking?** `CA_DEMO=1 streamlit run app.py` runs with stand-in models and no Ollama. Search, redaction, matter privacy, deadlines and the audit log are real; the answers are canned.

## Settings

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Model server. Must be local or on a private network. |
| `CA_CHAT_MODEL` | `llama3.1:8b` | Any Ollama chat model. |
| `CA_EMBED_MODEL` | `nomic-embed-text` | Any Ollama embedding model. |
| `CA_DATA_DIR` | `./data` | Where the index and audit log are stored. |
| `CA_USER` | your login name | Name recorded in the audit log. |
| `CA_ALLOW_REMOTE` | `0` | Set to `1` only to approve a model server outside the local network. |

## Using real documents

Replace the folders in `knowledge_base/`:

- `firm/` for policies and procedures, visible in every matter
- `matters/<MATTER-ID>/` for one client's files, visible only in that matter
- `statutes/` for public law. `python scripts/fetch_statutes.py` tries to download official Texas chapters; if the state site blocks it, save them from your browser into `statutes/official/`.

Then click **Rebuild index**.

## Tests

```bash
pytest
```

Covers redaction, deadline math (including leap years and weekend rollover), the local-only guard, matter isolation and audit logging. The tests use stand-in models, so they run anywhere.

## The browser demo

`docs/index.html` is a self-contained version for showing the project to people. It embeds the same knowledge base and runs the same redaction patterns, deadline rules and matter scoping in JavaScript, with keyword search standing in for embeddings. Nothing typed into it leaves the browser. Rebuild it after changing the knowledge base:

```bash
python scripts/build_demo.py
```

## How it's built

Python · Streamlit · ChromaDB · Ollama (Llama 3.1, nomic-embed-text)

```
app.py                   interface
case_assistant/
  config.py              settings and the local-only guard
  ingest.py              chunking, scoping and indexing
  rag.py                 scoped retrieval and cited answers
  redact.py              identifier masking
  deadlines.py           Texas deadline math
  audit.py               local audit log
  models.py              Ollama clients (and test stand-ins)
knowledge_base/          fictional firm, matters and statute summaries
scripts/fetch_statutes.py
tests/
```

Built by Jackie Miller · [jackiemiller.co](https://jackiemiller.co)
