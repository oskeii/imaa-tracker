import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from .dashboard import DashboardCard, DashboardFilters
from db import ENUMS, format_minutes

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

    def refresh(self, filters: DashboardFilters):
        self.ax.clear()
        self._draw(filters)
        self.canvas.draw()  # updates the screen
        self.figure.tight_layout()
        # plt.tight_layout()

    def _draw(self, filters: DashboardFilters):
        """Must be implemented by subclasses. Plot data on self.ax"""
        raise NotImplementedError


class TimeByMediumPieChart(MplChartCard):
    """
    Pie chart showing distribution of time spent across media types.
    """
    def __init__(self, parent=None):
        super().__init__("Time by Medium", figsize=(8, 4), parent=parent)

    def _draw(self, filters: DashboardFilters):
        import repo
        data = repo.get_time_by_medium(filters.start_date, filters.end_date)
        print("TIME BY MEDIUM:", data)
        # [{"medium_type": "novel", "total_minutes": 1234, "session_count": 62}, ...]
        # !TODO! handle scenarios with too many categories

        if not data:
            self.ax.text(0.5, 0.5, "No data",
                         ha="center", va="center",
                         transform=self.ax.transAxes)
            return

        labels, values, colors = [], [], []
        for row in data:
            labels.append(row["medium_type"].replace("_", " ").title())
            values.append(row["total_minutes"])
            colors.append(MEDIUM_COLORS.get(row["medium_type"], "#CCCCCC"))

        wedges, texts, autotexts = self.ax.pie(
            values,
            labels=labels,
            colors=colors,
            startangle=90,
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
            pctdistance=0.75
        )

        for t in autotexts:
            t.set_fontsize(9)

        # !TODO! add header for filtered time period
        # self.ax.set_title(f"{filters.start_date} - {filters.end_date}")


class TimeByMediumBarChart(MplChartCard):  # !TODO!
    """
    Stacked bar chart: time by medium, per month
    """
    def __init__(self, parent=None):
        super().__init__("Monthly Time by Medium", figsize=(8, 8), parent=parent)

    def _draw(self, filters: DashboardFilters):
        import repo
        import numpy as np
        data = repo.get_time_by_medium_monthly(filters.start_date, filters.end_date)
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
    ACTIVITY_COLORS = {
        "reading": "#F6BD16",
        "listening": "#5B8FF9",
    }

    def __init__(self, parent=None):
        super().__init__("Reading vs Listening", figsize=(8, 3.5), parent=parent)

    def _draw(self, filters: DashboardFilters):
        import repo
        import numpy as np
        data = repo.get_activity_breakdown(
            start_date=filters.start_date,
            end_date=filters.end_date,
            group_by="month"
        )

        if not data:
            self.ax.text(0.5, 0.5, "No data",
                         ha="center", va="center")
            return
        # {period1: {reading: X, listening: Y, both: Z, session_count: 123}, period2: {...}}
        periods = [period for period in data.keys()]
        x = range(len(periods))
        bottom = [0] * len(periods)

        # print("WHAT IS DATA VALUES??", data.values())

        for i, activity in enumerate(["reading", "listening"]):
            values = np.round(
                [row.get(activity, 0)/60 for row in data.values()],  # convert to hours
                decimals=2)
            color = self.ACTIVITY_COLORS.get(activity, "#CCC")
            self.ax.bar(x, values, bottom=bottom,
                        label=activity.capitalize(), color=color, width=0.5)
            bottom = [b+v for b, v in zip(bottom, values)]

            self.ax.set_xticks(x)
            self.ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=8)
            self.ax.set_ylabel("Hours")
            self.ax.legend(fontsize=8)
            self.ax.set_title("Monthly activity ratio")
