import os
import re
import urllib.parse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.context_builder import build_context
from src.db_introspect import get_schema
from src.llm_client import generate_insight, generate_sql
from src.planner import generate_plan
from src.report import build_html
from src.visualizer import render

OUTPUT_DIR = Path("output")
REPORT_PATH = OUTPUT_DIR / "report.html"
N_ITEMS = 5


def _build_engine() -> "object":
    password = urllib.parse.quote_plus(os.environ["DB_PASSWORD"])
    host = os.environ["DB_HOST"]
    port = os.environ.get("DB_PORT", "3306")
    user = os.environ["DB_USER"]
    db_name = os.environ["DB_NAME"]
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)


def _execute_sql(engine, sql: str) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row._mapping) for row in result]


def _safe_filename(title: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "chart"
    return f"{index:02d}_{slug}.png"


def _run_sql_with_retry(engine, question: str, schema_context: str, api_key: str) -> tuple[str, list[dict] | None, str | None]:
    sql = generate_sql(question, schema_context, api_key)
    try:
        rows = _execute_sql(engine, sql)
        return sql, rows, None
    except Exception as first_err:
        retry_question = (
            f"{question}\n\nThe previous SQL failed with error: {first_err}\n"
            "Generate a corrected SQL query that avoids that error."
        )
        try:
            sql_retry = generate_sql(retry_question, schema_context, api_key)
            rows = _execute_sql(engine, sql_retry)
            return sql_retry, rows, None
        except Exception as second_err:
            return sql, None, str(second_err)


def _process_item(engine, item: dict, index: int, schema_context: str, api_key: str) -> dict:
    title = item["title"]
    question = item["question"]
    print(f"[{index}/{N_ITEMS}] {title}")

    sql, rows, sql_err = _run_sql_with_retry(engine, question, schema_context, api_key)
    if sql_err is not None:
        return {"title": title, "sql": sql, "error": f"SQL failed: {sql_err}"}

    if not rows:
        return {"title": title, "sql": sql, "error": "Query returned no rows"}

    try:
        df = pd.DataFrame(rows)
        png_path = str(OUTPUT_DIR / _safe_filename(title, index))
        render(df, item["viz_type"], title, item["x_label"], item["y_label"], png_path)
    except Exception as e:
        return {"title": title, "sql": sql, "error": f"Visualization failed: {e}"}

    try:
        insight = generate_insight(question, sql, rows, api_key)
    except Exception as e:
        insight = f"(insight generation failed: {e})"

    return {"title": title, "sql": sql, "png_path": png_path, "insight": insight}


def main() -> None:
    load_dotenv()
    if not os.environ.get("DB_NAME"):
        raise SystemExit("DB_NAME is required in .env for report mode.")

    api_key = os.environ["GEMINI_API_KEY"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    engine = _build_engine()
    try:
        schema = get_schema(engine)
        schema_context = build_context(schema)

        print("Generating plan...")
        plan = generate_plan(schema_context, api_key, n_items=N_ITEMS)
        if not plan:
            raise SystemExit("Planner returned no valid items.")
        print(f"Planner returned {len(plan)} item(s).")

        items = [_process_item(engine, item, i + 1, schema_context, api_key) for i, item in enumerate(plan)]
    finally:
        engine.dispose()

    build_html(items, str(REPORT_PATH))
    print(f"\nReport written to: {REPORT_PATH.resolve()}")


if __name__ == "__main__":
    main()
