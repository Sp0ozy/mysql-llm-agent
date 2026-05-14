# CLAUDE.md — MySQL LLM Agent

## Project Goal

Python tool that connects to a remote MySQL database, introspects its schema, and uses Google Gemini for two workflows:

1. **Q&A mode** (`main.py`) — natural-language question → SQL → execute → describe in plain English. **STATUS: complete.**
2. **Report mode** — schema → LLM-generated visualization plan → SQL per item → matplotlib chart → business insight → output. Two delivery modes:
   - `generate_report.py` — CLI batch mode, produces `output/report.html` (self-contained static file). **STATUS: complete.**
   - `app/` — FastAPI + HTMX interactive dashboard, live polling, in-browser export. **STATUS: complete.**

Built for a Fintech course on LLM tooling.

## Constraints

- Python 3.11+
- SQLAlchemy 2.0 with `pymysql` driver (NOT raw `mysql-connector-python`)
- `google-genai` SDK for Gemini. Model fallback chain (in order): `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.5-flash-lite` → `gemini-2.0-flash-lite` → `gemini-1.5-flash`
- `python-dotenv` for credentials
- Schema introspection reads METADATA ONLY — never queries table data
- Pandas allowed in the visualization pipeline only (`planner.py`, `visualizer.py`, `report.py`, `generate_report.py`, `processing.py`). NOT in `db_introspect.py` or `context_builder.py`.
- Code must be readable and explainable line-by-line before submission

### FastAPI / HTMX constraints

- FastAPI with lifespan context manager; `app/deps.py` holds the single SQLAlchemy engine and schema state
- HTMX 2.0.4 loaded from CDN; no JS framework, no bundler
- All partial HTML responses use Jinja2 templates under `templates/partials/`
- Synchronous SQLAlchemy + LLM calls run via `asyncio.to_thread` so the event loop stays free for polling
- In-memory state only (`app/state.py` — `CURRENT_PLAN`, `RUNS`). Single-user, single-process (v1)
- Auth is a stub (`get_current_user() -> "local"`). Real auth deferred to v2.

### Security / guardrail constraints

- Every SQL string from the LLM must pass `src/sql_guard.validate_and_prepare(sql, schema)` before execution
- All LLM calls go through `src/llm_client._generate()`; never call the Gemini SDK directly from other modules
- Untrusted content (schema context, user questions, SQL, query results) must be wrapped with `_wrap_untrusted(label, text)` before being interpolated into prompts
- `SET SESSION max_execution_time = 30000` is prepended to every query execution (30 s hard cap)

## Project Structure

```
mysql-llm-agent/
├── .env                          # credentials (gitignored)
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md                     # this file
├── PLAN_INTERACTIVE.md           # FastAPI dashboard build plan
├── requirements.txt
├── main.py                       # Q&A CLI (Task A, done)
├── generate_report.py            # CLI report orchestrator (Task B batch mode, done)
├── src/
│   ├── __init__.py
│   ├── db_introspect.py          # schema extraction — get_schema(), list_databases()
│   ├── context_builder.py        # schema dict → markdown string
│   ├── llm_client.py             # Gemini wrappers with safety + injection guardrails
│   ├── pipeline.py               # Q&A orchestrator
│   ├── planner.py                # schema → structured JSON plan (Gemini response_schema)
│   ├── visualizer.py             # DataFrame → matplotlib Figure; make_figure() + save_figure()
│   ├── report.py                 # items + PNGs → self-contained HTML (base64 embedded)
│   ├── processing.py             # shared per-item pipeline (SQL guard → execute → chart → insight)
│   └── sql_guard.py              # read-only SQL validation (sqlparse-based)
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + lifespan, router includes
│   ├── deps.py                   # engine, schema, schema_context singletons + auth stub
│   ├── state.py                  # PlanItem, ItemResult, RunState dataclasses; CURRENT_PLAN, RUNS
│   ├── runner.py                 # async background task: iterates plan items via asyncio.to_thread
│   └── routes/
│       ├── __init__.py
│       ├── pages.py              # GET / — dashboard with schema summary
│       ├── plan.py               # POST /plan, POST /plan/row, PATCH /plan/row/{i}, DELETE /plan/row/{i}
│       ├── run.py                # POST /run, GET /run/{run_id}/status (HTMX polling)
│       ├── charts.py             # GET /charts/{run_id}/{item_id}.png — in-memory PNG serving
│       └── export.py             # POST /export/{run_id} — writes PNGs + returns HTML FileResponse
├── templates/
│   ├── base.html.j2              # HTMX CDN, full CSS, blocks (title, content)
│   ├── dashboard.html.j2         # main page: schema pill, plan form, run area
│   ├── report.html.j2            # static export template (base64 charts)
│   └── partials/
│       ├── _plan_table.html.j2   # editable plan table + Add row / Run report buttons
│       ├── _plan_row.html.j2     # single editable row (hx-patch on blur/change)
│       ├── _run_status.html.j2   # polling div: progress, result items, export button
│       └── _result_item.html.j2  # chart img + insight + SQL details
└── output/                       # gitignored — generated PNGs + report.html
```

