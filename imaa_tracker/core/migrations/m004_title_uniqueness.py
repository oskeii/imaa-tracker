"""Migration 004: normalize title names, merge duplicates, enforce uniqueness."""
import re
import unicodedata
import sqlite3

_WHITESPACE = re.compile(r"\s+")


def _normalize(text):
    """
    Snapshot of normalize_title() as of schema version 4.
    """
    if text is None:
        return None
    text = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", text).strip()


# Fields allowed to be merged from duplicate title
_MERGEABLE = (
    "genre", "tags", "cover_image",
    "youtube_channel_id", "youtube_url", "notes"
)
_MERGEABLE_PAIR = ("api", "api_id")


def upgrade(conn: sqlite3.Connection):
    # --- 1. Normalize every existing title
    for title_id, name in conn.execute("SELECT id, name FROM titles").fetchall():
        cleaned = _normalize(name)
        if cleaned != name:
            conn.execute("UPDATE titles SET name = ? WHERE id = ?", (cleaned, title_id))

    # --- 2. Normalize title_text on UNLINKED sessions (clean in-place)
    for sid, text in conn.execute(
            "SELECT id, title_text FROM immersion_sessions WHERE title_id IS NULL"
    ).fetchall():
        cleaned = _normalize(text)
        if cleaned != text:
            conn.execute(
                "UPDATE immersion_sessions SET title_text = ? WHERE id = ?",
                (cleaned, sid)
            )

    # --- 3. Merge duplicate title groups (possibly created during normalization)
    # SQLite gives bare columns the values from the MIN(id) row
    # A group may hold ASCII case variants, so the group key alone is ambiguous
    groups = conn.execute("""
        SELECT MIN(id), name, medium_type
        FROM titles
        GROUP BY name COLLATE NOCASE, medium_type
        HAVING COUNT(*) > 1
    """).fetchall()

    for keep_id, keep_name, medium_type in groups:
        dupes = [r[0] for r in conn.execute(
            "SELECT id FROM titles "
            "WHERE name = ? COLLATE NOCASE AND medium_type = ? AND id != ? "
            "ORDER BY id",
            (keep_name, medium_type, keep_id)
        )]
        qmarks = ",".join("?" for _ in dupes)

        # rescue any metadata the "original" is missing
        columns = (*_MERGEABLE, *_MERGEABLE_PAIR)
        col_list = ", ".join(columns)

        keep_row = conn.execute(
            f"SELECT {col_list} FROM titles WHERE id = ?", (keep_id,)
        ).fetchone()
        original = dict(zip(columns, keep_row))
        merged = dict(original)

        for dupe_row in conn.execute(
                f"SELECT {col_list} FROM titles WHERE id IN ({qmarks})", dupes
        ).fetchall():
            dupe = dict(zip(columns, dupe_row))
            for col in _MERGEABLE:
                if merged[col] is None and dupe[col] is not None:
                    merged[col] = dupe[col]

            if merged["api"] is None and dupe["api"] is not None:
                merged["api"], merged["api_id"] = dupe["api"], dupe["api_id"]

            if merged != original:
                sets = ", ".join(f"{c} = ?" for c in columns)
                conn.execute(
                    f"UPDATE titles SET {sets} WHERE id = ?",
                    (*(merged[c] for c in columns), keep_id)
                )

        # Repoint sessions, then drop dupes
        conn.execute(
            f"UPDATE immersion_sessions SET title_id = ? WHERE title_id IN ({qmarks})",
            (keep_id, *dupes)
        )
        conn.execute(f"DELETE FROM titles WHERE id IN ({qmarks})", dupes)

    # --- 4. Linked sessions adopt the canonical name as title_text
    for title_id, name in conn.execute("SELECT id, name FROM titles").fetchall():
        conn.execute(
            "UPDATE immersion_sessions SET title_text = ? WHERE title_id = ?",
            (name, title_id)
        )

    # --- 5. Enforce uniqueness on titles by name and medium
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_titles_name_medium
        ON titles(name COLLATE NOCASE, medium_type)
    """)
