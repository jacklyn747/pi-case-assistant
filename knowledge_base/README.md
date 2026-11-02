# Knowledge base

Everything in `firm/` and `matters/` is **fictional**. The firm, people, phone
numbers, identifiers and medical details were invented to demonstrate the
assistant. Identifiers use reserved or impossible values (SSNs starting with
000, 555 phone numbers, example.com email addresses).

- `firm/` holds firm policies and procedures, visible in every matter.
- `matters/<ID>/` holds one client matter, visible only when that matter is selected.
- `statutes/` holds public Texas law. Run `python scripts/fetch_statutes.py` once to
  download the official text from the Texas Legislature. That is the only
  network request the project makes, and it fetches public law only.

To use real firm documents, replace these folders with your own files and
rebuild the index from the sidebar. Nothing is uploaded anywhere.
