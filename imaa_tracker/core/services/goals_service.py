from datetime import date, timedelta
import json

from imaa_tracker.core.constants import ENUMS
from imaa_tracker.core.db import connect
from imaa_tracker.core.repo import get_goals

_PERIOD_ORDER = {"daily": 0, "weekly": 1, "monthly": 2, None: 3}


def _sort_goals(goals: list[dict]) -> list[dict]:
    """Pinned first, then by period, then oldest first"""
    return sorted(goals, key=lambda g: (
        not bool(g.get("achieved_at") is not None),
        not bool(g.get("pinned", 0)),
        _PERIOD_ORDER.get(g.get("period"), 999),
        g.get("created_at", ""),
    ))


def compute_goal_progress(goal: dict, as_of_date: str = None) -> dict:
    """
    Compute a goal's progress by querying session data live for the current period.

    Returns: current_value, target_value, progress_pct (between 0.0 and 1.0), achieved, period_start, period_end.
    """
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()

    period = goal["period"]
    if goal["goal_type"] == "lifetime":
        period_start, period_end = "1970-01-01", target_date.isoformat()
    elif period == "daily":
        period_start = period_end = target_date.isoformat()
    elif period == "weekly":
        monday = target_date - timedelta(days=target_date.weekday())
        period_start = monday.isoformat()
        period_end = (monday + timedelta(days=6)).isoformat()
    elif period == "monthly":
        first = target_date.replace(day=1)
        nxt = (first.replace(year=first.year + 1, month=1) if first.month == 12
               else first.replace(month=first.month+1))
        period_start = first.isoformat()
        period_end = (nxt - timedelta(days=1)).isoformat()
    else:
        period_start = period_end = target_date.isoformat()

    metric = goal["metric"]
    if metric == "session_count":
        agg = "COUNT(*)"
    elif metric in ENUMS["GOAL_METRICS"]:
        agg = f"COALESCE(SUM({metric}), 0)"
    else:
        raise ValueError(f"Unknown goal metric: {metric!r}")
    
    sql = f"SELECT {agg} FROM immersion_sessions WHERE date >= ? and date <= ?"
    params = [period_start, period_end]
    if goal["medium_type"]:
        sql += " AND medium_type = ?"
        params.append(goal["medium_type"])
    if goal["activity_type"]:
        sql += " AND activity_type = ?"
        params.append(goal["activity_type"])
    
    with connect() as conn:
        current = conn.execute(sql, params).fetchone()[0]
    
    target_val = goal["target_value"]
    return {
        "current_value": int(current),
        "target_value": target_val,
        "progress_pct": current / target_val if target_val > 0 else 0.0,
        "achieved": current >= target_val,
        "period_start": period_start,
        "period_end": period_end,

    }


