import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd

from .dashboard import DashboardCard
from db import ENUMS

MEDIUM_COLORS = {
    "anime":        "#5B8FF9",
    "drama":        "#5AD8A6",
    "light_novel":  "#F6BD16",
    "visual_novel": "#E86452",
    "novel":        "#6DC8EC",
    "book":         "#945FB9",
    "manga":        "#FF9845",
    "game":         "#1E9493",
    "podcast":      "#FF99C3",
    "audiobook":    "#9270CA",
    "youtube":      "#FF6B6B",
}


def _group_small_slices(
        data: list[dict],
        value_key: str = "total_minutes",
        label_key: str = "medium_type",
        threshold: float = 0.05
):
    """
    Merge entries below `threshold` (as a fraction of the total) into a single "other" row
    Input Data: [{label_key: "novel", value_key: 1234,...}, ...]
    Output Data: same structure, with smaller entries combined in "other"
        [
            {label_key: "novel", value_key: 1234,...},
            ...,
            {label_key: "other", value_key: 123,...},
        ]
    """
    total = sum([r[value_key] for r in data])
    if total == 0:
        return data

    cutoff = total * threshold
    keepers, smalls = [], []
    for row in data:
        if row[value_key] >= cutoff:
            keepers.append(row)
        else:
            smalls.append(row)

    if smalls:
        other_row = {label_key: "other", value_key: sum(r[value_key] for r in smalls)}
        if "session_count" in smalls[0]:
            other_row["session_count"] = sum(r.get("session_count", 0) for r in smalls)
        keepers.append(other_row)
    return keepers


def _fill_missing_periods(data: dict, group_by: str, fill_keys: list[str]) -> dict:
    """
    Fill in missing periods between earliest and latest keys with zero-valued entries.
    group_by:
        "month" -> keys are expected as "YYYY-MM"
        "week" -> keys are expected as "YYYY-MM-DD" anchored to Monday of that week
        otherwise, returns data as-is
    fill_keys: subdict keys that are to be defaulted to 0
    """
    if not data or group_by not in ("month", "week"):
        return data

    periods = sorted(data.keys())
    start, end = periods[0], periods[-1]

    if group_by == "month":
        rng = pd.period_range(start=start, end=end, freq="M")
        full_keys = [str(p) for p in rng]
    else:  # "week"
        rng = pd.date_range(start=start, end=end, freq="W-MON")
        full_keys = [d.strftime("%Y-%m-%d") for d in rng]

    filled = {}
    for key in full_keys:
        filled[key] = data[key] if key in data else {k: 0 for k in fill_keys}
    return filled


def _limit_recent_periods(data: dict, max_periods: int) -> dict:
    """Keep only the N most recent periods. Expects sortable stable string keys"""
    if len(data) <= max_periods:
        return dict(sorted(data.items()))
    sorted_keys = sorted(data.keys())[-max_periods:]
    return {k: data[k] for k in sorted_keys}


def _format_period_str(filters: dict) -> str:
    """Readable label for currently filtered period"""
    if filters.get("start_date") and filters.get("end_date"):
        return f"{filters.get('start_date')} → {filters.get('end_date')}"
    if filters.get("start_date"):
        return f"Since {filters.get('start_date')}"
    if filters.get("end_date"):
        return f"Until {filters.get('end_date')}"
    return "All-time"


class MplChartCard(DashboardCard):
    """
    Base class for matplotlib-based dashboard charts
    Handles Figure/Canvas creation. Subclasses just implement _draw()
    """
    def __init__(self, title: str, figsize=(5, 4), dpi=100, parent=None):
        super().__init__(title, parent)

        # FigureCanvasQTAgg  <  Figure  <  Axes
        self.figure, self.ax = plt.subplots(figsize=figsize)
        self.figure.set_dpi(dpi)
        # self.figure.tight_layout()

        self.canvas = FigureCanvas(self.figure)  # wraps matplotlib Figure as a QtWidget
        self.canvas.setMinimumHeight(300)
        # self.canvas.installEventFilter(self)  # !TODO! propagate wheel scroll event
        self.add_content_widget(self.canvas)

        # self.figure.set_alpha(0)

    def refresh(self):
        self.ax.clear()
        self._draw()
        self.canvas.draw()  # updates the screen
        self.figure.tight_layout()

    def _draw(self):
        """Must be implemented by subclasses. Plot data on self.ax"""
        raise NotImplementedError


