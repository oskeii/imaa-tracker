from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QLabel
)
from .dashboard import DashboardCard
from db import format_minutes, format_duration_str

from datetime import date
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

ACTIVITY_COLORS = {
    "reading": "#F6BD16",
    "listening": "#5B8FF9",
    "both": "#5AD8A6"
}


class StatBlock(QWidget):
    """
    Secondary stat: a number stacked above a small muted label
    """
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self._value = QLabel("--")
        self._value.setStyleSheet(
            "font-size: 18px; font-weight: 600; color: palette(text);"
        )
        self._label = QLabel(label.upper())
        self._label.setStyleSheet(
            "font-size: 9px; letter-spacing: 1px; color: palette(mid);"
        )

        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, value: str):
        self._value.setText(value)


class HeroStat(QWidget):
    """
    Primary "hero" stat: headline number of the card
    (2x the size of a StatBlock)
    """
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._value = QLabel("--")
        self._value.setStyleSheet(
            "font-size: 34px; font-weight: 700px; color: palette(text);"
        )
        self._label = QLabel(label.upper())
        self._label.setStyleSheet(
            "font-size: 10px; letter-spacing: 1.5px; color: palette(mid);"
        )
        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, value: str):
        self._value.setText(value)


def _make_separator() -> QFrame:
    """A thin horizontal divider between card sections"""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    sep.setStyleSheet("color: palette(mid); margin: 8px 0;")
    sep.setFixedHeight(1)
    return sep


def _stat_row(*blocks: QWidget) -> QHBoxLayout:
    """Pack StatBlocks into evenly-spaced horizontal row"""
    row = QHBoxLayout()
    row.setSpacing(20)
    for b in blocks:
        row.addWidget(b)
        row.addStretch()
    return row


class DailySummaryCard(DashboardCard):
    """Today's immersion summary: time, characters, sessions"""
    SUPPORTED_FILTERS = {"target_date"}
    DEFAULT_FILTERS = {"target_date": date.today().isoformat()}
    STEP_FILTER = "target_date"
    STEP_PERIOD = "day"

    def __init__(self, parent=None):
        super().__init__("Daily Summary", parent)

        # Subtitle: date
        self._date_label = QLabel()
        self._date_label.setStyleSheet(
            "font-size: 11px; color: palette(mid); margin-bottom: 4px;"
        )
        self.add_content_widget(self._date_label)
        # self.add_content_widget(_make_separator())

        # Hero: total immersion time
        self._time_hero = HeroStat("Immersion Time")
        self.add_content_widget(self._time_hero)
        self.add_content_widget(_make_separator())

        # Secondary row: characters and session count
        self._chars_block = StatBlock("Characters")
        self._sessions_block = StatBlock("Sessions")
        self.add_content_layout(_stat_row(self._chars_block, self._sessions_block))
        self.add_content_widget(_make_separator())

        # Activity breakdown row
        self._reading_block = StatBlock("Reading")
        self._listening_block = StatBlock("Listening")
        self._both_block = StatBlock("Both")
        self.add_content_layout(_stat_row(
            self._reading_block, self._listening_block, self._both_block,
        ))

    def refresh(self):
        import repo
        summary = repo.get_daily_summary(target_date=self.filters.get("target_date"))

        d = date.fromisoformat(summary["date"])
        self._date_label.setText(d.strftime("%A, %B %d"))

        self._time_hero.set_value(format_duration_str(summary["total_minutes"]))
        self._chars_block.set_value(f"{summary['total_chars']:,}")
        self._sessions_block.set_value(str(summary["session_count"]))
        # !! currently does not count 'both' activity
        by_act = summary.get("by_activity", {})
        self._reading_block.set_value(format_minutes(by_act.get("reading", 0)))
        self._listening_block.set_value(format_minutes(by_act.get("listening", 0)))
        self._both_block.set_value(format_minutes(by_act.get("both", 0)))


