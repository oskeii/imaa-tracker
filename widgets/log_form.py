from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDateEdit, QComboBox, QLineEdit, QSpinBox, QTextEdit,
    QLabel, QPushButton, QMessageBox, QCompleter,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from db import ENUMS

# Conditional visibility - which metric fields are relevant for each medium type
MEDIUM_FIELDS = {}

# Display names for medium types
MEDIUM_DISPLAY = {}


class LogForm(QWidget):
    """
    Form for logging immersion sessions.

    Signals:
        sig_session_logged: emitted after a session is successfully saved,
                            so other widgets (ex. session history table) know to refresh.
    """

    sig_session_logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Stopwatch ---
        self.label = QLabel("Stopwatch goes here")
        main_layout.addWidget(self.label)

        # --- Form fields ---
        form_group = QGroupBox("Log Session")
        form_layout = QFormLayout(form_group)

        # date
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        # self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Date:", self.date_edit)

        # medium type dropdown
        self.medium_combo = QComboBox()
        for mt in ENUMS["MEDIUM_TYPES"]:
            self.medium_combo.addItem(MEDIUM_DISPLAY.get(mt, mt), userData=mt)
        form_layout.addRow("Medium:", self.medium_combo)

        # title - text field with auto-complete
        self.title_edit = QLineEdit()
        # self.title_edit.setPlaceholderText("Start typing to search titles...")
        # self.title_completer = QCompleter()
        # self.title_edit.setCompleter(self.title_completer)
        form_layout.addRow("Title:", self.title_edit)

        # activity type
        self.activity_combo = QComboBox()
        for at in ENUMS["ACTIVITY_TYPES"]:
            self.activity_combo.addItem(at.capitalize(), userData=at)
        form_layout.addRow("Activity:", self.activity_combo)

        # duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1440)
        self.duration_spin.setSuffix(" min")
        form_layout.addRow("Duration:", self.duration_spin)

        # -- Conditional metric fields --

        # character count, page count, episode count, reading direction

        # details: volume, chapter, episode name, url, notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Additional comments...")
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow("Notes:", self.notes_edit)

        main_layout.addWidget(form_group)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()

        # log, log+new, clear
        self.log_btn = QPushButton("Log Session")
        self.log_btn.setDefault(True)

        self.log_new_btn = QPushButton("Log && New")
        self.log_new_btn.setToolTip("Log this session and clear the form for a new session")

        self.clear_btn = QPushButton("Clear")

        btn_layout.addStretch()
        btn_layout.addWidget(self.log_btn)
        btn_layout.addWidget(self.log_new_btn)
        btn_layout.addWidget(self.clear_btn)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

    def _connect_signals(self):
        # Medium type changes --> show/hide relevant fields

        # Stopwatch stopped --> populate duration field

        # Button actions
        pass

    def _update_field_visibility(self):
        """Show/hide  metric fields based on selected medium type."""
        pass

    def _update_default_activity(self):
        """Set a relevant default activity type based on selected medium type."""
        pass

    def _refresh_completer(self):
        """Update the title autocomplete list based on selected medium type."""
        pass

    def _collect_form_data(self):
        """Validate form fields. Returns dict or None if invalid."""
        return None

    def _submit(self):
        """Validate and save the session."""
        data = self._collect_form_data()
        pass

    def _submit_and_clear(self):
        """Save, then clear form for next entry."""
        data = self._collect_form_data()

    def _clear_form(self, keep_date=False, keep_medium=False):
        """Reset form. Optionally preserve date and medium for consecutive logs."""
        pass

    def statusBar_message(self, msg: str):
        """Show a message on main window's status bar."""
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(msg, 3000)
