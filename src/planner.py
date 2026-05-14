import json

from google.genai import types

from .llm_client import _generate

ALLOWED_VIZ = {"bar", "line", "pie", "scatter", "hist"}
REQUIRED_KEYS = {"title", "question", "viz_type", "x_label", "y_label"}

PLAN_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title":    types.Schema(type=types.Type.STRING),
            "question": types.Schema(type=types.Type.STRING),
            "viz_type": types.Schema(type=types.Type.STRING, enum=["bar", "line", "pie", "scatter", "hist"]),
            "x_label":  types.Schema(type=types.Type.STRING),
            "y_label":  types.Schema(type=types.Type.STRING),
        },
        required=["title", "question", "viz_type", "x_label", "y_label"],
    ),
)


def _build_prompt(schema_context: str, n_items: int) -> str:
    return f"""You are a senior data analyst. Given the database schema below, propose {n_items} useful business visualizations.

Rules:
- "viz_type" MUST be one of: "bar", "line", "pie", "scatter", "hist".
- "question" is a natural-language description that a SQL generator will turn into a query — it must be answerable from the schema alone.
- Prefer aggregations a business user would actually care about (totals, trends, distributions, comparisons).
- No duplicates. No raw-row dumps.

Schema:
{schema_context}"""


def _validate(items: list) -> list[dict]:
    """Belt-and-braces post-pass: drop any item that slipped through with bad keys/viz_type."""
    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not REQUIRED_KEYS.issubset(item.keys()):
            continue
        if item["viz_type"] not in ALLOWED_VIZ:
            continue
        valid.append({k: item[k] for k in REQUIRED_KEYS})
    return valid


def generate_plan(schema_context: str, api_key: str, n_items: int = 5) -> list[dict]:
    """Ask Gemini for a structured JSON plan of N visualizations."""
    prompt = _build_prompt(schema_context, n_items)
    raw = _generate(api_key, prompt, response_mime_type="application/json", response_schema=PLAN_SCHEMA)
    items = json.loads(raw)
    if not isinstance(items, list):
        raise ValueError(f"Planner expected a JSON array, got {type(items).__name__}")
    return _validate(items)
