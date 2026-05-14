import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from matplotlib.backends.backend_agg import FigureCanvasAgg

from app.state import RUNS

router = APIRouter()


@router.get("/charts/{run_id}/{item_id}.png")
async def get_chart(run_id: str, item_id: int):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if item_id >= len(run.results) or run.results[item_id] is None:
        raise HTTPException(404, "Chart not ready")
    result = run.results[item_id]
    if result.fig is None:
        raise HTTPException(404, "No chart for this item")

    buf = io.BytesIO()
    FigureCanvasAgg(result.fig).print_png(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
