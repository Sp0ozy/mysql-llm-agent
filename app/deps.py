import os
import urllib.parse

from sqlalchemy import create_engine

from src.context_builder import build_context
from src.db_introspect import get_schema

_engine = None
_schema: dict | None = None
_schema_context: str | None = None


def init() -> None:
    global _engine, _schema, _schema_context
    password = urllib.parse.quote_plus(os.environ["DB_PASSWORD"])
    url = (
        f"mysql+pymysql://{os.environ['DB_USER']}:{password}"
        f"@{os.environ['DB_HOST']}:{os.environ.get('DB_PORT', '3306')}"
        f"/{os.environ['DB_NAME']}"
    )
    _engine = create_engine(url)
    _schema = get_schema(_engine)
    _schema_context = build_context(_schema)


def shutdown() -> None:
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None


def get_engine():
    return _engine


def get_schema_context() -> tuple[dict, str]:
    return _schema, _schema_context


def get_api_key() -> str:
    return os.environ["GEMINI_API_KEY"]


def get_current_user() -> str:
    return "local"
