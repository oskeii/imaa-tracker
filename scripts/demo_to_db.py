"""
Migrate demo data from demo.json into the SQLite database.

Usage:
    python -m demo_to_db [path_to_demo.json]

The demo.json uses `days_ago` integer offsets instead of absolute dates,
so re-running this script always produces a database with current activity.

By default, this drops and recreates all data in the database. Use --append
to add demo data alongside existing data (not recommended unless your DB
is already empty).
"""

import sys
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta

from db import get_connection, DB_NAME
from migrations import open_database


def days_ago_to_iso(days: int, reference: date = None) -> str:
    """Convert a `days_ago` integer offset to an ISO date string."""
    if reference is None:
        reference = date.today()
    return (reference - timedelta(days=days)).isoformat()


def clear_demo_data(conn: sqlite3.Connection):
    """Drop all data from every table (preserves schema)."""
    tables = [
        "goal_log", "milestones", "goals",
        "exam_scores", "study_sessions",
        "immersion_sessions", "titles", "resources",
    ]
    cur = conn.cursor()
    for t in tables:
        cur.execute(f"DELETE FROM {t}")
    # Reset autoincrement counters (sqlite_sequence may not exist on a fresh DB)
    try:
        cur.execute("DELETE FROM sqlite_sequence")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    print(f"  Cleared {len(tables)} tables.")


def import_titles(data: list[dict], conn: sqlite3.Connection) -> dict[tuple, int]:
    """
    Insert titles and return a lookup map: (name, medium_type) → title_id.
    Some sessions reference titles by name alone, others by (name, medium)
    when the same name exists across multiple media.
    """
    cur = conn.cursor()
    lookup: dict[tuple, int] = {}
    for t in data:
        cur.execute("""
            INSERT INTO titles
            (name, medium_type, genre, tags, cover_image, api, api_id,
             youtube_channel_id, youtube_url, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["name"], t["medium_type"],
            t.get("genre"), t.get("tags"), t.get("cover_image"),
            t.get("api"), t.get("api_id"),
            t.get("youtube_channel_id"), t.get("youtube_url"),
            t.get("notes"),
        ))
        title_id = cur.lastrowid
        lookup[(t["name"], t["medium_type"])] = title_id
    conn.commit()
    return lookup


def import_resources(data: list[dict], conn: sqlite3.Connection) -> dict[str, int]:
    """Insert resources and return a lookup map: name → resource_id."""
    cur = conn.cursor()
    lookup: dict[str, int] = {}
    for r in data:
        cur.execute("""
            INSERT INTO resources
            (name, resource_type, level, cover_image, url, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            r["name"], r["resource_type"],
            r.get("level"), r.get("cover_image"),
            r.get("url"), r.get("notes"),
        ))
        lookup[r["name"]] = cur.lastrowid
    conn.commit()
    return lookup


def import_immersion_sessions(
    data: list[dict], conn: sqlite3.Connection,
    title_lookup: dict[tuple, int],
):
    """Insert immersion sessions, resolving title_id from the title name."""
    cur = conn.cursor()
    for s in data:
        date_str = days_ago_to_iso(s["days_ago"])
        title_text = s.get("title")
        medium_type = s["medium_type"]

        # Resolve title_id
        title_id = title_lookup.get((title_text, medium_type))

        # URLs as JSON
        urls = s.get("urls")
        urls_json = json.dumps(urls) if urls else None

        cur.execute("""
            INSERT INTO immersion_sessions
            (date, title_id, title_text, medium_type, activity_type,
             duration_minutes, character_count, page_count, episode_count,
             reading_direction, volume, chapter, episode_name,
             urls_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str, title_id, title_text, medium_type, s["activity_type"],
            s.get("duration_minutes"), s.get("character_count"),
            s.get("page_count"), s.get("episode_count"),
            s.get("reading_direction"), s.get("volume"),
            s.get("chapter"), s.get("episode_name"),
            urls_json, s.get("notes"),
        ))
    conn.commit()


def import_study_sessions(
    data: list[dict], conn: sqlite3.Connection,
    resource_lookup: dict[str, int],
):
    """Insert study sessions, resolving resource_id from resource name."""
    cur = conn.cursor()
    for s in data:
        date_str = days_ago_to_iso(s["days_ago"])
        resource_name = s.get("resource_name")
        resource_id = resource_lookup.get(resource_name) if resource_name else None

        cur.execute("""
            INSERT INTO study_sessions
            (date, study_type, resource_id, resource_text, duration_minutes,
             anki_deck, anki_reviews, anki_new_cards, topic_area, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str, s["study_type"], resource_id, resource_name,
            s.get("duration_minutes"),
            s.get("anki_deck"), s.get("anki_reviews"), s.get("anki_new_cards"),
            s.get("topic_area"), s.get("notes"),
        ))
    conn.commit()


