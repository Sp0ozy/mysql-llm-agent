# mysql-llm-agent

## What it does

Connects to a remote MySQL database, introspects its schema (tables, columns, foreign keys — no actual data), and uses Google Gemini to answer natural-language questions about it. You type a question; the tool generates SQL, executes it, and replies in plain English.

## Architecture

1. **Introspect** — `db_introspect.py` reads schema metadata via SQLAlchemy Inspector
2. **Context** — `context_builder.py` formats the schema into a compact markdown string
3. **Generate SQL** — `llm_client.generate_sql()` sends the context + question to Gemini
4. **Execute** — `pipeline.py` runs the SQL against the live database
5. **Describe** — `llm_client.describe_results()` asks Gemini to summarise the results in plain language

## Setup

```bash
git clone <repo-url>
cd mysql-llm-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
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

Get a free Gemini API key at **aistudio.google.com** → "Get API key".
Leave `DB_NAME` blank on the first run to discover available databases.

## Usage

### Q&A mode

```bash
python main.py
```

The schema context is printed once on startup, then you get an interactive prompt:

```
Question (or 'exit'): How many payments are there?

SQL: SELECT COUNT(*) FROM payments
Answer: There are 33,461 payments recorded in the system.
```

Type `exit` to quit.

### Report mode

```bash
python generate_report.py
```

Generates a self-contained HTML report with 4–6 visualizations and business insights, driven entirely from the schema. The agent:

1. **Plans** — `planner.py` asks Gemini for a JSON list of visualizations a business user would care about (`{title, question, viz_type, x_label, y_label}`)
2. **Queries** — for each plan item, generates SQL, executes it, and retries once with the error fed back if the query fails
3. **Visualizes** — `visualizer.py` renders the result as a matplotlib chart (bar, line, pie, scatter, or histogram)
4. **Explains** — `llm_client.generate_insight()` writes a 1–2 sentence business takeaway per chart
5. **Assembles** — `report.py` renders everything into a single HTML file with base64-embedded PNGs

Output is written to `output/report.html`. One failed item never crashes the whole report — failures appear inline with the SQL that was attempted.

## Notes

- Uses `google-genai` SDK. Models are tried in priority order with automatic fallback on both `503 UNAVAILABLE` and `429 RESOURCE_EXHAUSTED` errors, so transient overloads and per-minute quota limits do not break a run. Free tier: ~15 requests/min, 1500/day.
- Schema introspection reads only metadata — no table data is ever fetched during setup.
- Rows returned by SQL are capped at 20 before being sent to Gemini to keep token usage low.
- The HTML report is fully self-contained (PNGs embedded as base64) so it can be shared or graded as a single file. The `output/` directory is gitignored.
