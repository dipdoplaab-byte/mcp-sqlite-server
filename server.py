import argparse
import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-sqlite")

ROOT = Path.home() / ".mcp-sqlite"
CONNECTED: dict[str, sqlite3.Connection] = {}
PATHS: dict[str, Path] = {}


def _resolve(name: str) -> Path:
    if name not in PATHS:
        raise ValueError(f"unknown database '{name}' — call open_database first")
    return PATHS[name]


def _conn(name: str) -> sqlite3.Connection:
    if name not in CONNECTED:
        path = _resolve(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        CONNECTED[name] = conn
    return CONNECTED[name]


def _first_word(sql: str) -> str:
    stripped = sql.lstrip()
    if not stripped:
        return ""
    return stripped.split(None, 1)[0].upper()


def _rows_to_json(rows: list[sqlite3.Row]) -> str:
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool()
def open_database(name: str, path: str = "") -> str:
    """Register (or create) a SQLite database so other tools can use it."""
    if not name.strip():
        raise ValueError("name is required")
    target = Path(path).expanduser() if path else ROOT / f"{name}.sqlite"
    PATHS[name] = target
    CONNECTED.pop(name, None)
    _conn(name)
    return f"database '{name}' ready at {target}"


@mcp.tool()
def list_databases() -> str:
    """List all registered databases."""
    return json.dumps(
        [{"name": n, "path": str(p)} for n, p in PATHS.items()],
        ensure_ascii=False,
    )


@mcp.tool()
def query(db: str, sql: str) -> str:
    """Run a read-only SELECT against a registered database and return rows as JSON."""
    if _first_word(sql) not in ("SELECT", "WITH", "EXPLAIN", "PRAGMA", "VALUES"):
        raise ValueError("query() only accepts read statements (SELECT/WITH/PRAGMA)")
    cur = _conn(db).execute(sql)
    return _rows_to_json(cur.fetchall())


@mcp.tool()
def execute(db: str, sql: str, params: str = "[]") -> str:
    """Run a write statement (INSERT/UPDATE/DELETE/DDL) against a registered database."""
    if _first_word(sql) in ("SELECT", "WITH", "VALUES"):
        raise ValueError("execute() only accepts write/DDL statements")
    bound = json.loads(params or "[]")
    conn = _conn(db)
    cur = conn.execute(sql, tuple(bound))
    conn.commit()
    return json.dumps(
        {
            "changes": cur.rowcount,
            "last_insert_rowid": cur.lastrowid,
            "ok": True,
        }
    )


@mcp.tool()
def list_tables(db: str) -> str:
    """List tables and views in a registered database."""
    cur = _conn(db).execute(
        "SELECT name, type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return _rows_to_json(cur.fetchall())


@mcp.tool()
def table_schema(db: str, table: str) -> str:
    """Return columns and indexes for a table in a registered database."""
    conn = _conn(db)
    cols = conn.execute(f"PRAGMA table_info({json.dumps(table)})").fetchall()
    idxs = conn.execute(f"PRAGMA index_list({json.dumps(table)})").fetchall()
    return json.dumps(
        {"table": table, "columns": [dict(c) for c in cols], "indexes": [dict(i) for i in idxs]},
        ensure_ascii=False,
        default=str,
    )


def main() -> None:
    global ROOT
    parser = argparse.ArgumentParser(description="MCP SQLite server")
    parser.add_argument("--db", action="append", metavar="NAME=PATH", help="pre-register databases")
    parser.add_argument("--root", default=str(ROOT), help="default directory for new databases")
    args = parser.parse_args()

    ROOT = Path(args.root).expanduser()
    ROOT.mkdir(parents=True, exist_ok=True)

    for item in args.db or []:
        name, _, path = item.partition("=")
        PATHS[name.strip()] = Path(path).expanduser()

    mcp.run()


if __name__ == "__main__":
    main()