import pandas as pd

from src.llm_client import generate_insight, generate_sql
from src.visualizer import render


def _run_sql_with_retry(engine, question: str, schema_context: str, api_key: str) -> tuple[str, list[dict] | None, str | None]:
    sql = generate_sql(question, schema_context, api_key)
    try:
        rows = _execute(engine, sql)
        return sql, rows, None
    except Exception as first_err:
        retry_question = (
            f"{question}\n\nThe previous SQL failed with error: {first_err}\n"
            "Generate a corrected SQL query that avoids that error."
        )
        try:
            sql_retry = generate_sql(retry_question, schema_context, api_key)
            rows = _execute(engine, sql_retry)
            return sql_retry, rows, None
        except Exception as second_err:
            return sql, None, str(second_err)


def _execute(engine, sql: str) -> list[dict]:
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row._mapping) for row in result]


def process_plan_item(
    engine,
    item: dict,
    index: int,
    schema,
    schema_context: str,
    api_key: str,
    out_path: str | None = None,
) -> dict:
    """Run one plan item end-to-end. Returns a result dict.

    Success: {title, sql, rows, png_path, insight}  (png_path is None when out_path is None)
    Failure: {title, sql, error}
    """
    title = item["title"]
    question = item["question"]

    sql, rows, sql_err = _run_sql_with_retry(engine, question, schema_context, api_key)
    if sql_err is not None:
        return {"title": title, "sql": sql, "error": f"SQL failed: {sql_err}"}

    if not rows:
        return {"title": title, "sql": sql, "error": "Query returned no rows"}

    png_path = None
    if out_path is not None:
        try:
            df = pd.DataFrame(rows)
            render(df, item["viz_type"], title, item["x_label"], item["y_label"], out_path)
            png_path = out_path
        except Exception as e:
            return {"title": title, "sql": sql, "error": f"Visualization failed: {e}"}

    try:
        insight = generate_insight(question, sql, rows, api_key)
    except Exception as e:
        insight = f"(insight generation failed: {e})"

    return {"title": title, "sql": sql, "rows": rows, "png_path": png_path, "insight": insight}
