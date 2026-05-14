from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app import deps
from app.routes import charts, export, pages, plan
from app.routes import run as run_routes

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    deps.init()
    yield
    deps.shutdown()


app = FastAPI(title="MySQL LLM Agent", lifespan=lifespan)

app.include_router(pages.router)
app.include_router(plan.router)
app.include_router(run_routes.router)
app.include_router(charts.router)
app.include_router(export.router)
