import re
from google import genai
from google.genai import errors

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

_client: genai.Client | None = None
_client_key: str | None = None


def _get_client(api_key: str) -> genai.Client:
    global _client, _client_key
    if _client is None or _client_key != api_key:
        _client = genai.Client(api_key=api_key)
        _client_key = api_key
    return _client


def _generate(api_key: str, prompt: str) -> str:
    """Try each model in priority order, falling back on 503 errors."""
    client = _get_client(api_key)
    for model in MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
        except errors.ServerError as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"[warn] {model} unavailable, trying next model...")
                continue
            raise
    raise RuntimeError("All Gemini models are currently unavailable. Try again later.")


def generate_sql(question: str, schema_context: str, api_key: str) -> str:
    """Ask Gemini to write a single SQL query answering the question."""
    prompt = f"""You are a MySQL expert. Given the database schema below, write a single SQL query that answers the user's question.
        Rules:
        - Return ONLY the SQL query, no markdown fences, no explanation.
        - Use only tables and columns from the schema.
        - Prefer aggregations over returning raw rows when the question asks for a metric.

        Schema:
        {schema_context}

        Question: {question}
        SQL:"""

    sql = _generate(api_key, prompt)

    # Strip markdown fences defensively (```sql ... ``` or ``` ... ```)
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


def describe_results(question: str, sql: str, results: list[dict], api_key: str) -> str:
    """Ask Gemini to explain the query results in plain language."""
    truncated = results[:20]

    prompt = f"""A user asked: "{question}"
        This SQL was executed:
        {sql}
        Results (first 20 rows):
        {truncated}
        Write a 2-3 sentence answer to the user's question based on these results. Do not mention the SQL or the schema. Speak as if answering the user directly."""

    return _generate(api_key, prompt)
