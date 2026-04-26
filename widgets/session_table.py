from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView,
    QLabel, QDateEdit, QComboBox, QPushButton, QAbstractItemView
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate

from db import ENUMS, format_minutes
import repo

# Column definitions: (header_text, dict_key, alignment  # !TODO!
COLUMNS = [
    ("Date",        "date",             Qt.AlignmentFlag.AlignCenter),
    ("Title",       "title_text",       Qt.AlignmentFlag.AlignLeft),
    ("Medium",      "medium_type",      Qt.AlignmentFlag.AlignCenter),
    ("Activity",    "activity_type",    Qt.AlignmentFlag.AlignCenter),
    ("Duration",    "duration_minutes", Qt.AlignmentFlag.AlignRight),
    ("Chars",       "character_count",  Qt.AlignmentFlag.AlignRight),
    ("Pages",       "page_count",       Qt.AlignmentFlag.AlignRight),
    ("Episodes",    "episode_count",    Qt.AlignmentFlag.AlignRight),
    ("Vol.",        "volume",           Qt.AlignmentFlag.AlignCenter),
    ("Ch.",         "chapter",          Qt.AlignmentFlag.AlignCenter),
]


class SessionTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: list[dict] = []

    def load(self, sessions: list[dict]):
        """Replace all data for a fresh data load."""
        self.beginResetModel()
        self._sessions = sessions
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._sessions)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        session = self._sessions[index.row()]
        header, key, alignment = COLUMNS[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            value = session.get(key)
            if value is None:
                return ""
            if key == "duration_minutes":
                return format_minutes(value)
            if key == "character_count":
                return f"{value:,}"
            return str(value)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return alignment

        return None

    def headerData(self, section: int, orientation, role: int = Qt.ItemDataRole.DisplayRole):
        """Column header labels"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section][0]  # !! better to use dict...
        return None

    def get_session_id(self, row: int):
        """Helper to get database ID for a row"""
        if 0 <= row < len(self._sessions):
            return self._sessions[row].get("id")
        return None


class SessionHistoryWidget(QWidget):
    """
    Filterable table showing logged immersion sessions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        # --- Filter bar ---
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-3))
        self.start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("Medium:"))
        self.medium_filter = QComboBox()
        self.medium_filter.addItem("Any", userData=None)
        for mt in ENUMS["MEDIUM_TYPES"]:
            self.medium_filter.addItem(mt.replace("_", " ").title(), userData=mt)
        filter_layout.addWidget(self.medium_filter)

        filter_layout.addWidget(QLabel("Activity:"))
        self.activity_filter = QComboBox()
        self.activity_filter.addItem("Any", userData=None)
        for at in ENUMS["ACTIVITY_TYPES"]:
            self.activity_filter.addItem(at.capitalize(), userData=at)
        filter_layout.addWidget(self.activity_filter)

        self.refresh_btn = QPushButton("Refresh")
        filter_layout.addWidget(self.refresh_btn)
        filter_layout.addStretch()

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        filter_layout.addWidget(self.delete_btn)

        layout.addLayout(filter_layout)

        # --- Table view ---
        self.tabel_view = QTableView()
        self.model = SessionTableModel()
        self.tabel_view.setModel(self.model)

        # configure view
        self.tabel_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabel_view.setAlternatingRowColors(True)
        self.tabel_view.setSortingEnabled(False)  # sorting vie SQL
        # set Title column stretch # !!
        # header = self.tabel_view.horizontalHeader()
        # header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tabel_view)

    def _connect_signals(self):
        self.refresh_btn.clicked.connect(self.refresh)
        self.delete_btn.clicked.connect(self.delete_selected)

        self.tabel_view.selectionModel().selectionChanged.connect(
            lambda: self.delete_btn.setEnabled(
                bool(self.tabel_view.selectionModel().selectedRows())
            )
        )

    def refresh(self):
        """Re-query the database with current filters and reload table."""
        print("Refreshing session history table...")
        print(f"""
            CURRENT FILTERS:
            start_date=\t{self.start_date.date().toString("yyyy-MM-dd")},
            end_date=\t{self.end_date.date().toString("yyyy-MM-dd")},
            medium_type=\t{self.medium_filter.currentData()},
            activity_type=\t{self.activity_filter.currentData()}           
        """)
        sessions = repo.get_immersion_sessions(
            start_date=self.start_date.date().toString("yyyy-MM-dd"),
            end_date=self.end_date.date().toString("yyyy-MM-dd"),
            medium_type=self.medium_filter.currentData(),
            activity_type=self.activity_filter.currentData()
        )
        self.model.load(sessions)

        print("RECENT SESSIONS:\n", sessions)

        # Update summary
        total_min = sum(s.get("duration_minutes", 0) or 0 for s in sessions)
        total_char = sum(s.get("character_count", 0) or 0 for s in sessions)
        self.summary_label.setText(
            f"{len(sessions)} sessions  |  "
            f"{format_minutes(total_min)} total  |  "
            f"{total_char:,} characters"
        )

    def delete_selected(self):
        """Delete session of the currently selected row."""
        rows = self.tabel_view.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        session_id = self.model.get_session_id(row)
        if session_id is not None:
            repo.delete_immersion_session(session_id)
            self.refresh()