class TimeByMediumPieChart(MplChartCard):
    """
    Pie chart showing distribution of time spent across media types.
    """

    SUPPORTED_FILTERS = {"start_date", "end_date"}

    def __init__(self, parent=None):
        super().__init__("Time by Medium", figsize=(8, 4), parent=parent)

    def _draw(self):
        import repo
        data = repo.get_time_by_medium(
            self.filters.get("start_date"),
            self.filters.get("end_date"),
            self.filters.get("activity_type")
        )
        print("TIME BY MEDIUM:", data)
        # [{"medium_type": "novel", "total_minutes": 1234, "session_count": 62}, ...]

        if not data:
            self.ax.text(0.5, 0.5, "No data",
                         ha="center", va="center",
                         transform=self.ax.transAxes)
            return
        data = _group_small_slices(data)

        labels, values, colors = [], [], []
        for row in data:
            labels.append(row["medium_type"].replace("_", " ").title())
            values.append(row["total_minutes"])
            colors.append(MEDIUM_COLORS.get(row["medium_type"], "#999999"))

        wedges, texts, autotexts = self.ax.pie(
            values,
            labels=labels,
            colors=colors,
            startangle=90,
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 4.5 else "",
            pctdistance=0.75
        )

        for t in autotexts:
            t.set_fontsize(9)
            # t.set_color("white")
            t.set_fontweight("bold")

        self.ax.set_title(_format_period_str(self.filters), fontsize=10)


class TimeByMediumBarChart(MplChartCard):  # !TODO!
    """
    Stacked bar chart: time by medium, per month
    """
    SUPPORTED_FILTERS = {"start_date", "end_date", "activity_type"}

    def __init__(self, parent=None):
        super().__init__("Monthly Time by Medium", figsize=(8, 8), parent=parent)

    def _draw(self):
        import repo
        import numpy as np
        data = repo.get_time_by_medium_monthly(
            self.filters.get("start_date"),
            self.filters.get("end_date"),
            self.filters.get("activity_type")
        )
        # {"2026-04": {"novel": 1234, "anime": 234,...}, "2026-05": {...}, ...}
        periods = [period for period in data.keys()]
        x = range(len(periods))
        bottom = [0] * len(periods)

        # print("WHAT IS DATA VALUES??", data.values())

        for i, m in enumerate(ENUMS["MEDIUM_TYPES"]):
            values = np.round(
                [row.get(m, 0) / 60 for row in data.values()],  # convert to hours
                decimals=2)
            color = MEDIUM_COLORS.get(m, "#CCC")
            self.ax.bar(x, values, bottom=bottom,
                        label=m.capitalize(), color=color, width=0.5)
            bottom = [b + v for b, v in zip(bottom, values)]

            self.ax.set_xticks(x)
            self.ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=8)
            self.ax.set_ylabel("Hours")
            self.ax.legend(fontsize=8)


class ActivityRatioChart(MplChartCard):
    """
    Stacked bar chart: reading vs listening, per month.
    """
    SUPPORTED_FILTERS = {"start_date", "end_date", "group_by"}
    DEFAULT_FILTERS = {"group_by": "month"}

    ACTIVITY_COLORS = {
        "reading": "#F6BD16",
        "listening": "#5B8FF9",
    }

    def __init__(self, parent=None, group_by="month", max_periods=12):
        super().__init__("Reading vs Listening", figsize=(8, 3.5), parent=parent)
        self.max_periods = max_periods
        self.filters["group_by"] = group_by

    def _draw(self):
        import repo
        import numpy as np
        data = repo.get_activity_breakdown(
            self.filters.get("start_date"),
            self.filters.get("end_date"),
            self.filters.get("group_by")
        )

        if not data:
            self.ax.text(0.5, 0.5, "No data",
                         ha="center", va="center")
            return
        # data = {period1: {reading: X, listening: Y, both: Z, session_count: 123}, period2: {...}}
        # Fill empty period gaps
        data = _fill_missing_periods(
            data,
            group_by=self.filters.get("group_by"),
            fill_keys=["reading", "listening", "both", "session_count"]
        )
        # Limit to 12 most recent periods
        data = _limit_recent_periods(data, self.max_periods)

        # Distribute "both" activity minutes 50/50 between reading/listening
        adjusted = {}
        for period, vals in data.items():
            half_both = vals.get("both", 0) / 2
            adjusted[period] = {
                "reading": vals.get("reading", 0) + half_both,
                "listening": vals.get("listening", 0) + half_both,
            }

        periods = list(adjusted.keys())
        x = range(len(periods))
        bottom = np.zeros(len(periods))

        for activity in ["reading", "listening"]:
            values = np.array(
                [round(adjusted[p][activity] / 60, 2) for p in periods]  # minutes to hours
            )
            color = self.ACTIVITY_COLORS.get(activity, "#CCC")
            self.ax.bar(
                x, values, bottom=bottom,
                label=activity.capitalize(),
                color=color,
                width=0.5
            )
            bottom += values

            self.ax.set_xticks(x)
            self.ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=8)
            self.ax.set_ylabel("Hours")
            self.ax.legend(fontsize=8, loc="upper left")
            self.ax.set_title("Monthly activity ratio", fontsize=10)
