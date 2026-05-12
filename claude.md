# CLAUDE.md — MySQL LLM Agent

## Project Goal

Python tool that connects to a remote MySQL database, introspects its schema, and uses Google Gemini for two workflows:

1. **Q&A mode** (`main.py`) — natural-language question → SQL → execute → describe in plain English. **STATUS: complete, tagged `pre-task2`.**
2. **Report mode** (`generate_report.py`) — schema → LLM-generated visualization plan → SQL per item → matplotlib chart → business insight → self-contained HTML report. **STATUS: to be built (see PLAN.md).**

Built for a Fintech course on LLM tooling. Grading criterion for Task B: the agent must autonomously generate a useful analytical report from schema alone.

## Constraints

- Python 3.11+
- SQLAlchemy 2.0 with `pymysql` driver (NOT raw `mysql-connector-python`)
- `google-genai` SDK for Gemini (model fallback chain: `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-1.5-flash`)
- `python-dotenv` for credentials
- Schema introspection reads METADATA ONLY — never queries table data
- Pandas allowed in the visualization pipeline only (`planner.py`, `visualizer.py`, `report.py`, `generate_report.py`). NOT in `db_introspect.py` or `context_builder.py`.
- Code must be readable and explainable line-by-line before submission

## Project Structure

```
mysql-llm-agent/
├── .env                       # credentials (gitignored)
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md                  # this file — project reference
├── PLAN.md                    # active build plan for Task B
├── requirements.txt
├── main.py                    # Q&A CLI (Task A, done)
├── generate_report.py         # Report orchestrator (Task B, to build)
├── src/
│   ├── __init__.py
│   ├── db_introspect.py       # schema extraction (done)
│   ├── context_builder.py     # schema → markdown (done)
│   ├── llm_client.py          # Gemini wrappers (extend for Task B)
│   ├── pipeline.py            # Q&A orchestrator (done)
│   ├── planner.py             # NEW: schema → JSON plan
│   ├── visualizer.py          # NEW: DataFrame → PNG
│   └── report.py              # NEW: items → HTML
├── templates/
│   └── report.html.j2         # NEW: Jinja2 report template
└── output/                    # NEW: gitignored, generated PNGs + report.html
```

## Environment Variables (`.env`)

```
DB_HOST=87.110.123.151
DB_PORT=3306
DB_USER=fita
DB_PASSWORD=2026-04-28
DB_NAME=                       # leave blank on first run to discover
GEMINI_API_KEY=
```

## requirements.txt

Current (Q&A mode):
```
sqlalchemy>=2.0.0
pymysql>=1.1.0
google-genai>=1.0.0
python-dotenv>=1.0.0
```

To add for Task B:
```
pandas>=2.0.0
matplotlib>=3.8.0
jinja2>=3.1.0
```

## Module Conventions

### Existing (do not modify unless PLAN.md says so)

- **`src/db_introspect.py`** — `get_schema(engine) -> dict`, `list_databases(engine) -> list[str]`. Uses SQLAlchemy Inspector. Filters system schemas. Returns nested dict with tables → columns + foreign_keys.
- **`src/context_builder.py`** — `build_context(schema: dict) -> str`. Compact markdown. No headers larger than `##`. Token-efficient.
- **`src/llm_client.py`** — `_generate(api_key, prompt)` with model fallback on 503. `generate_sql(question, schema_context, api_key)` strips markdown fences. `describe_results(question, sql, results, api_key)` truncates to 20 rows.
- **`src/pipeline.py`** — `answer_question(engine, schema_context, question, api_key) -> dict`. Returns `{"sql", "rows", "answer"}` or `{"sql", "error"}` on SQL failure.
- **`main.py`** — interactive CLI loop. Must remain functional after Task B work.

### New (build per PLAN.md)

- **`src/planner.py`** — `generate_plan(schema_context, api_key, n_items=5) -> list[dict]`. Each item: `{title, question, viz_type, x_label, y_label}`. `viz_type` ∈ {bar, line, pie, scatter, hist}.
- **`src/visualizer.py`** — `render(df, viz_type, title, x_label, y_label, out_path) -> str`. Matplotlib `Agg` backend. Dispatches on viz_type.
- **`src/report.py`** — `build_html(items, out_path) -> None`. Self-contained HTML with base64-embedded PNGs.
- **`src/llm_client.py` additions** — `generate_insight(question, sql, results, api_key) -> str`. Business takeaway, not recap.
- **`generate_report.py`** — orchestrator. Handles per-item SQL failure with one retry, never crashes the whole report.

## Build Order

Q&A mode (Task A) is complete and tagged `gemini-qa-v1`. Do not refactor it.

For Task B, follow **PLAN.md** strictly:
1. Dependencies
2. Planner
3. Visualizer
4. Insight generator
5. Report assembler
6. Orchestrator
7. Commit + share

**Stop after every step. Verify by running the test snippet in PLAN.md. Do not proceed until the human confirms.**

## What NOT to do

- Don't use `mysql-connector-python` directly — SQLAlchemy + pymysql only.
- Don't use raw `information_schema` queries when Inspector methods exist.
- Don't query actual table data during introspection.
- Don't commit `.env` or `output/`.
- Don't break the existing Q&A mode while building the report mode.
- Don't merge planner + visualizer + report into one file.
- Don't add CSS frameworks. Plain inline CSS in the Jinja template.
- Don't trust LLM output without validation. Parse → validate → retry once → fail loudly.
- Don't add Streamlit, FastAPI, or any web framework. The deliverable is a static HTML file.
- Don't add unnecessary abstractions (no Strategy pattern for viz types — a dispatch dict is enough).
- Don't write more than ~20 lines per file in a single shot. Build incrementally and let the human read each addition.
