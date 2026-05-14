import urllib.parse
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.db_introspect import get_schema, list_databases
from src.context_builder import build_context
from src.pipeline import answer_question

load_dotenv()

password = urllib.parse.quote_plus(os.environ["DB_PASSWORD"])
host = os.environ["DB_HOST"]
port = os.environ.get("DB_PORT", "3306")
user = os.environ["DB_USER"]
db_name = os.environ.get("DB_NAME", "")
api_key = os.environ["GEMINI_API_KEY"]

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
schema_context = build_context(schema)

print("--- Schema Context ---")
print(schema_context)
print("----------------------\n")

while True:
    try:
        question = input("Question (or 'exit'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if question.lower() == "exit":
        break
    if not question:
        continue

    result = answer_question(engine, schema_context, question, api_key, schema=schema)

    print(f"\nSQL: {result['sql']}")
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Answer: {result['answer']}\n")

engine.dispose()
