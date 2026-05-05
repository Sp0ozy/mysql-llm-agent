import re
import google.generativeai as genai


def _configure(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")


def generate_sql(question: str, schema_context: str, api_key: str) -> str:
    """Ask Gemini to write a single SQL query answering the question."""
    model = _configure(api_key)

    prompt = f"""You are a MySQL expert. Given the database schema below, write a single SQL query that answers the user's question.
        Rules:
        - Return ONLY the SQL query, no markdown fences, no explanation.
        - Use only tables and columns from the schema.
        - Prefer aggregations over returning raw rows when the question asks for a metric.
        
        Schema:
        {schema_context}
        
        Question: {question}
        SQL:"""

    response = model.generate_content(prompt)
    sql = response.text.strip()

    # Strip markdown fences defensively (```sql ... ``` or ``` ... ```)
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


def describe_results(question: str, sql: str, results: list[dict], api_key: str) -> str:
    """Ask Gemini to explain the query results in plain language."""
    model = _configure(api_key)

    truncated = results[:20]

    prompt = f"""A user asked: "{question}"
        This SQL was executed:
        {sql}
        Results (first 20 rows):
        {truncated}
        Write a 2-3 sentence answer to the user's question based on these results. Do not mention the SQL or the schema. Speak as if answering the user directly."""

    response = model.generate_content(prompt)
    return response.text.strip()
