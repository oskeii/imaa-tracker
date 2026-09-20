"""Compare a fully-migrated database against a fresh one. Diagnostic only."""
import re
import sqlite3
import tempfile
from pathlib import Path

from imaa_tracker.core import db, migrations

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "schema_v0.sql"
_COMMENT = re.compile(r"--[^\n]*")
_CHECK_KW = re.compile(r"\bCHECK\b\s*\(", re.IGNORECASE)


def _check_constraints(sql: str) -> list[str]:
    """
    Pull every CHECK (...) clause out of a CREATE statement, normalized and sorted.
    PRAGMA table_info doesn't report CHECKs, so this is needed to make sure enum constraints are the same.
    """
    if not sql:
        return []
    sql = _COMMENT.sub("", sql)

    out = []
    for m in _CHECK_KW.finditer(sql):
        i = m.end() - 1  # position of the opening paren
        depth, j, in_str = 0, i, False
        while j < len(sql):
            ch = sql[j]
            if in_str:
                if ch == "'":
                    if j + 1 < len(sql) and sql[j + 1] == "'":
                        j += 1  # escaped quote inside a literal
                    else:
                        in_str = False
            elif ch == "'":
                in_str = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(" ".join(sql[i:j + 1].split()))  # collapse whitespace
    return sorted(out)


def _build_pair(tmp: Path) -> tuple[str, str]:
    """Return (migrated_path, fresh_path)."""
    migrated = str(tmp / "migrated.db")
    conn = sqlite3.connect(migrated)
    conn.executescript(FIXTURE.read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    conn.close()
    migrations.migrate(migrated, backup=False)

    fresh = str(tmp / "fresh.db")
    db.init_db(fresh)
    return migrated, fresh


def _dump(path: str) -> dict:
    """{table: {"columns": {...}, "indexes": {...}, "sql": ...}} for every user table."""
    out = {}

    with db.connect(path) as conn:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for t in tables:
            cols = {
                r[1]: {"type": r[2], "notnull": r[3], "default": r[4], "pk": r[5]}
                for r in conn.execute(f"PRAGMA table_info({t})")
            }
            idx = {
                r[1]: {"unique": r[2], "origin": r[3]}
                for r in conn.execute(f"PRAGMA index_list({t})")
            }
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
            ).fetchone()[0]
            out[t] = {"columns": cols, "indexes": idx, "sql": sql}
    return out


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        migrated, fresh = _build_pair(Path(d))
        a, b = _dump(migrated), _dump(fresh)

        for t in sorted(set(a) | set(b)):
            if t not in a:
                print(f"[{t}] MISSING from migrated")
                continue
            if t not in b:
                print(f"[{t}] MISSING from fresh")
                continue

            for col in sorted(set(a[t]["columns"]) | set(b[t]["columns"])):
                ca, cb = a[t]["columns"].get(col), b[t]["columns"].get(col)
                if ca != cb:
                    print(f"[{t}.{col}] migrated={ca} fresh={cb}")

            for name in sorted(set(a[t]["indexes"]) | set(b[t]["indexes"])):
                ia, ib = a[t]["indexes"].get(name), b[t]["indexes"].get(name)
                if ia != ib:
                    print(f"[{t}::{name}] migrated={ia} fresh={ib}")

            ka = _check_constraints(a[t]["sql"])
            kb = _check_constraints(b[t]["sql"])
            if ka != kb:
                print(f"[{t}] CHECK constraints differ:")
                for c in sorted(set(ka) - set(kb)):
                    print(f"    only in migrated: {c}")
                for c in sorted(set(kb) - set(ka)):
                    print(f"    only in fresh   : {c}")


if __name__ == "__main__":
    main()
