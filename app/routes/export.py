from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.state import RUNS
from src.report import build_html
from src.visualizer import save_figure

OUTPUT_DIR = Path("output")
router = APIRouter()


@router.post("/export/{run_id}")
async def export_html(run_id: str):
    run = RUNS.get(run_id)
    if not run or run.status != "done":
        raise HTTPException(400, "Run not complete")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for i, result in enumerate(run.results):
        if result is None:
            continue
        if result.error:
            items.append({"title": result.title, "sql": result.sql, "error": result.error})
        elif result.fig:
            png_path = str(OUTPUT_DIR / f"{run_id}_{i:02d}.png")
            save_figure(result.fig, png_path)
            items.append({
                "title": result.title,
                "sql": result.sql,
                "png_path": png_path,
                "insight": result.insight,
            })

    report_path = str(OUTPUT_DIR / f"{run_id}_report.html")
    build_html(items, report_path)
    return FileResponse(report_path, media_type="text/html", filename="report.html")
