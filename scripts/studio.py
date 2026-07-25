"""A local database browser for data/carr.sqlite. Nothing is hardcoded.

    uv run python scripts/studio.py

Opens http://127.0.0.1:8787 with a table browser: every table, every column,
sorting, search, pagination, a read-only SQL console, and row editing and
deletion. It reads the schema out of the database at request time, so it
works on whatever the file happens to contain -- add a table tomorrow and it
appears without touching this file.

Why a server and not a static page: a file:// page cannot write to SQLite.
Deleting or editing a row needs a process holding the database open, so this
is one. It binds to 127.0.0.1 only and uses nothing outside the standard
library.

Two safety properties, because data/carr.sqlite is the scientific asset and
`generations` rows cost real money:

  * Every mutating request snapshots the whole database to data/backups/
    first, via carr.db.backup(). Nothing done here is unrecoverable.
  * The SQL console runs on a read-only connection and refuses anything that
    is not a single SELECT/WITH/EXPLAIN/PRAGMA.

Run with --read-only to disable editing and deletion entirely.
"""

import argparse
import json
import re
import sqlite3
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db  # noqa: E402

PAGE = Path(__file__).with_name("studio.html")

# Only these may run in the SQL console, and only one statement at a time.
READ_ONLY_SQL = re.compile(r"^\s*(select|with|explain|pragma)\b", re.IGNORECASE)

# Tables whose rows cost money. The UI warns harder before touching these.
COSTLY_TABLES = {"generations"}

_state = {"db": db.DEFAULT_DB, "read_only": False, "backed_up": False}
_lock = threading.Lock()


# ----------------------------------------------------------------- helpers


def open_db(read_only: bool = False) -> sqlite3.Connection:
    path = Path(_state["db"])
    if read_only:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_backup() -> str | None:
    """One snapshot per server run, taken before the first write."""
    with _lock:
        if _state["backed_up"]:
            return None
        dest = db.backup(_state["db"])
        _state["backed_up"] = True
        return str(dest) if dest else None


def jsonable(value):
    """SQLite gives back bytes for BLOBs; JSON cannot carry them."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<BLOB {len(bytes(value))} bytes>"
    return value


def tables(conn) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


def columns(conn, table: str) -> list[dict]:
    return [
        {"name": r["name"], "type": r["type"] or "",
         "pk": bool(r["pk"]), "notnull": bool(r["notnull"])}
        for r in conn.execute(f'PRAGMA table_info("{table}")')
    ]


def key_column(cols: list[dict]) -> str:
    """The column to address a row by. Falls back to SQLite's implicit rowid."""
    pks = [c["name"] for c in cols if c["pk"]]
    return pks[0] if len(pks) == 1 else "rowid"


def dependents(conn, table: str) -> list[tuple[str, str, str]]:
    """(child_table, child_column, parent_column) for every FK pointing here."""
    found = []
    for other in tables(conn):
        for fk in conn.execute(f'PRAGMA foreign_key_list("{other}")'):
            if fk["table"] == table:
                found.append((other, fk["from"], fk["to"]))
    return found


def check_table(conn, table: str) -> None:
    """Guard against SQL injection through the table name."""
    if table not in tables(conn):
        raise ValueError(f"no such table: {table}")


# -------------------------------------------------------------- api routes


def api_schema() -> dict:
    conn = open_db(read_only=True)
    out = []
    for name in tables(conn):
        cols = columns(conn, name)
        n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        out.append({
            "name": name,
            "rows": n,
            "columns": cols,
            "key": key_column(cols),
            "costly": name in COSTLY_TABLES,
            "dependents": [d[0] for d in dependents(conn, name)],
        })
    conn.close()
    path = Path(_state["db"])
    return {
        "tables": out,
        "db_path": str(path),
        "db_bytes": path.stat().st_size if path.exists() else 0,
        "read_only": _state["read_only"],
    }


def api_rows(q: dict) -> dict:
    table = q.get("table", [""])[0]
    limit = min(int(q.get("limit", ["50"])[0]), 500)
    offset = max(int(q.get("offset", ["0"])[0]), 0)
    sort = q.get("sort", [""])[0]
    direction = "DESC" if q.get("dir", ["asc"])[0].lower() == "desc" else "ASC"
    search = q.get("q", [""])[0].strip()

    conn = open_db(read_only=True)
    check_table(conn, table)
    cols = columns(conn, table)
    names = [c["name"] for c in cols]
    key = key_column(cols)

    select = ", ".join(f'"{n}"' for n in names)
    if key == "rowid":
        select = f"rowid AS rowid, {select}"

    where, params = "", []
    if search:
        # Search every column as text. Slow on big tables, but this is a
        # 3,000-row research database, not a production system.
        clauses = [f'CAST("{n}" AS TEXT) LIKE ?' for n in names]
        where = " WHERE " + " OR ".join(clauses)
        params = [f"%{search}%"] * len(names)

    order = ""
    if sort in names:
        order = f' ORDER BY "{sort}" {direction}'

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{table}"{where}', params
    ).fetchone()[0]
    rows = conn.execute(
        f'SELECT {select} FROM "{table}"{where}{order} LIMIT ? OFFSET ?',
        [*params, limit, offset],
    ).fetchall()
    conn.close()

    return {
        "table": table, "columns": cols, "key": key, "total": total,
        "limit": limit, "offset": offset,
        "rows": [{k: jsonable(r[k]) for k in r.keys()} for r in rows],
    }


