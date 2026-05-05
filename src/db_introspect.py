from sqlalchemy import inspect

SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}


def list_databases(engine) -> list[str]:
    """Return all non-system database names visible to the current user."""
    with engine.connect() as conn:
        rows = conn.execute(__import__("sqlalchemy").text("SHOW DATABASES"))
        return [row[0] for row in rows if row[0] not in SYSTEM_SCHEMAS]


def get_schema(engine) -> dict:
    """
    Introspect the connected database and return a structured schema dict.
    Only reads metadata — never queries actual table data.
    """
    inspector = inspect(engine)
    db_name = engine.url.database

    tables = []
    for table_name in inspector.get_table_names():
        # --- columns ---
        columns = []
        pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": col["name"] in pk_cols,
            })

        # --- foreign keys ---
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            for local_col, ref_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                foreign_keys.append({
                    "column": local_col,
                    "references_table": fk["referred_table"],
                    "references_column": ref_col,
                })

        tables.append({
            "name": table_name,
            "columns": columns,
            "foreign_keys": foreign_keys,
        })

    return {"database": db_name, "tables": tables}
