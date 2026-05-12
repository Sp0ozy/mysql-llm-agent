import base64
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "report.html.j2"
REPORT_TITLE = "MySQL Visualization Report"


def _encode_png(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _prepare(items: list[dict]) -> list[dict]:
    prepared = []
    for item in items:
        out = {
            "title": item.get("title", "Untitled"),
            "sql": item.get("sql", ""),
            "insight": item.get("insight", ""),
            "error": item.get("error"),
            "png_b64": "",
        }
        if not out["error"] and item.get("png_path"):
            out["png_b64"] = _encode_png(item["png_path"])
        prepared.append(out)
    return prepared


def build_html(items: list[dict], out_path: str) -> None:
    """Render items into a self-contained HTML report at out_path."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template(TEMPLATE_NAME)

    prepared = _prepare(items)
    html = template.render(
        report_title=REPORT_TITLE,
        items=prepared,
        item_count=len(prepared),
    )

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