class WeeklySummaryCard(DashboardCard):
    """
    Two-column weekly overview
    """
    SUPPORTED_FILTERS = {"target_date"}
    DEFAULT_FILTERS = {"target_date": date.today().isoformat()}
    STEP_FILTER = "target_date"
    STEP_PERIOD = "week"

    def __init__(self, parent=None):
        super().__init__("Weekly Summary", parent)

        # Subtitle: date range
        self._week_label = QLabel()
        self._week_label.setStyleSheet(
            "font-size: 11px; color: palette(mid); margin-bottom: 4px;"
        )
        self.add_content_widget(self._week_label)
        self.add_content_widget(_make_separator())

        # Two-column body
        body = QHBoxLayout()
        body.setSpacing(24)
        self.add_content_layout(body)

        stats_col = QVBoxLayout()
        stats_col.setSpacing(8)
        self._build_stats_column(stats_col)
        body.addLayout(stats_col, stretch=2)

        chart_col = QVBoxLayout()
        self._build_chart_column(chart_col)
        body.addLayout(chart_col, stretch=3)

    def _build_stats_column(self, layout: QVBoxLayout):
        self._time_hero = HeroStat("Immersion Time")
        layout.addWidget(self._time_hero)
        # layout.addWidget(_make_separator())

        self._chars_hero = HeroStat("Total Characters")
        layout.addWidget(self._chars_hero)
        layout.addWidget(_make_separator())

        # self._chars_block = StatBlock("Characters")
        self._avg_chars_block = StatBlock("Avg Chars/Day")
        self._avg_time_block = StatBlock("Avg Time/Day")

        self._reading_block = StatBlock("Reading")
        self._listening_block = StatBlock("Listening")
        self._avg_read_time_block = StatBlock("Avg Reading Time/Day")
        self._avg_listen_time_block = StatBlock("Avg Listening Time/Day")

        layout.addLayout(_stat_row(self._avg_time_block))
        layout.addWidget(_make_separator())
        layout.addLayout(_stat_row(self._reading_block, self._avg_read_time_block, self._avg_chars_block))
        layout.addWidget(_make_separator())
        layout.addLayout(_stat_row(self._listening_block, self._avg_listen_time_block))

        layout.addStretch()

    def _build_chart_column(self, layout: QVBoxLayout):
        self._fig, self._ax = plt.subplots(figsize=(5, 3.5))
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setMinimumHeight(240)
        layout.addWidget(self._canvas)

    def refresh(self):
        import repo
        summary = repo.get_weekly_summary(week_of=self.filters.get("target_date"))
        print("WEEKLY SUMMARY:", summary)

        # Subtitle
        week_start = date.fromisoformat(summary['week_start']).strftime("%b-%d-%Y")
        week_end = date.fromisoformat(summary['week_end']).strftime("%b-%d-%Y")
        self._week_label.setText(
            f"{week_start} → {week_end}"
        )

        # stats column
        self._time_hero.set_value(format_duration_str(summary["total_minutes"]))
        self._chars_hero.set_value(f"{summary['total_chars']:,}")
        by_act = summary["by_activity"]
        self._reading_block.set_value(format_minutes(by_act["reading"]))
        self._listening_block.set_value(format_minutes(by_act["listening"]))

        avg = summary["daily_avg"]
        self._avg_chars_block.set_value(f"{avg['chars']:,}")
        self._avg_time_block.set_value(format_minutes(avg["minutes"]))
        self._avg_read_time_block.set_value(format_minutes(avg["reading_minutes"]))
        self._avg_listen_time_block.set_value(format_minutes(avg["listening_minutes"]))

        # chart column
        self._draw_activity_chart(summary["daily_minutes"])

    def _draw_activity_chart(self, daily_minutes: dict):
        """Stacked bar for daily activity breakdown"""
        self._ax.clear()

        # daily_minutes already in order (mon->sun)
        days = list(daily_minutes.keys())
        x = np.arange(len(days))
        bottom = np.zeros(len(days))
        day_labels = [date.fromisoformat(d).strftime("%a") for d in days]

        for activity in ("reading", "listening", "both"):
            values = np.array([daily_minutes[d][activity] for d in days])
            self._ax.bar(
                x, values, bottom=bottom,
                label=activity.capitalize(),
                color=ACTIVITY_COLORS[activity],
                width=0.7,
            )
            bottom += values

        self._ax.set_xticks(x)
        self._ax.set_xticklabels(day_labels, fontsize=9)
        self._ax.set_ylabel("Minutes", fontsize=9)
        self._ax.legend(fontsize=8, loc="upper right", frameon=False)
        self._ax.set_title("Daily Activity", fontsize=10)

        self._ax.spines["top"].set_visible(False)
        self._ax.spines["right"].set_visible(False)

        self._canvas.draw()
        self._fig.tight_layout()


class AllTimeTotalsCard(DashboardCard):
    """All-time grand totals."""
    def __init__(self, parent=None):
        super().__init__("All-Time Totals", parent)

        # Subtitle: "Since YYYY-MM-DD"
        self._since_label = QLabel()
        self._since_label.setStyleSheet(
            "font-size: 11px; color: palette(mid); margin-bottom: 4px;"
        )
        self.add_content_widget(self._since_label)
        # self.add_content_widget(_make_separator())

        # Hero: total time
        self._time_hero = HeroStat("Total Immersion Time")
        self.add_content_widget(self._time_hero)
        self.add_content_widget(_make_separator())

        # Volume stats row
        self._chars_block = StatBlock("Chars")
        self._sessions_block = StatBlock("Sessions")
        self._active_days_block = StatBlock("Active Days")
        self.add_content_layout(_stat_row(
            self._chars_block, self._sessions_block, self._active_days_block
        ))
        self.add_content_widget(_make_separator())

        # Activity breakdown
        self._reading_block = StatBlock("Reading")
        self._listening_block = StatBlock("Listening")
        self._both_block = StatBlock("Both")
        self.add_content_layout(_stat_row(
            self._reading_block, self._listening_block, self._both_block,
        ))
        self.add_content_widget(_make_separator())

        # Content row
        self._pages_block = StatBlock("Pages")
        self._episodes_block = StatBlock("Episodes")
        self._titles_block = StatBlock("Titles")
        self.add_content_layout(_stat_row(
            self._pages_block, self._episodes_block, self._titles_block,
        ))

    def refresh(self):
        import repo
        totals = repo.get_alltime_totals()
        print("ALL-TIME TOTALS:", totals)

        first = totals.get("first_session")
        if first:
            d = date.fromisoformat(first)
            self._since_label.setText(f"Since {d.strftime('%B %d, %Y')}")
        else:
            self._since_label.setText("No sessions logged yet")
        # hero
        self._time_hero.set_value(format_minutes(totals.get("total_minutes", 0)))
        # volume row
        self._sessions_block.set_value(f"{totals.get('session_count', 0):,}")
        self._active_days_block.set_value(f"{totals.get('active_days', 0):,}")
        self._titles_block.set_value(f"{totals.get('title_count', 0):,}")
        # activity row
        by_act = totals.get("by_activity", {})
        self._reading_block.set_value(format_minutes(by_act.get("reading", 0)))
        self._listening_block.set_value(format_minutes(by_act.get("listening", 0)))
        self._both_block.set_value(format_minutes(by_act.get("both", 0)))

        self._chars_block.set_value(f"{totals.get('total_chars', 0):,}")
        self._pages_block.set_value(f"{totals.get('total_pages', 0):,}")
        self._episodes_block.set_value(f"{totals.get('total_episodes', 0):,}")
