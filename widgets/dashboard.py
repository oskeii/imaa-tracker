from PyQt6.QtWidgets import (
    QWidget, QFrame, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from db import ENUMS, format_minutes, format_duration_str


# APP:
#       Initialize a DashboardContainer object,
#       then use the add_card() method to add widgets from both the dashboard and charts modules

# DASHBOARD:
#       DashboardCard serves as the base class for each individual dashboard widget (charts, summaries)
#
#       DashboardContainer is the main widget for the dashboard tab.
#       It holds a scrollable area for dashboard widgets,
#       and a filter bar which propagates filter changes to all children.


class DashboardFilters:
    """Data class holding current filter state for dashboard."""
    def __init__(self):
        self.start_date: str = None
        self.end_date: str = None

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date
        }


class DashboardCard(QFrame):
    """
    Base class for dashboard widgets.
    Subclasses must implement:
        _build_content(self) -> QWidget | QLayout
        refresh(self, filters: DashboardFilters)
    """
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.card_title = title

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        # !! is this even doing anything?
        # self.setLineWidth(1)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self._layout.addWidget(self._title_label)

    def add_content_widget(self, widget: QWidget):
        self._layout.addWidget(widget)

    def add_content_layout(self, layout: QLayout):
        self._layout.addLayout(layout)

    def refresh(self, filters: DashboardFilters):
        """Must be implemented by subclass. Called when data is updated or filters changed."""
        raise NotImplementedError


class DashboardContainer(QWidget):
    """
    The main dashboard tab (container)

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[DashboardCard] = []
        self._filters = DashboardFilters()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        filter_layout.addWidget(self._refresh_btn)
        main_layout.addLayout(filter_layout)

        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.addStretch()
        main_layout.addWidget(self._card_container)

    def _connect_signals(self):
        self._refresh_btn.clicked.connect(self._on_refresh)

    def add_card(self, card: DashboardCard):
        self._cards.append(card)
        # Insert widget before stretch
        self._card_layout.insertWidget(self._card_layout.count() - 1, card)
        card.refresh(self._filters)

    def _on_refresh(self):
        print("REFRESHING DASHBOARD....")
        for card in self._cards:
            print(card.card_title)
            card.refresh(self._filters)

    def refresh_all(self):
        """Trigger refresh on all cards (with current filters)"""
        self._on_refresh()


# SUMMARY CARDS
class DailySummaryCard(DashboardCard):
    """Today's immersion summary: time, characters, sessions"""
    def __init__(self, parent=None):
        super().__init__("Today's Summary", parent)

        grid = QGridLayout()

        self._time_header = QLabel("Immersion Time")
        self._time_header.setStyleSheet("font-size: 11px; color: gray;")
        self._time_label = QLabel("0 min")
        self._time_label.setStyleSheet("font-weight: bold; font-size: 20px;")

        self._chars_header = QLabel("Characters Read")
        self._chars_header.setStyleSheet("font-size: 11px; color: gray;")
        self._chars_label = QLabel("0 chars")
        self._chars_label.setStyleSheet("font-weight: bold; font-size: 20px;")

        self._sessions_label = QLabel("0 sessions")
        self._sessions_label.setStyleSheet("font-size: 14px; color: gray;")
        self._reading_label = QLabel("Reading: 0 min")
        self._reading_label.setStyleSheet("font-size: 14px; color: gray;")
        self._listening_label = QLabel("Listening: 0 min")
        self._listening_label.setStyleSheet("font-size: 14px; color: gray;")

        grid.addWidget(self._time_header, 0, 0)
        grid.addWidget(self._time_label, 1, 0, 3, 1)
        grid.addWidget(self._chars_header, 0, 1)
        grid.addWidget(self._chars_label, 1, 1, 3, 1)

        grid.addWidget(self._sessions_label, 1, 2)
        grid.addWidget(self._listening_label, 2, 2)
        grid.addWidget(self._reading_label, 3, 2)

        self.add_content_layout(grid)

    def refresh(self, filters: DashboardFilters):
        import repo
        summary = repo.get_daily_summary()
        print("DAILY SUMMARY:", summary)

        self._time_label.setText(format_duration_str(summary["total_minutes"]))
        self._chars_label.setText(f'{summary["total_chars"]:,} chars')
        self._sessions_label.setText(f'{summary["session_count"]} sessions')

        # !! currently does not count 'both' activity
        by_act = summary.get("by_activity", {})
        self._reading_label.setText(
            f'Reading: {format_duration_str(by_act.get("reading", 0))}'
        )
        self._listening_label.setText(
            f'Listening: {format_duration_str(by_act.get("listening", 0))}'
        )


class AllTimeTotalsCard(DashboardCard):
    """All-time grand totals."""
    def __init__(self, parent=None):
        super().__init__("All-Time Totals", parent)
        self._labels = {}
        grid = QGridLayout()

        for i, (key, display) in enumerate([
            ("total_minutes", "Total Time"),
            ("total_chars", "Characters Read"),
            ("session_count", "Sessions"),
            ("active_days", "Active Days")
        ]):
            header = QLabel(display)
            header.setStyleSheet("font-size: 11px; color: gray;")
            value = QLabel("--")
            value.setStyleSheet("font-weight: bold; font-size: 16px")
            grid.addWidget(header, 0, i)
            grid.addWidget(value, 1, i)
            self._labels[key] = value

        self.add_content_layout(grid)

    def refresh(self, filters: DashboardFilters):
        import repo
        totals = repo.get_alltime_totals()
        print("ALL-TIME TOTALS:", totals)

        for key, label in self._labels.items():
            if key == "total_minutes":
                label.setText(format_minutes(totals[key]))
            else:
                label.setText(f"{totals[key]:,}")

