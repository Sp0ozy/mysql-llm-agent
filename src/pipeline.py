from sqlalchemy import text

from src.llm_client import generate_sql, describe_results


def answer_question(engine, schema_context: str, question: str, api_key: str) -> dict:
    """
    Full pipeline: question -> SQL -> execute -> natural-language answer.
    Returns a dict with keys: sql, rows, answer  (or sql, error on failure).
    """
    sql = generate_sql(question, schema_context, api_key)

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
    except Exception as e:
        return {"sql": sql, "error": str(e)}

    answer = describe_results(question, sql, rows, api_key)
    return {"sql": sql, "rows": rows, "answer": answer}
