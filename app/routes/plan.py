from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

from app import deps, state
from app.state import ALLOWED_VIZ, CURRENT_PLAN, PlanItem
from src.planner import generate_plan as llm_generate_plan

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_VIZ_OPTIONS = sorted(ALLOWED_VIZ)


def _plan_table_response(request: Request):
    return templates.TemplateResponse(
        request, "partials/_plan_table.html.j2",
        {"plan": CURRENT_PLAN, "viz_options": _VIZ_OPTIONS},
    )


@router.post("/plan")
async def generate_plan(request: Request, n_items: int = Form(5)):
    _, schema_context = deps.get_schema_context()
    api_key = deps.get_api_key()
    raw = llm_generate_plan(schema_context, api_key, n_items=n_items)
    state.CURRENT_PLAN.clear()
    state.CURRENT_PLAN.extend(PlanItem(**item) for item in raw)
    return _plan_table_response(request)


@router.post("/plan/row")
async def add_row(request: Request):
    state.CURRENT_PLAN.append(
        PlanItem(title="", question="", viz_type="bar", x_label="", y_label="")
    )
    return _plan_table_response(request)


@router.patch("/plan/row/{i}")
async def update_row(
    request: Request,
    i: int,
    title: str = Form(""),
    question: str = Form(""),
    viz_type: str = Form("bar"),
    x_label: str = Form(""),
    y_label: str = Form(""),
):
    if viz_type not in ALLOWED_VIZ:
        viz_type = "bar"
    if 0 <= i < len(state.CURRENT_PLAN):
        state.CURRENT_PLAN[i] = PlanItem(
            title=title, question=question, viz_type=viz_type,
            x_label=x_label, y_label=y_label,
        )
    item = state.CURRENT_PLAN[i] if 0 <= i < len(state.CURRENT_PLAN) else None
    return templates.TemplateResponse(
        request, "partials/_plan_row.html.j2",
        {"item": item, "index": i, "viz_options": _VIZ_OPTIONS},
    )


@router.delete("/plan/row/{i}")
async def delete_row(request: Request, i: int):
    if 0 <= i < len(state.CURRENT_PLAN):
        state.CURRENT_PLAN.pop(i)
    return _plan_table_response(request)
