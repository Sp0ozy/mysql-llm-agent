from sqlalchemy import text

from src.llm_client import describe_results, generate_sql
from src.sql_guard import SQLGuardError, validate_and_prepare


def answer_question(
    engine, schema_context: str, question: str, api_key: str, schema: dict | None = None
) -> dict:
    """
    Full pipeline: question -> SQL -> execute -> natural-language answer.
    Returns a dict with keys: sql, rows, answer  (or sql, error on failure).
    When schema is provided the SQL guard runs before execution.
    """
    sql = generate_sql(question, schema_context, api_key)

    try:
        if schema is not None:
            sql = validate_and_prepare(sql, schema)
        with engine.connect() as conn:
            if schema is not None:
                conn.execute(text("SET SESSION max_execution_time = 30000"))
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
    except (SQLGuardError, Exception) as e:
        return {"sql": sql, "error": str(e)}

    answer = describe_results(question, sql, rows, api_key)
    return {"sql": sql, "rows": rows, "answer": answer}
