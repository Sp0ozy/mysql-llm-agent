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

## Notes

- Uses `google-genai` SDK. Models are tried in priority order: `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-1.5-flash`. If the top model is overloaded (503), the next one is used automatically. Free tier: ~15 requests/min, 1500/day.
- Schema introspection reads only metadata — no table data is ever fetched during setup.
- Rows returned by SQL are capped at 20 before being sent to Gemini to keep token usage low.
