from PyQt6.QtWidgets import (
    QWidget, QFrame, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QScrollArea, QSizePolicy,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt

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


# Summary cards moved to ./summary_cards.py
