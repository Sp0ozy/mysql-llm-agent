import asyncio
from dataclasses import asdict

from app.state import RUNS, ItemResult
from src.processing import process_plan_item


async def run_plan(
    run_id: str, engine, schema: dict, schema_context: str, api_key: str
) -> None:
    run = RUNS[run_id]
    run.status = "running"
    try:
        for i, item in enumerate(run.plan):
            run.cursor = i
            raw = await asyncio.to_thread(
                process_plan_item, engine, asdict(item), i, schema, schema_context, api_key
            )
            if "error" in raw:
                run.results[i] = ItemResult(
                    title=raw["title"], sql=raw["sql"], error=raw["error"]
                )
            else:
                run.results[i] = ItemResult(
                    title=raw["title"],
                    sql=raw["sql"],
                    insight=raw.get("insight"),
                    fig=raw.get("fig"),
                    rows=raw.get("rows"),
                )
        run.status = "done"
    except Exception as exc:
        run.status = "failed"
        print(f"[error] run {run_id} failed unexpectedly: {exc}")