## Environment Variables (`.env`)

```
DB_HOST=87.110.123.151
DB_PORT=3306
DB_USER=fita
DB_PASSWORD=2026-04-28
DB_NAME=direct_payments
GEMINI_API_KEY=
```

## requirements.txt

```
sqlalchemy>=2.0.0
pymysql>=1.1.0
google-genai>=1.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
matplotlib>=3.8.0
jinja2>=3.1.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9
sqlparse>=0.5.0
```

## Running the app

```bash
# Interactive dashboard
uvicorn app.main:app --reload

# CLI batch report
python generate_report.py

# Q&A CLI
python main.py
```

## Module Conventions

### Core (do not modify structure)

- **`src/db_introspect.py`** — `get_schema(engine) -> dict`, `list_databases(engine) -> list[str]`. Uses SQLAlchemy Inspector. `schema["tables"]` is a **list** of dicts `[{name, columns, foreign_keys}]`, not a keyed dict.
- **`src/context_builder.py`** — `build_context(schema: dict) -> str`. Compact markdown. Token-efficient.
- **`src/llm_client.py`** — `_generate(api_key, prompt, *, response_mime_type=None, response_schema=None)` with model fallback on 503/429. Wraps every call with `system_instruction` + `_SAFETY_SETTINGS`. Exported: `generate_sql`, `describe_results`, `generate_insight`.
- **`src/sql_guard.py`** — `validate_and_prepare(sql, schema) -> str`. Strips comments, rejects multi-statement, enforces SELECT/WITH start, rejects DML/DDL keywords, validates FROM/JOIN table names against schema + CTE aliases. Raises `SQLGuardError` on violation.
- **`src/processing.py`** — `process_plan_item(engine, item, index, schema, schema_context, api_key) -> dict`. Returns `{title, sql, rows, fig, insight}` on success or `{title, sql, error}` on failure. Called by both `generate_report.py` and `app/runner.py`.
- **`src/pipeline.py`** — `answer_question(engine, schema_context, question, api_key, schema=None) -> dict`. Passes schema to sql_guard when provided.

### FastAPI app

- **`app/deps.py`** — `init()`, `shutdown()`, `get_engine()`, `get_schema_context()`, `get_api_key()`, `get_current_user()`.
- **`app/state.py`** — `CURRENT_PLAN: list[PlanItem]`, `RUNS: dict[str, RunState]`. Both are module-level globals (single-process v1).
- **`app/runner.py`** — `run_plan(run_id, engine, schema, schema_context, api_key)` async coroutine; run via `BackgroundTasks`.
- Routes follow the pattern: partial HTML in, partial HTML out; use `TemplateResponse(request, "name.j2", context)` (new Starlette positional API — `request` is first arg, not in context dict).

## What NOT to do

- Don't use `mysql-connector-python` directly — SQLAlchemy + pymysql only.
- Don't use raw `information_schema` queries when Inspector methods exist.
- Don't query actual table data during introspection.
- Don't commit `.env` or `output/`.
- Don't break the existing Q&A CLI (`main.py`) or batch report (`generate_report.py`).
- Don't merge planner + visualizer + report + processing into one file.
- Don't add CSS frameworks. Plain inline CSS only.
- Don't trust LLM output without validation — parse → validate → retry once → fail loudly.
- Don't call the Gemini SDK from outside `src/llm_client.py`.
- Don't interpolate untrusted strings into prompts without `_wrap_untrusted()`.
- Don't execute SQL without first calling `sql_guard.validate_and_prepare()`.
- Don't add unnecessary abstractions (no Strategy pattern for viz types — a dispatch dict is enough).
- Don't add persistent storage (Redis, SQLite) until v2.
- Don't implement real auth until v2.
