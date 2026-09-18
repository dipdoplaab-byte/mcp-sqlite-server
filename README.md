# mcp-sqlite-server

An [MCP](https://modelcontextprotocol.io) server that gives any MCP-aware coding agent read/write access to SQLite databases — schema inspection, queries, and migrations over the standard JSON-RPC tools protocol.

Built on the official [`mcp`](https://pypi.org/project/mcp/) Python SDK with the `FastMCP` layer. Single file, stdlib `sqlite3`, no ORM, no magic.

## Tools

| Tool             | Purpose                                                            |
| ---------------- | ------------------------------------------------------------------ |
| `open_database`  | Register (or create) a database by name and optional path          |
| `list_databases` | Show every registered database and its resolved location           |
| `query`          | Read-only `SELECT` / `WITH` / `PRAGMA` — returns rows as JSON      |
| `execute`        | Write / DDL statements — returns change count and last rowid       |
| `list_tables`    | Tables and views in a database                                     |
| `table_schema`   | Columns and indexes of a table                                     |

## Setup

```bash
pip install -r requirements.txt
# or
pip install mcp
```

Run the server:

```bash
python server.py
```

Databases live in `~/.mcp-sqlite/` by default. Override with `--root`, or pre-register with `--db`:

```bash
python server.py --root ./data --db app=./data/app.db --db cache=./data/cache.db
```

## Configuring a client

### Claude Desktop

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "python",
      "args": ["/absolute/path/to/server.py", "--root", "/absolute/path/to/data"]
    }
  }
}
```

### opencode

```json
{
  "mcp": {
    "sqlite": {
      "type": "local",
      "command": ["python", "/absolute/path/to/server.py", "--root", "/absolute/path/to/data"],
      "enabled": true
    }
  }
}
```

## Example

```text
open_database(name="analytics")
query(db="analytics", sql="SELECT name, type FROM sqlite_master ORDER BY name")
execute(db="analytics", sql="CREATE TABLE events (id INTEGER PRIMARY KEY, payload TEXT, ts INTEGER)")
execute(db="analytics", sql="INSERT INTO events (payload, ts) VALUES (?, ?)", params="[\"hello\", 1720000000]")
query(db="analytics", sql="SELECT COUNT(*) AS n FROM events")
```

`query()` refuses anything that isn't read-only; `execute()` refuses `SELECT`/`WITH`/`VALUES`. Statements are parameterized when you pass `params`.

## Notes

- Connections use `WAL` mode and `foreign_keys = ON`.
- The server talks MCP over stdio — no ports, no network surface.