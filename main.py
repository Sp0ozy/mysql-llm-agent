import urllib.parse
from pprint import pprint

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine

from src.db_introspect import get_schema, list_databases
from src.context_builder import build_context

load_dotenv()

password = urllib.parse.quote_plus(os.environ["DB_PASSWORD"])
host = os.environ["DB_HOST"]
port = os.environ.get("DB_PORT", "3306")
user = os.environ["DB_USER"]
db_name = os.environ.get("DB_NAME", "")

if not db_name:
    discovery_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/"
    discovery_engine = create_engine(discovery_url)
    databases = list_databases(discovery_engine)
    print("Available databases:", databases)
    discovery_engine.dispose()
    raise SystemExit("Set DB_NAME in .env and re-run.")

url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
engine = create_engine(url)

schema = get_schema(engine)
pprint(schema)

print("\n--- Schema Context (what the LLM will see) ---\n")
print(build_context(schema))

engine.dispose()
