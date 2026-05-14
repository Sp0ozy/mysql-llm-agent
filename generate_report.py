import os
import re
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.context_builder import build_context
from src.db_introspect import get_schema
from src.planner import generate_plan
from src.processing import process_plan_item
from src.report import build_html
from src.visualizer import save_figure

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


def _safe_filename(title: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "chart"
    return f"{index:02d}_{slug}.png"


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

        items = []
        for i, item in enumerate(plan):
            print(f"[{i + 1}/{len(plan)}] {item['title']}")
            result = process_plan_item(engine, item, i + 1, schema, schema_context, api_key)
            if "fig" in result:
                png_path = str(OUTPUT_DIR / _safe_filename(result["title"], i + 1))
                save_figure(result["fig"], png_path)
                result["png_path"] = png_path
            items.append(result)
    finally:
        engine.dispose()

    build_html(items, str(REPORT_PATH))
    print(f"\nReport written to: {REPORT_PATH.resolve()}")


if __name__ == "__main__":
    main()
