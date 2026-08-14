from datetime import date, timedelta
import json

from imaa_tracker.core.constants import ENUMS
from imaa_tracker.core.db import connect


# SERVICES:
#   _sort_goals
#   compute_goal_progress, compute_habit_health, get_habit_dot_data,
#   get_active_goals_with_progress, get_log_strip_goals, check_and_log_goals


# REPO:
#  add_goal, get_goals, update_goal, toggle_pinned, toggle_show_on_log
#  add_milestone, get_milestones
_GOAL_UPDATE_COLS = frozenset({
    "name", "target_value", "period", "medium_type", "activity_type",
    "health_window_days", "is_active", "achieved_at", "notes",
    "pinned", "show_on_log",
})

def add_goal(
    name: str, goal_type: str, metric: str, target_value: int,
    period: str = None,
    medium_type: str = None, activity_type: str = None,
    health_window_days: int = 60,
    notes: str = None
) -> int:
    print("ADD GOAL:", (name, goal_type, metric, target_value, period,
             medium_type, activity_type, health_window_days, notes))
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO goals
            (name, goal_type, metric, target_value, period,
             medium_type, activity_type, health_window_days, notes) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, goal_type, metric, target_value, period,
             medium_type, activity_type, health_window_days, notes),
        )
        return cur.lastrowid

def get_goals(active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM goals"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY goal_type, name"  
    with connect() as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

def get_goal_by_id(goal_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        return dict(row)

def update_goal(goal_id: int, **fields) -> None:
    updates = {k: v for k, v in fields.items() if k in _GOAL_UPDATE_COLS}
    if not updates:
        return
    set_str = ", ".join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [goal_id]
    with connect() as conn:
        conn.execute(f"UPDATE goals SET {set_str} WHERE id = ?", params)

def toggle_pinned(goal_id: int) -> int:
    """Toggle goals.pinned. Returns new value (0 or 1) or 0 if goal not found"""
    with connect() as conn:
        row = conn.execute(
            "SELECT pinned FROM goals WHERE id = ?", (goal_id,)
        ).fetchone()
        if not row:
            return 0
        new_val = 0 if row["pinned"] else 1
        conn.execute("UPDATE goals SET pinned = ? WHERE id = ?", (new_val, goal_id))
        return new_val

def toggle_show_on_log(goal_id: int) -> int:
    """Toggle goals.show_on_log. Returns new value (0 or 1) or 0 if goal not found"""
    with connect() as conn:
        row = conn.execute(
            "SELECT show_on_log FROM goals WHERE id = ?", (goal_id,)
        ).fetchone()
        if not row:
            return 0
        new_val = 0 if row["show_on_log"] else 1
        conn.execute("UPDATE goals SET show_on_log = ? WHERE id = ?", (new_val, goal_id))
        return new_val


def add_milestone(
    title: str, date_str: str,
    goal_id: int = None,
    metric: str = None, metric_value: int = None, filter_json: str = None,
    notes: str = None
) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO milestones 
            (title, date, goal_id, metric, metric_value, filter_json, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, date_str, goal_id, metric, metric_value, filter_json, notes)
        )
        return cur.lastrowid


def get_milestones(limit: int = 50) -> list[dict]:
    """Milestones (with goal name if linked), newest first."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.*, g.name AS goal_name
            FROM milestones m
            LEFT JOIN goals g ON m.goal_id = g.id
            ORDER BY m.date DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
