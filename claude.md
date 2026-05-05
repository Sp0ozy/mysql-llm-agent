# CLAUDE.md — MySQL LLM Context Generator

## Project Goal

Build a Python tool that:
1. Connects to a remote MySQL server
2. Introspects schema (tables, columns, types, foreign keys) — NOT data
3. Generates a structured context document describing the database
4. Uses Google Gemini API to generate SQL from natural-language questions
5. Executes the SQL and uses Gemini again to describe results in natural language

This is a homework assignment for a Fintech course on LLM tooling. The grading criterion is whether the context generation enables the LLM to produce correct SQL.

## Constraints

- Python 3.11+
- Use SQLAlchemy 2.0 (with `pymysql` driver), NOT raw `mysql-connector-python`
- Use `google-generativeai` for Gemini API
- Use `python-dotenv` for credentials
- DO NOT query actual table data during introspection — only metadata via `information_schema` or SQLAlchemy's `Inspector`
- Code must be readable and explainable; the human will review it line-by-line before submission

## Project Structure
mysql-llm-agent/
├── .env                    # credentials (gitignored)
├── .env.example            # template, committed
├── .gitignore
├── README.md
├── requirements.txt
├── src/
│   ├── init.py
│   ├── db_introspect.py    # schema extraction
│   ├── context_builder.py  # format schema → markdown context
│   ├── llm_client.py       # Gemini wrappers
│   └── pipeline.py         # orchestrate end-to-end
└── main.py                 # CLI entry point

## Environment Variables (`.env`)
DB_HOST=87.110.123.151
DB_PORT=3306
DB_USER=fita
DB_PASSWORD=2026-04-28
DB_NAME=                    # to be discovered, leave blank initially
GEMINI_API_KEY=

`.env.example` should mirror this with empty values.

## requirements.txt
sqlalchemy>=2.0.0
pymysql>=1.1.0
google-generativeai>=0.8.0
python-dotenv>=1.0.0

## Module Specifications

### `src/db_introspect.py`

Single function: `get_schema(engine) -> dict`

Use `sqlalchemy.inspect(engine)`. Return this exact structure:

```python
{
    "database": "<db_name>",
    "tables": [
        {
            "name": "orders",
            "columns": [
                {
                    "name": "id",
                    "type": "INTEGER",          # str(col["type"])
                    "nullable": False,
                    "primary_key": True
                },
                ...
            ],
            "foreign_keys": [
                {
                    "column": "customer_id",
                    "references_table": "customers",
                    "references_column": "id"
                },
                ...
            ]
        },
        ...
    ]
}
```

Filter out system schemas: `information_schema`, `mysql`, `performance_schema`, `sys`.

Include a helper `list_databases(engine) -> list[str]` for the initial discovery step (since `DB_NAME` is unknown).

### `src/context_builder.py`

Function: `build_context(schema: dict) -> str`

Convert the schema dict into a markdown string the LLM will consume. Format:
Database: <name>
Table: orders
Columns:

id: INTEGER, PRIMARY KEY, NOT NULL
customer_id: INTEGER, NOT NULL
total: DECIMAL(10,2), NULL allowed

Foreign Keys:

customer_id → customers.id


Keep it compact. The LLM pays for every token. No headers larger than `##`.

### `src/llm_client.py`

Initialize Gemini with `google.generativeai.configure(api_key=...)` and `GenerativeModel("gemini-2.5-flash")` (or `gemini-1.5-flash` if 2.5 unavailable — use the flash tier, not pro, to stay within free quota).

Two functions:

#### `generate_sql(question: str, schema_context: str) -> str`

Prompt template:
You are a MySQL expert. Given the database schema below, write a single SQL query that answers the user's question.
Rules:

Return ONLY the SQL query, no markdown fences, no explanation.
Use only tables and columns from the schema.
Prefer aggregations over returning raw rows when the question asks for a metric.

Schema:
{schema_context}
Question: {question}
SQL:

Strip any markdown fences from the response (```sql ... ```) defensively.

#### `describe_results(question: str, sql: str, results: list[dict]) -> str`

Prompt template:
A user asked: "{question}"
This SQL was executed:
{sql}
Results (first 20 rows):
{results}
Write a 2-3 sentence answer to the user's question based on these results. Do not mention the SQL or the schema. Speak as if answering the user directly.

Truncate `results` to 20 rows before sending (token cost).

### `src/pipeline.py`

Function: `answer_question(engine, schema_context: str, question: str) -> dict`

Flow:
1. Call `generate_sql(question, schema_context)` → get SQL string
2. Execute SQL via `engine.connect().execute(text(sql))` → fetch all rows as list of dicts
3. Call `describe_results(question, sql, rows)` → get description
4. Return `{"sql": sql, "rows": rows, "answer": description}`

Wrap the SQL execution in try/except. If it fails, return `{"sql": sql, "error": str(e)}` so the human can see what the LLM generated.

### `main.py`

CLI loop:
1. Load `.env`
2. Build engine from env vars (URL-encode the password using `urllib.parse.quote_plus`)
3. Call `get_schema(engine)` → cache once
4. Call `build_context(schema)` → cache once
5. `while True:` prompt user for a question, run `answer_question`, print SQL + answer
6. Type `exit` to quit

Print the schema context once on startup so the user can see what the LLM sees.

## .gitignore
.env
pycache/
*.pyc
venv/
.venv/
*.egg-info/
.idea/
.vscode/

## README.md

Sections:
1. **What it does** — 2-3 sentences
2. **Architecture** — bullet list: introspect → context → LLM → SQL → execute → describe
3. **Setup** — clone, venv, install, copy `.env.example` to `.env`, fill in keys
4. **Usage** — `python main.py`, ask questions
5. **Notes** — mention Gemini model used, free-tier quota caveats

## Build Order (strict)

1. Project structure + `.gitignore` + `requirements.txt` + `.env.example`
2. `db_introspect.py` + a quick test in `main.py` that just `pprint`s the schema
3. After human confirms schema looks right: `context_builder.py`
4. `llm_client.py` (both functions)
5. `pipeline.py`
6. Wire up full `main.py` CLI loop
7. README

Stop after each step and let the human verify before continuing.

## What NOT to do

- Don't use `mysql-connector-python` directly — SQLAlchemy with pymysql only.
- Don't use raw `information_schema` queries when Inspector methods exist.
- Don't query actual table data during introspection.
- Don't commit `.env`.
- Don't add features beyond the spec (no Streamlit UI, no fancy logging, no retry logic).
- Don't use `pandas` — return rows as plain dicts.