def compute_habit_health(goal_id: int, window_days: int = None) -> dict:
    """
    Habit health for recurring goal = percent of periods achieved within a window.
    Also includes current and best streaks.
    """
    with connect() as conn:
        if window_days is None:
            g = conn.execute(
                "SELECT health_window_days FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
            window_days = g["health_window_days"] if g else 60
        cutoff = (date.today() - timedelta(days=window_days)).isoformat()
        rows = conn.execute(
            """
            SELECT period_date, is_achieved FROM goal_log
            WHERE goal_id = ? AND period_date >= ?
            ORDER BY period_date ASC
            """,
            (goal_id, cutoff),
        ).fetchall()

    entries = [dict(r) for r in rows]
    total = len(entries)
    achieved = sum(1 for e in entries if e["is_achieved"])

    best_streak = streak = 0
    for e in entries:
        if e["is_achieved"]:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    
    current_streak = 0
    for e in reversed(entries):
        if e["is_achieved"]:
            current_streak += 1
        else:
            break

    return {
        "health_pct": (achieved / total * 100) if total else 0.0,
        "achieved_count": achieved,
        "total_periods": total,
        "current_streak": current_streak,
        "best_streak": best_streak,
    }
    

def get_habit_dot_data(goal_id: int, count: int = 60) -> list[dict]:
    """
    Per-period achievement data for a habit dot strip, 
    oldest first, so it reads left-to-right chronologically.
    Returns each entry as: {"date": ISO, "status": "achieved" | "missed" | "none"}
    """
    pass
    

def get_active_goals_with_progress(recently_achieved_window_days: int = 3) -> list[dict]:
    """
    Active goals, plus lifetime goals achieved within the last N days (shown with "Achieved" badge)
    Each enriched with progress data; recurring goals get habit_health
    """
    cutoff = (date.today() - timedelta(days=recently_achieved_window_days)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM goals
            WHERE is_active = 1
                OR (goal_type = 'lifetime'
                AND achieved_at IS NOT NULL
                AND achieved_at >= ?)
            """,
            (cutoff,)
        ).fetchall()

    goals = [dict(r) for r in rows]
    for g in goals:
        g["progress"] = compute_goal_progress(g)
        if g["goal_type"] == "recurring":
            g["habit_health"] = compute_habit_health(g["id"])
    return _sort_goals(goals)


def check_and_log_goals(as_of_date: str = None) -> list[dict]:
    """    
    Evaluate goals against current session data,
    record each period's outcome to goal_log, and return goal events for UI to notify on.
    If lifetime goal achieved, deactivate and create a milestone.
    Evaluates for lifetime goal regression ONLY when as_of_date is the present day.
    """
    target = date.fromisoformat(as_of_date) if as_of_date else date.today()
    events: list[dict] = []
    goals = get_goals()

    with connect() as conn:
        # --- 1. active goals -> current progress based on session data
        for goal in goals:
            progress = compute_goal_progress(goal, as_of_date=target.isoformat())

            if goal["goal_type"] == "recurring":
                prev = conn.execute(
                    """
                    SELECT is_achieved FROM goal_log
                    WHERE goal_id = ? AND period_date = ?
                    """,
                    (goal["id"], progress["period_start"])
                ).fetchone()
                was_achieved = bool(prev["is_achieved"]) if prev else False

                conn.execute(
                    """
                    INSERT OR REPLACE INTO goal_log
                    (goal_id, period_date, actual_value, target_value, is_achieved)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        goal["id"], progress["period_start"],
                        progress["current_value"], progress["target_value"],
                        (1 if progress["achieved"] else 0),
                    )
                )

                if progress["achieved"] and not was_achieved:
                    # !! maybe want feedback on progress of unachieved goals that aren't shown on log-tab
                    events.append(
                        {"type": "recurring", "goal": goal, "progress": progress}
                    )

            elif goal["goal_type"] == "lifetime" and (progress["achieved"] and not goal["achieved_at"]):
                conn.execute(
                    "UPDATE goals SET achieved_at = ?, is_active = 0 WHERE id = ?",
                    (target.isoformat(), goal["id"],)
                )
                filters = {}
                m, a = goal["medium_type"], goal["activity_type"]
                if m:
                    filters["medium_type"] = m
                if a:
                    filters["activity_type"] = a

                cur = conn.execute(
                    """
                    INSERT INTO milestones
                    (title, date, goal_id, metric, metric_value, filter_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"Goal achieved: {goal['name']}", target.isoformat(),
                        goal["id"], goal["metric"], progress["current_value"],
                        json.dumps(filters) if filters else None,
                    )
                )
                events.append({
                    "type": "lifetime", "goal": goal,
                    "progress": progress, "milestone_id": cur.lastrowid,
                })

        # --- 2. achieved lifetime goals -> regression check
        if target >= date.today():
            achieved_rows = conn.execute(
                """
                SELECT * from goals
                WHERE goal_type = 'lifetime' AND achieved_at IS NOT NULL
                """
            ).fetchall()

            for row in achieved_rows:
                goal = dict(row)
                progress = compute_goal_progress(goal, as_of_date=target.isoformat())
                if progress["achieved"]:  # according to live session data
                    continue

                #  Un-achieve, reactivate goal, delete associated milestone
                conn.execute(
                    "UPDATE goals SET achieved_at = NULL, is_active = 1 WHERE id = ?",
                    (goal["id"],)
                )

                conn.execute("DELETE FROM milestones WHERE goal_id = ?", (goal["id"],))

                events.append({
                    "type": "lifetime_regression", "goal": goal, "progress": progress,
                })

    return events


def get_log_strip_goals() -> list[dict]:
    """Active goals flagged to be shown on log-tab strip, with progress data for each."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM goals
            WHERE is_active = 1 AND show_on_log = 1
            ORDER BY pinned DESC, created_at
            """
        ).fetchall()
    goals = [dict(r) for r in rows]
    for g in goals:
        g["progress"] = compute_goal_progress(g)
    return goals