def import_exam_scores(
    data: list[dict], conn: sqlite3.Connection,
    resource_lookup: dict[str, int],
):
    cur = conn.cursor()
    for e in data:
        date_str = days_ago_to_iso(e["days_ago"])
        resource_id = resource_lookup.get(e.get("resource_name"))
        sections_json = json.dumps(e.get("sections", {}), ensure_ascii=False)

        cur.execute("""
            INSERT INTO exam_scores
            (date, level, exam_type, resource_id, source_text,
             sections_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str, e["level"], e["exam_type"], resource_id,
            e.get("source_text"), sections_json, e.get("notes"),
        ))
    conn.commit()


def import_goals(data: list[dict], conn: sqlite3.Connection) -> dict[str, int]:
    """Insert goals. Returns name → goal_id lookup for milestone linking."""
    cur = conn.cursor()
    lookup: dict[str, int] = {}
    for g in data:
        created_at = days_ago_to_iso(g.get("created_days_ago", 0))
        achieved_at = (
            days_ago_to_iso(g["achieved_days_ago"])
            if g.get("achieved_days_ago") is not None else None
        )
        cur.execute("""
            INSERT INTO goals
            (name, goal_type, metric, target_value, period,
             medium_type, activity_type, health_window_days,
             is_active, achieved_at, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g["name"], g["goal_type"], g["metric"], g["target_value"],
            g.get("period"), g.get("medium_type"), g.get("activity_type"),
            g.get("health_window_days", 60),
            g.get("is_active", 1), achieved_at,
            g.get("notes"), created_at,
        ))
        lookup[g["name"]] = cur.lastrowid
    conn.commit()
    return lookup