def api_query(body: dict) -> dict:
    sql = (body.get("sql") or "").strip().rstrip(";")
    if not sql:
        raise ValueError("empty query")
    if not READ_ONLY_SQL.match(sql):
        raise ValueError("only SELECT, WITH, EXPLAIN and PRAGMA are allowed here")
    if ";" in sql:
        raise ValueError("one statement at a time")

    # A read-only connection, so even a clever SELECT cannot write.
    conn = open_db(read_only=True)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(1000)
        names = [d[0] for d in cur.description] if cur.description else []
        return {
            "columns": names,
            "rows": [[jsonable(v) for v in r] for r in rows],
            "truncated": len(rows) == 1000,
        }
    finally:
        conn.close()


def api_delete(body: dict) -> dict:
    if _state["read_only"]:
        raise PermissionError("server started with --read-only")

    table = body["table"]
    keys = body.get("keys") or []
    cascade = bool(body.get("cascade"))
    if not keys:
        raise ValueError("nothing selected")

    backup_path = ensure_backup()
    conn = open_db()
    check_table(conn, table)
    key = key_column(columns(conn, table))
    marks = ",".join("?" * len(keys))
    removed_children: dict[str, int] = {}

    try:
        if cascade:
            for child, child_col, parent_col in dependents(conn, table):
                cur = conn.execute(
                    f'DELETE FROM "{child}" WHERE "{child_col}" IN '
                    f'(SELECT "{parent_col}" FROM "{table}" WHERE "{key}" IN ({marks}))',
                    keys,
                )
                if cur.rowcount > 0:
                    removed_children[child] = cur.rowcount

        cur = conn.execute(f'DELETE FROM "{table}" WHERE "{key}" IN ({marks})', keys)
        conn.commit()
        deleted = cur.rowcount
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        conn.close()
        # Almost always a foreign key: another table still points at this row.
        blockers = [d[0] for d in dependents(open_db(read_only=True), table)]
        raise ValueError(
            f"{exc}. Rows in {', '.join(blockers) or 'another table'} still "
            f"reference this. Re-run with cascade to remove those too."
        ) from exc
    finally:
        if conn:
            conn.close()

    return {"deleted": deleted, "children": removed_children, "backup": backup_path}


def api_update(body: dict) -> dict:
    if _state["read_only"]:
        raise PermissionError("server started with --read-only")

    table, row_key, column = body["table"], body["key"], body["column"]
    value = body.get("value")

    backup_path = ensure_backup()
    conn = open_db()
    check_table(conn, table)
    cols = columns(conn, table)
    if column not in [c["name"] for c in cols]:
        conn.close()
        raise ValueError(f"no such column: {column}")
    key = key_column(cols)

    if value == "":
        value = None
    cur = conn.execute(
        f'UPDATE "{table}" SET "{column}" = ? WHERE "{key}" = ?', (value, row_key)
    )
    conn.commit()
    conn.close()
    return {"updated": cur.rowcount, "backup": backup_path}


# ------------------------------------------------------------------ server


class Handler(BaseHTTPRequestHandler):
    server_version = "carr-studio"

    def log_message(self, fmt, *args):  # quieter than the default access log
        pass

    def _send(self, payload, status=200, content_type="application/json"):
        body = (payload if isinstance(payload, bytes)
                else json.dumps(payload).encode())
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _guard(self, fn, *args):
        try:
            self._send(fn(*args))
        except PermissionError as exc:
            self._send({"error": str(exc)}, 403)
        except (ValueError, KeyError) as exc:
            self._send({"error": str(exc)}, 400)
        except Exception as exc:  # surfaced in the UI rather than swallowed
            self._send({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(PAGE.read_bytes(), content_type="text/html; charset=utf-8")
        if url.path == "/api/schema":
            return self._guard(api_schema)
        if url.path == "/api/rows":
            return self._guard(api_rows, parse_qs(url.query))
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send({"error": "bad JSON"}, 400)

        routes = {"/api/query": api_query, "/api/delete": api_delete,
                  "/api/update": api_update}
        if url.path in routes:
            return self._guard(routes[url.path], body)
        self._send({"error": "not found"}, 404)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1",
                    help="loopback only by default; this server has no auth")
    ap.add_argument("--read-only", action="store_true",
                    help="disable editing and deletion")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    path = Path(args.db) if args.db else db.DEFAULT_DB
    if not path.exists():
        sys.exit(f"no database at {path}\n"
                 f"run:  uv run python scripts/init_db.py")

    _state["db"] = path
    _state["read_only"] = args.read_only

    url = f"http://{args.host}:{args.port}"
    conn = open_db(read_only=True)
    n_tables = len(tables(conn))
    conn.close()

    print(f"  {path}  ({path.stat().st_size / 1024:.0f} KB, {n_tables} tables)")
    print(f"  {url}" + ("   [read-only]" if args.read_only else ""))
    if not args.read_only:
        print("  writes enabled -- the database is snapshotted to data/backups/"
              " before the first one")
    print("  ctrl-c to stop\n")

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
