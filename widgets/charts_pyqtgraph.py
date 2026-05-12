import pyqtgraph as pg
from PyQt6.QtCore import Qt
from datetime import date, timedelta

from .dashboard import DashboardCard, DashboardFilters


pg.setConfigOptions(antialias=True)

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

        print(x[1] - x[0])
        print(x[2] - x[0])
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


