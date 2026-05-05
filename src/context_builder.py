def build_context(schema: dict) -> str:
    """Convert a schema dict into a compact markdown string for the LLM."""
    lines = [f"Database: {schema['database']}", ""]

    for table in schema["tables"]:
        lines.append(f"Table: {table['name']}")
        lines.append("Columns:")
        for col in table["columns"]:
            parts = [f"  {col['name']}: {col['type']}"]
            if col["primary_key"]:
                parts.append("PRIMARY KEY")
            if not col["nullable"]:
                parts.append("NOT NULL")
            else:
                parts.append("NULL allowed")
            lines.append(", ".join(parts))

        if table["foreign_keys"]:
            lines.append("Foreign Keys:")
            for fk in table["foreign_keys"]:
                lines.append(f"  {fk['column']} -> {fk['references_table']}.{fk['references_column']}")

        lines.append("")

    return "\n".join(lines).strip()
