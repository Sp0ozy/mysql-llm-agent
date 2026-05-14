from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import deps, runner, state
from app.state import CURRENT_PLAN, RUNS, RunState, new_run_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/run")
async def start_run(request: Request, background_tasks: BackgroundTasks):
    if not CURRENT_PLAN:
        return HTMLResponse("<p>No plan items. Generate a plan first.</p>", status_code=400)

    run_id = new_run_id()
    run = RunState(
        run_id=run_id,
        plan=list(CURRENT_PLAN),
        results=[None] * len(CURRENT_PLAN),
        status="running",
    )
    RUNS[run_id] = run

    background_tasks.add_task(
        runner.run_plan,
        run_id,
        deps.get_engine(),
        *deps.get_schema_context(),
        deps.get_api_key(),
    )

    return templates.TemplateResponse(
        request, "partials/_run_status.html.j2", {"run": run, "run_id": run_id}
    )


@router.get("/run/{run_id}/status")
async def run_status(request: Request, run_id: str):
    run = RUNS.get(run_id)
    if not run:
        return HTMLResponse("<p>Run not found.</p>", status_code=404)

    response = templates.TemplateResponse(
        request, "partials/_run_status.html.j2", {"run": run, "run_id": run_id}
    )
    if run.status in ("done", "failed"):
        response.headers["HX-Trigger"] = "runComplete"
    return response
