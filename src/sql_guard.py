import re

import sqlparse


class SQLGuardError(Exception):
    pass


_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|RENAME|"
    r"GRANT|REVOKE|REPLACE|MERGE|CALL|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

# Captures the first CTE name in: WITH <name> AS (
_CTE_RE = re.compile(r"\bWITH\s+(\w+)\s+AS\s*\(", re.IGNORECASE)

_TABLE_AFTER_FROM = re.compile(r"\bFROM\s+`?(\w+)`?", re.IGNORECASE)
_TABLE_AFTER_JOIN = re.compile(r"\bJOIN\s+`?(\w+)`?", re.IGNORECASE)


def validate_and_prepare(sql: str, schema: dict) -> str:
    """Validate sql is a safe read-only SELECT. Returns cleaned SQL on success.

    Raises SQLGuardError on any violation.
    """
    # 1. Strip comments and trailing semicolons
    sql = sqlparse.format(sql, strip_comments=True).strip().rstrip(";").strip()
    if not sql:
        raise SQLGuardError("Empty SQL after stripping comments.")

    # 2. Reject multi-statement
    statements = [s.strip() for s in sqlparse.split(sql) if s.strip()]
    if len(statements) != 1:
        raise SQLGuardError(f"Expected 1 SQL statement, got {len(statements)}.")

    # 3. Must start with SELECT or WITH (CTE)
    first_word = sql.split()[0].upper()
    if first_word not in ("SELECT", "WITH"):
        raise SQLGuardError(f"Only SELECT queries are allowed (got {first_word!r}).")

    # 4. Reject forbidden DML/DDL keywords anywhere in the statement
    match = _FORBIDDEN.search(sql)
    if match:
        raise SQLGuardError(f"Forbidden keyword in query: {match.group().upper()}.")

    # 5. Collect CTE aliases — they are valid "tables" without being in the schema
    cte_aliases = {m.group(1).lower() for m in _CTE_RE.finditer(sql)}

    # 6. Every FROM/JOIN target must exist in schema or be a CTE alias
    known = {t["name"].lower() for t in schema.get("tables", [])}
    referenced = {
        m.group(1).lower()
        for pattern in (_TABLE_AFTER_FROM, _TABLE_AFTER_JOIN)
        for m in pattern.finditer(sql)
    }
    unknown = referenced - known - cte_aliases
    if unknown:
        raise SQLGuardError(f"Unknown table(s) referenced: {', '.join(sorted(unknown))}.")

    return sql
