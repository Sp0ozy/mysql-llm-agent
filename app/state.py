from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import matplotlib.figure


ALLOWED_VIZ = {"bar", "line", "pie", "scatter", "hist"}


@dataclass
class PlanItem:
    title: str
    question: str
    viz_type: str
    x_label: str
    y_label: str


@dataclass
class ItemResult:
    title: str
    sql: str
    insight: str | None = None
    error: str | None = None
    fig: matplotlib.figure.Figure | None = None
    rows: list[dict] | None = None


@dataclass
class RunState:
    run_id: str
    plan: list[PlanItem]
    results: list[ItemResult | None] = field(default_factory=list)
    status: str = "editing"   # editing | running | done | failed
    cursor: int = 0


# Draft plan shared across requests (single-user)
CURRENT_PLAN: list[PlanItem] = []

# In-progress and completed runs keyed by run_id
RUNS: dict[str, RunState] = {}


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]
