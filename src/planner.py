import json
import re

from .llm_client import _generate

ALLOWED_VIZ = {"bar", "line", "pie", "scatter", "hist"}
REQUIRED_KEYS = {"title", "question", "viz_type", "x_label", "y_label"}


def _build_prompt(schema_context: str, n_items: int) -> str:
    return f"""You are a senior data analyst. Given the database schema below, propose {n_items} useful business visualizations.

Rules:
- Return ONLY a JSON array. No prose, no markdown fences, no commentary.
- Each element MUST be an object with EXACTLY these keys: "title", "question", "viz_type", "x_label", "y_label".
- "viz_type" MUST be one of: "bar", "line", "pie", "scatter", "hist".
- "question" is a natural-language description that a SQL generator will turn into a query — it must be answerable from the schema alone.
- Prefer aggregations a business user would actually care about (totals, trends, distributions, comparisons).
- No duplicates. No raw-row dumps.

Schema:
{schema_context}

JSON:"""


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse(raw: str) -> list[dict]:
    return json.loads(_strip_fences(raw))


def _validate(items: list) -> list[dict]:
    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if set(item.keys()) < REQUIRED_KEYS:
            continue
        if item["viz_type"] not in ALLOWED_VIZ:
            continue
        valid.append({k: item[k] for k in REQUIRED_KEYS})
    return valid


def generate_plan(schema_context: str, api_key: str, n_items: int = 5) -> list[dict]:
    """Ask Gemini for a JSON plan of N visualizations. Retry once on parse failure."""
    prompt = _build_prompt(schema_context, n_items)
    raw = _generate(api_key, prompt)

    try:
        items = _parse(raw)
    except json.JSONDecodeError:
        retry_prompt = (
            prompt
            + "\n\nYour previous response was not valid JSON:\n"
            + raw
            + "\n\nReturn ONLY a valid JSON array now. No fences, no prose."
        )
        raw = _generate(api_key, retry_prompt)
        items = _parse(raw)

    if not isinstance(items, list):
        raise ValueError(f"Planner expected a JSON array, got {type(items).__name__}")

    return _validate(items)
