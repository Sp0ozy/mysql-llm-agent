from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app import deps

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def dashboard(request: Request):
    schema, _ = deps.get_schema_context()
    tables = [t["name"] for t in schema.get("tables", [])]
    return templates.TemplateResponse(request, "dashboard.html.j2", {"tables": tables})
