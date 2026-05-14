# mysql-llm-agent

Connects to a remote MySQL database, introspects its schema, and uses Google Gemini for two workflows:

- **Q&A mode** — ask a natural-language question, get SQL + a plain-English answer
- **Report mode** — auto-generate a full analytical report (charts + insights) from schema alone

---

## Setup

```bash
git clone <repo-url>
cd mysql-llm-agent
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```
DB_HOST=<host>
DB_PORT=3306
DB_USER=<user>
DB_PASSWORD=<password>
DB_NAME=<database>
GEMINI_API_KEY=<your-gemini-api-key>
```

Get a free Gemini API key at **aistudio.google.com → Get API key**.

---

## Usage

### Interactive dashboard (FastAPI + HTMX)

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

1. The schema is loaded on startup and shown at the top.
2. Click **Generate plan** — Gemini proposes 5 chart items based on your schema.
3. Edit any row inline (title, question, chart type, axis labels).
4. Click **Run report** — each item runs in the background; results stream in as they complete.
5. Click **Export static HTML** when done — downloads a self-contained report file.

### CLI batch report

```bash
python generate_report.py
```

Writes `output/report.html` — a self-contained file with embedded charts and insights.

### Q&A CLI

```bash
python main.py
```

```
Question (or 'exit'): How many payments are there?

SQL: SELECT COUNT(*) FROM payments
Answer: There are 33,461 payments recorded in the system.
```

---

## Architecture

### Q&A pipeline

1. **Introspect** — `db_introspect.py` reads schema metadata via SQLAlchemy Inspector (no table data)
2. **Context** — `context_builder.py` formats schema into a compact markdown string
3. **SQL guard** — `sql_guard.validate_and_prepare()` rejects DML/DDL and validates table names
4. **Generate SQL** — `llm_client.generate_sql()` sends context + question to Gemini
5. **Execute** — `pipeline.py` runs the SQL with a 30 s server-side timeout
6. **Describe** — `llm_client.describe_results()` summarises results in plain English

### Report pipeline (per chart item)

1. `planner.py` — Gemini generates a structured plan (title, question, chart type, axis labels) via `response_schema`
2. `processing.py` — per item: SQL guard → execute → DataFrame → `visualizer.make_figure()`→ `llm_client.generate_insight()`
3. `report.py` / `app/routes/export.py` — assembles items into self-contained HTML

### FastAPI app

- `app/main.py` — FastAPI app with lifespan; mounts all routers
- `app/deps.py` — engine + schema singletons, auth stub
- `app/state.py` — in-memory `CURRENT_PLAN` and `RUNS` (single-process v1)
- `app/runner.py` — async background task via `asyncio.to_thread`
- `app/routes/` — pages, plan CRUD, run polling, chart serving, HTML export
- `templates/` — Jinja2 templates; partials swapped in by HTMX

---

## Security guardrails

| Guardrail | Where enforced |
|---|---|
| Read-only SQL (SELECT/WITH only, no DML/DDL) | `sql_guard.validate_and_prepare()` — called before every execution |
| Table name validation against live schema | `sql_guard` — rejects references to unknown tables |
| 30 s query hard cap | `SET SESSION max_execution_time = 30000` prepended to every query |
| Prompt injection defence | Untrusted content (schema, SQL, results) wrapped in `<<<UNTRUSTED:…>>>` delimiters |
| LLM safety filters | `BLOCK_ONLY_HIGH` on all Gemini harm categories |
| Model fallback on overload | `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.5-flash-lite` → `gemini-2.0-flash-lite` → `gemini-1.5-flash` |

---

## Notes

- Schema introspection reads metadata only — no table data is fetched during setup.
- Result rows sent to Gemini are capped at 20 to keep token usage low.
- Free Gemini tier: ~15 requests/min, 1 500/day.
- Auth is a stub (`"local"` user) — real auth planned for v2.
- State is in-memory; restarting the server clears all runs.