def import_milestones(
    data: list[dict], conn: sqlite3.Connection,
    goal_lookup: dict[str, int],
):
    cur = conn.cursor()
    for m in data:
        date_str = days_ago_to_iso(m["days_ago"])
        # Optional goal link (only goal-triggered milestones have this)
        goal_id = goal_lookup.get(m.get("goal_name"))
        filter_json = json.dumps(m["filter"]) if m.get("filter") is not None else None

        cur.execute("""
            INSERT INTO milestones
            (title, date, goal_id, metric, metric_value, filter_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            m["title"], date_str, goal_id,
            m.get("metric"), m.get("metric_value"),
            filter_json, m.get("notes"),
        ))
    conn.commit()


def backfill_goal_log(conn: sqlite3.Connection):
    """
    Backfill goal_log entries for recurring goals based on actual session data.
    For each active recurring goal, iterate through every period in its history
    and record whether it was achieved.

    This makes the habit health charts work — without this, recurring goals
    have no history to compute streaks from.
    """
    cur = conn.cursor()

    # Get all recurring goals
    goals = cur.execute("""
        SELECT * FROM goals WHERE goal_type = 'recurring'
    """).fetchall()

    today = date.today()

    for goal in goals:
        # Determine the range to backfill: from goal.created_at to today
        try:
            created = date.fromisoformat(goal["created_at"][:10])
        except (TypeError, ValueError):
            created = today - timedelta(days=goal["health_window_days"])

        period = goal["period"]
        if period == "daily":
            step = timedelta(days=1)
            period_starts = []
            d = created
            while d <= today:
                period_starts.append(d)
                d += step
        elif period == "weekly":
            # Find first Monday on or after created
            d = created
            d += timedelta(days=(7 - d.weekday()) % 7) if d.weekday() != 0 else timedelta(0)
            period_starts = []
            while d <= today:
                period_starts.append(d)
                d += timedelta(days=7)
        elif period == "monthly":
            d = created.replace(day=1)
            period_starts = []
            while d <= today:
                period_starts.append(d)
                # advance to next month
                if d.month == 12:
                    d = d.replace(year=d.year + 1, month=1)
                else:
                    d = d.replace(month=d.month + 1)
        else:
            continue

        # For each period, sum the relevant metric from sessions
        metric = goal["metric"]
        if metric == "session_count":
            agg = "COUNT(*)"
        else:
            agg = f"COALESCE(SUM({metric}), 0)"

        for ps in period_starts:
            # Compute period end
            pe = None
            if period == "daily":
                pe = ps
            elif period == "weekly":
                pe = ps + timedelta(days=6)
            elif period == "monthly":
                if ps.month == 12:
                    pe = ps.replace(year=ps.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    pe = ps.replace(month=ps.month + 1, day=1) - timedelta(days=1)

            sql = f"""SELECT {agg} FROM immersion_sessions
                     WHERE date >= ? AND date <= ?"""
            params = [ps.isoformat(), pe.isoformat()]
            if goal["medium_type"]:
                sql += " AND medium_type = ?"
                params.append(goal["medium_type"])
            if goal["activity_type"]:
                sql += " AND activity_type = ?"
                params.append(goal["activity_type"])

            actual = cur.execute(sql, params).fetchone()[0]
            achieved = 1 if actual >= goal["target_value"] else 0

            cur.execute("""
                INSERT OR REPLACE INTO goal_log
                (goal_id, period_date, actual_value, target_value, is_achieved)
                VALUES (?, ?, ?, ?, ?)
            """, (goal["id"], ps.isoformat(), actual, goal["target_value"], achieved))

    conn.commit()


def print_summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\n--- Demo data summary ---")

    for tbl, label in [
        ("titles", "Titles"),
        ("immersion_sessions", "Immersion sessions"),
        ("resources", "Resources"),
        ("study_sessions", "Study sessions"),
        ("exam_scores", "Exam scores"),
        ("goals", "Goals"),
        ("goal_log", "Goal log entries"),
        ("milestones", "Milestones"),
    ]:
        count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {label:20s} {count}")

    cur.execute("SELECT MIN(date), MAX(date) FROM immersion_sessions")
    row = cur.fetchone()
    print(f"\n  Date range:          {row[0]} → {row[1]}")

    cur.execute("SELECT SUM(duration_minutes) FROM immersion_sessions")
    total = cur.fetchone()[0] or 0
    print(f"  Total immersion:     {total:,} min ({total/60:.1f} hours)")

    cur.execute("""SELECT medium_type, COUNT(*) as c, SUM(duration_minutes) as m
                   FROM immersion_sessions GROUP BY medium_type ORDER BY m DESC""")
    print("\n  By medium:")
    for row in cur.fetchall():
        print(f"    {row[0]:15s}  {row[1]:4d} sessions, {row[2] or 0:,} min")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", nargs="?", default="demo.json",
                        help="Path to demo.json (default: ./demo.json)")
    parser.add_argument("--append", action="store_true",
                        help="Add to existing data instead of clearing first")
    parser.add_argument("--db", default=None,
                        help=f"Database path (default: {DB_NAME})")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        sys.exit(1)

    db_path = args.db or DB_NAME

    print(f"Opening database at {db_path}...")
    open_database(db_path)   # creates a fresh schema or migrates an existing one (if outdated)
    conn = get_connection(db_path)

    if not args.append:
        print("Clearing existing data...")
        clear_demo_data(conn)

    print(f"Loading {json_path}...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    print("Importing titles...")
    title_lookup = import_titles(data["titles"], conn)
    print(f"  {len(title_lookup)} titles inserted.")

    print("Importing resources...")
    resource_lookup = import_resources(data["resources"], conn)
    print(f"  {len(resource_lookup)} resources inserted.")

    print("Importing immersion sessions...")
    import_immersion_sessions(data["immersion_sessions"], conn, title_lookup)
    print(f"  {len(data['immersion_sessions'])} sessions inserted.")

    print("Importing study sessions...")
    import_study_sessions(data["study_sessions"], conn, resource_lookup)
    print(f"  {len(data['study_sessions'])} sessions inserted.")

    print("Importing exam scores...")
    import_exam_scores(data["exam_scores"], conn, resource_lookup)
    print(f"  {len(data['exam_scores'])} exam scores inserted.")

    print("Importing goals...")
    goal_lookup = import_goals(data["goals"], conn)
    print(f"  {len(goal_lookup)} goals inserted.")

    print("Importing milestones...")
    import_milestones(data["milestones"], conn, goal_lookup)
    print(f"  {len(data['milestones'])} milestones inserted.")

    print("Backfilling goal_log entries from session data...")
    backfill_goal_log(conn)

    print_summary(conn)
    conn.close()
    print(f"\nDone. Database: {db_path}")


if __name__ == "__main__":
    main()
