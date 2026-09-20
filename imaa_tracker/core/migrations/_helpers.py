"""
Shared migration mechanics.

FROZEN. APPEND ONLY.
Every applied migration depends on these behaving exactly as they did when it was written.
Fix bugs by adding a new function, never by editing an existing one.

Mechanism only — no enum values, no schema knowledge. Those stay snapshotted inside each migration.
"""
import sqlite3


def column_exists(conn, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def sql_tuple(values) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def assert_data_is_clean(conn: sqlite3.Connection, table: str, column: str, allowed) -> None:
    """Check existing data meets constraints before building new table."""
    placeholders = ", ".join("?" for _ in allowed)
    bad_values = conn.execute(
        f"SELECT DISTINCT {column} FROM {table} "
        f"WHERE {column} IS NOT NULL AND {column} NOT IN ({placeholders})",
        tuple(allowed)
    ).fetchall()
    if bad_values:
        values = [row[0] for row in bad_values]
        raise RuntimeError(
            f"Cannot add CHECK constraint: {table}.{column} contains values not in the allowed list: {values}. "
            f"Fix these rows first. \n"
            f"Allowed values: {list(allowed)}"
        )


def rebuild_table(
        conn: sqlite3.Connection,
        table: str,
        create_new_sql: str,
        columns: list[str],
        index_sqls: list[str]) -> None:
    """
    table: original table name
    create_new_sql: sql script to create the new table. new table name should be appended with '_new'
    Caller must:
        - Call inside a transaction
        - PRAGMA foreign_keys=OFF before transaction begins
    """
    cols = ", ".join(columns)

    conn.execute(create_new_sql)  # new table with temporary name
    conn.execute(f"INSERT INTO {table}_new ({cols}) SELECT {cols} from {table}")  # copy over table contents
    conn.execute(f"DROP TABLE {table}")  # drop original
    conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")  # rename new table to replace

    # Recreate indexes
    for sql in index_sqls:
        conn.execute(sql)

