import pyqtgraph as pg
from PyQt6.QtCore import Qt
from datetime import date, timedelta

from .dashboard import DashboardCard, DashboardFilters


pg.setConfigOptions(antialias=True)

def dates_to_timestamps(date_strings: list[str]) -> list[int]:
    """Convert ISO date strings to UNIX timestamps for pyqtgraph axis"""
    return [date.fromisoformat(d).toordinal() for d in date_strings]


class DateAxisItem(pg.AxisItem):
    """
    Custom AxisItem class to display Unix timestamps as human-readable dates
    """
    def tickStrings(self, values: list[float], scale: float, spacing: float):
        strings = []
        for v in values:
            try:
                d = date.fromordinal(int(v))
                # Different date formats based on zoom level
                if spacing > 28:  # show month
                    strings.append(d.strftime("%Y-%m"))
                elif spacing > 5:  # show month-day
                    strings.append(d.strftime("%b %d"))
                else:  # show full date
                    strings.append(d.strftime("%m-%d"))
            except (ValueError, OverflowError):
                strings.append("")

        return strings


class PgChartCard(DashboardCard):
    """
    Base class for pyqtgraph-based dashboard cards.
    Creates a PlotWidget and handles basic setup.
    """
    def __init__(self, title: str, use_date_axis: bool = True, parent=None):
        super().__init__(title, parent)
        # self.plot_widget = pg.PlotWidget()
        # self.plot_widget = None

        if use_date_axis:
            date_axis = DateAxisItem(orientation="bottom")
            self.plot_widget = pg.PlotWidget(axisItems={"bottom": date_axis})
        else:
            self.plot_widget = pg.PlotWidget()

        self.plot_widget.setBackground("transparent")
        self.plot_widget.setMinimumHeight(300)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)

        self.view_box = self.plot_widget.getViewBox()
        self.view_box.setLimits(yMin=0)

        self.add_content_widget(self.plot_widget)

    def refresh(self, filters: DashboardFilters):
        self.plot_widget.clear()
        self._draw(filters)

    def _draw(self, filters: DashboardFilters):
        raise NotImplementedError


class ImmersionTimeTrend(PgChartCard):
    """
    Line chart: daily immersion time over the selected period
        Line A - daily hours
        Line B - 7-day rolling average
    """
    def __init__(self, parent=None):
        super().__init__("Immersion Time Trend", parent=parent)
        self.plot_widget.setLabel("left", "Hours")

    def _draw(self, filters: DashboardFilters):
        import repo
        import pandas as pd

        data = repo.get_daily_totals(
            filters.start_date,
            filters.end_date
        )

        if not data:
            return

        # [{"date": "2026-04-01", "total_minutes": 78, "total_chars": 3665, "session_count": 2}, ...]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        # Fill in missing dates with 0
        full_date_range = pd.date_range(
            start=df["date"].iloc[0],
            end=df["date"].iloc[-1],
            freq="D"
        )
        df = df.set_index("date").reindex(full_date_range, fill_value=0).reset_index()
        df.rename(columns={"index": "date"}, inplace=True)

        # convert dates to Unix timestamps for pyqtgraph x-axis
        x = [d.toordinal() for d in df["date"].dt.date]
        total_hours = df["total_minutes"] / 60

        # Adjust axis limits
        p95 = total_hours.quantile(0.95)
        y_max_view = max(p95*1.3, 1.5)

        self.view_box.setLimits(
            xMin=x[0]-6, xMax=x[-1]+6,
            yMin=0, yMax=total_hours.max() * 1.1,
            minYRange=1.5, minXRange=7,
        )
        self.plot_widget.setYRange(0, y_max_view)

        self.plot_widget.addLegend()

        # Line A: daily hours
        self.plot_widget.plot(
            x, total_hours.values,
            pen=pg.mkPen("#5B8FF933", width=1),
            name="Daily",
        )

        # Outlier markers
        outlier_mask = total_hours > p95
        if outlier_mask.any():
            ox = [x[i] for i in range(len(x)) if outlier_mask.iloc[i]]
            oy = total_hours[outlier_mask].values
            self.plot_widget.plot(
                ox, oy, pen=None,
                symbol="t", symbolSize=10, symbolBrush="#FF6B6B",
                name="Outliers",
            )


        # Line B: 14-day rolling average
        if len(df) >= 14:
            rolling = total_hours.rolling(14, min_periods=1).mean()
            self.plot_widget.plot(
                x, rolling.values,
                pen=pg.mkPen("#FF6B6B", width=2.5),
                name="14-day avg"
            )


class ReadingSpeedTrend(PgChartCard):
    """
    Reading speed (chars/hr) over time.
    Scatter plot: reading speed per session
    Line plot: rolling average trend

    """
    def __init__(self, parent=None):
        super().__init__(title="Reading Speed Trend", parent=parent)
        self.plot_widget.setLabel("left", "Chars/hr")

    def _draw(self, filters: DashboardFilters):
        import repo
        import pandas as pd
        import numpy as np

        data = repo.get_reading_speed_data(filters.start_date, filters.end_date)
        if not data:
            return

        df = pd.DataFrame(data)
        # Compute derived metric
        df["speed"] = df["character_count"] / (df["duration_minutes"] / 60)

        # !! Filter extreme outliers
        # q1, q3 = np.percentile(df["speed"], [0.25, 0.75])
        # l_bound = q1 - ((q3-q1) * 1.5)
        # u_bound = q3 + ((q3-q1) * 1.5)
        # if (q3-q1) > 0:
        #     df = df[(df["speed"] >= l_bound) &
        #         (df["speed"] <= u_bound)]
        # if df.empty:
        #     return

        x = dates_to_timestamps(df["date"].values)
        # Adjust axis limits
        p95 = df["speed"].quantile(0.95)
        y_max_view = max(p95*1.5, 5000)

        self.view_box.setLimits(
            xMin=min(x)-14, xMax=max(x)+14,
            yMin=0, yMax=df["speed"].max() * 1.1,
            minYRange=50, minXRange=5,
        )
        self.plot_widget.setYRange(0, y_max_view)
        self.plot_widget.addLegend()
        # Scatter plot for individual sessions
        has_direction = df["reading_direction"].notna().any()
        self.plot_widget.plot(
            x, df["speed"].values,
            pen=None,
            symbol="o", symbolSize=6,
            symbolBrush="#5B8FF9"
        )

        # Rolling average trend line
        if len(df) >= 5:
            rolling = df["speed"].rolling(10, min_periods=2).mean()
            self.plot_widget.plot(
                x, rolling.values,
                pen=pg.mkPen("#F6BD16", width=2.5),
                name="10-session avg"
            )
