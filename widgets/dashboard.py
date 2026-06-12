from PyQt6.QtWidgets import (
    QWidget, QFrame, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QScrollArea, QSizePolicy,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from datetime import date
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
        self.medium_type: str = None
        self.activity_type: str = None

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "medium_type": self.medium_type,
            "activity_type": self.activity_type,
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
        self._layout.addStretch()

    def add_content_widget(self, widget: QWidget):
        self._layout.insertWidget(self._layout.count() - 1, widget)

    def add_content_layout(self, layout: QLayout):
        self._layout.insertLayout(self._layout.count() - 1, layout)

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

        # Scrollable area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setSpacing(12)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        main_layout.addWidget(self._scroll)

    def _connect_signals(self):
        self._refresh_btn.clicked.connect(self._on_refresh)

    def add_card(self, card: DashboardCard):
        self._cards.append(card)
        # Insert widget before stretch
        self._card_layout.insertWidget(self._card_layout.count() - 1, card)
        card.refresh(self._filters)

    def add_cards_hbox(self, *cards: DashboardCard):
        hbox = QHBoxLayout()

        self._card_layout.insertLayout(self._card_layout.count() - 1, hbox)
        for c in cards:
            self._cards.append(c)
            hbox.addWidget(c)
            c.refresh(self._filters)

    def _on_refresh(self):
        print("REFRESHING DASHBOARD....")
        for card in self._cards:
            print(card.card_title)
            card.refresh(self._filters)

    def refresh_all(self):
        """Trigger refresh on all cards (with current filters)"""
        self._on_refresh()


# SUMMARY CARDS
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
    def __init__(self, parent=None):
        super().__init__("Today's Summary", parent)

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

    def refresh(self, filters: DashboardFilters):
        import repo
        summary = repo.get_daily_summary()

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


# !TODO! Weekly Summary


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

    def refresh(self, filters: DashboardFilters):
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


