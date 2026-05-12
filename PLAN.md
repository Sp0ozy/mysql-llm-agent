# PLAN.md — Task B: Visualization Agent

## What this adds to the existing project

The current repo (tagged `pre-task2`) answers a single natural-language question against the DB. Task B requires a multi-step agent that:

1. Generates a **plan** of N data visualizations from the schema context
2. For each plan item: generates SQL → executes → creates a chart → writes an insight
3. Combines everything into **one self-contained HTML report**
4. Shared via GitHub with instructor

## New deliverable

`python generate_report.py` produces `output/report.html` containing 4–6 visualizations + business insights from the MySQL database.

## Files to CREATE

| File | Purpose |
|---|---|
| `src/planner.py` | schema_context → JSON plan |
| `src/visualizer.py` | DataFrame + viz spec → PNG |
| `src/report.py` | items list → self-contained HTML |
| `templates/report.html.j2` | Jinja2 template |
| `generate_report.py` | orchestrator at project root |
| `output/` | gitignored directory for PNGs + report.html |

## Files to MODIFY

| File | Change |
|---|---|
| `src/llm_client.py` | add `generate_plan()` and `generate_insight()` |
| `requirements.txt` | add `pandas`, `matplotlib`, `jinja2` |
| `.gitignore` | add `output/` |
| `README.md` | add usage section for report mode |

## Files to LEAVE UNTOUCHED

- `src/db_introspect.py`
- `src/context_builder.py`
- `src/pipeline.py` (Q&A mode still works)
- `main.py` (Q&A loop stays)

## Build Order (strict — stop after each step, verify, then continue)

### Step 1 — Dependencies

Add to `requirements.txt`:
```
pandas>=2.0.0
matplotlib>=3.8.0
jinja2>=3.1.0
```
Then:
```bash
pip install -r requirements.txt
python -c "import pandas, matplotlib, jinja2; print('ok')"
```
**Stop and verify** the print succeeds before moving on.

---

### Step 2 — Planner

Create `src/planner.py`.

**Function signature:**
```python
def generate_plan(schema_context: str, api_key: str, n_items: int = 5) -> list[dict]:
```

**Each plan item structure:**
```python
{
    "title": str,           # e.g. "Revenue by region"
    "question": str,        # natural-language description fed to SQL generator
    "viz_type": str,        # one of: "bar", "line", "pie", "scatter", "hist"
    "x_label": str,
    "y_label": str
}
```

**Prompt requirements:**
- Ask Gemini to return ONLY a JSON array, no prose, no markdown fences.
- Constrain `viz_type` to the 5 allowed values.
- Ask for `n_items` aggregations that a business user would actually want.

**Robustness:**
- Strip ` ```json ` / ` ``` ` fences defensively (same pattern as `generate_sql`).
- Parse with `json.loads`. On `JSONDecodeError`, retry ONCE with a reinforcement prompt that includes the broken output. If retry also fails, raise.
- Validate every item has all 5 keys and `viz_type` is in the allowed set. Drop invalid items.

**Test before moving on:**
```python
from src.planner import generate_plan
plan = generate_plan(schema_context, api_key)
import json; print(json.dumps(plan, indent=2))
```
Eyeball the plan — does it make sense for THIS database?

---

### Step 3 — Visualizer

Create `src/visualizer.py`.

**Function signature:**
```python
def render(
    df: pd.DataFrame,
    viz_type: str,
    title: str,
    x_label: str,
    y_label: str,
    out_path: str,
) -> str:
```

Returns the saved path.

**Implementation rules:**
- `import matplotlib; matplotlib.use("Agg")` at top of file (no GUI backend).
- Dispatch on `viz_type` to 5 small helper functions.
- Assume first column is x-axis, second column is y-axis (or document the chosen convention).
- For `pie`: use first column as labels, second as values.
- For `hist`: use first numeric column.
- Always: set title, x_label, y_label, `plt.tight_layout()`, save at 150 DPI, `plt.close()`.

**Test before moving on:**
```python
import pandas as pd
from src.visualizer import render
df = pd.DataFrame({"region": ["A","B","C"], "revenue": [100, 200, 150]})
render(df, "bar", "Test", "Region", "Revenue", "output/test.png")
```
Open the PNG. Does it look right?

---

### Step 4 — Insight generator

Add to `src/llm_client.py`:

```python
def generate_insight(question: str, sql: str, results: list[dict], api_key: str) -> str:
```

**Different from `describe_results`:**
- `describe_results` = neutral recap of the data
- `generate_insight` = 1–2 sentence **business takeaway** ("Region A dominates revenue — 40% of total despite only 20% of customers")

**Prompt should explicitly forbid:**
- Recapping numbers the user can already see
- Mentioning SQL or the schema
- Filler phrases like "this shows that…"

Truncate results to 20 rows before sending.

---

### Step 5 — Report assembler

Create `templates/report.html.j2`:
- Minimal HTML: `<title>`, `<h1>` for report name, then a section per item.
- Each section: `<h2>{{ title }}</h2>`, `<img src="data:image/png;base64,{{ png_b64 }}">`, `<p>{{ insight }}</p>`, `<details><summary>SQL</summary><pre>{{ sql }}</pre></details>`.
- Plain inline CSS at the top. No frameworks. Max-width ~900px, sensible padding.

Create `src/report.py`:
```python
def build_html(items: list[dict], out_path: str) -> None:
```

Each item: `{"title", "png_path", "insight", "sql"}` (or `"error"` if step failed).
- Base64-encode each PNG and pass as `png_b64` so the HTML is self-contained.
- Render template with Jinja2, write to `out_path`.

---

### Step 6 — Orchestrator

Create `generate_report.py` at project root.

**Flow:**
1. Load `.env`, build engine (same as `main.py`)
2. `schema = get_schema(engine)` → `context = build_context(schema)`
3. `plan = generate_plan(context, api_key)`
4. For each plan item:
   - `sql = generate_sql(item["question"], context, api_key)`
   - Try execute → `pd.DataFrame(rows)`. On error: retry SQL generation ONCE, feeding the error back as additional context. If still failing, record error item and continue.
   - `png_path = visualizer.render(df, ...)`
   - `insight = generate_insight(item["question"], sql, rows, api_key)`
   - Append to `items`
5. `build_html(items, "output/report.html")`
6. Print absolute path of `report.html`.

**Failure handling:** one bad plan item must NOT crash the whole report. Include failed items with the error message visible in the report.

---

### Step 7 — Commit + share

- Update `README.md` with a "Report mode" section.
- `git add -A && git commit -m "feat: visualization agent for Task B"`
- Push to GitHub.
- Submit repo URL to course.

---

## What NOT to do

- Don't merge planner + visualizer + report into one file. Keep separation.
- Don't use pandas in `db_introspect.py` or `context_builder.py`. Only in viz pipeline.
- Don't make the plan interactive (no chained follow-ups). Single-shot plan.
- Don't add CSS frameworks (Tailwind, Bootstrap). Plain inline CSS only.
- Don't commit `output/`. Add to `.gitignore`.
- Don't trust LLM output without validation. Always parse → validate → retry once → fail loudly.
- Don't bolt new features into existing modules unless listed in "Files to MODIFY". Add new modules instead.
- Don't break the existing Q&A loop. `main.py` must still work after every step.
