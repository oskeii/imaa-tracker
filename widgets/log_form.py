from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDateEdit, QComboBox, QLineEdit, QSpinBox, QTextEdit,
    QLabel, QPushButton, QMessageBox, QCompleter,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
import json

from db import ENUMS
import repo

# form display name, default activity, and relevant metric fields for each medium type
MEDIUM_DETAILS = {
    "anime": {
        "display_name": "Anime",
        "default_act": "listening",
        "fields": {"episode_count", "episode_name", "volume"}
    },
    "drama": {
        "display_name": "Drama",
        "default_act": "listening",
        "fields": {"episode_count", "episode_name", "volume"},
    },
    "light_novel": {
        "display_name": "Light Novel",
        "default_act": "reading",
        "fields": {"character_count", "volume", "chapter", "reading_direction"}
    },
    "visual_novel": {
        "display_name": "Visual Novel",
        "default_act": "both",
        "fields": {"character_count", "volume", "chapter", "reading_direction"},
    },
    "novel": {
        "display_name": "Novel",
        "default_act": "reading",
        "fields": {"character_count", "volume", "chapter", "reading_direction"},
    },
    "book": {
        "display_name": "Book",
        "default_act": "reading",
        "fields": {"character_count", "volume", "chapter", "reading_direction"},
    },
    "manga": {
        "display_name": "Manga",
        "default_act": "reading",
        "fields": {"page_count", "character_count", "volume", "chapter"},
    },
    "game": {
        "display_name": "Game",
        "default_act": "both",
        "fields": {"character_count"},
    },
    "podcast": {
        "display_name": "Podcast",
        "default_act": "listening",
        "fields": {"episode_count", "episode_name"},
    },
    "audiobook": {
        "display_name": "Audiobook",
        "default_act": "listening",
        "fields": {"volume", "chapter"},
    },
    "youtube": {
        "display_name": "YouTube",
        "default_act": "listening",
        "fields": {"urls"},
    },
}


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
        self._connect_signals()
        self._update_default_activity()
        self._update_field_visibility()
        self._refresh_completer()

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
        form_layout.addRow("Date:", self.date_edit)

        # medium type dropdown
        self.medium_combo = QComboBox()
        for mt in ENUMS["MEDIUM_TYPES"]:
            self.medium_combo.addItem(MEDIUM_DETAILS[mt].get("display_name", mt), userData=mt)
        form_layout.addRow("Medium:", self.medium_combo)

        # title - text field with auto-complete
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Start typing to search titles...")
        # !TODO! auto-complete
        self.title_completer = QCompleter()
        self.title_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.title_completer.setFilterMode(Qt.MatchFlag.MatchContains)

        self.title_edit.setCompleter(self.title_completer)
        form_layout.addRow("Title:", self.title_edit)

        # activity type
        self.activity_combo = QComboBox()
        for at in ENUMS["ACTIVITY_TYPES"]:
            self.activity_combo.addItem(at.capitalize(), userData=at)
        form_layout.addRow("Activity:", self.activity_combo)

        # duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 1440)  # 24hrs
        self.duration_spin.setSuffix(" min")
        form_layout.addRow("Duration:", self.duration_spin)

        # -- Conditional metric fields --

        # character count
        self.char_spin = QSpinBox()
        self.char_spin.setRange(0, 5_000_000)
        self.char_spin.setSpecialValueText("-")

        self._char_label = QLabel("Characters:")
        form_layout.addRow(self._char_label, self.char_spin)

        # page count
        self.page_spin = QSpinBox()
        self.page_spin.setRange(0, 14400)  # 24h * 60m * 600pg
        self.page_spin.setSpecialValueText("-")

        self._page_label = QLabel("Pages:")
        form_layout.addRow(self._page_label, self.page_spin)

        # episode count
        self.episode_spin = QSpinBox()
        self.episode_spin.setRange(0, 200)
        self.episode_spin.setSpecialValueText("-")

        self._episode_label = QLabel("Episodes:")
        form_layout.addRow(self._episode_label, self.episode_spin)

        # reading direction
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("-", userData=None)
        self.direction_combo.addItem("Horizontal", userData="horizontal")
        self.direction_combo.addItem("Vertical", userData="vertical")

        self._dir_label = QLabel("Reading Direction:")
        form_layout.addRow(self._dir_label, self.direction_combo)

        # Details
        self.volume_edit = QLineEdit()
        self.volume_edit.setPlaceholderText("e.g. Vol. 3, Season 2")
        self._vol_label = QLabel("Volume:")
        form_layout.addRow(self._vol_label, self.volume_edit)

        self.chapter_edit = QLineEdit()
        self.chapter_edit.setPlaceholderText("e.g. Ch. 12, 1-1, Ch. 46-54")
        self._chap_label = QLabel("Chapter:")
        form_layout.addRow(self._chap_label, self.chapter_edit)
        # !! might remove this field
        self.ep_name_edit = QLineEdit()
        self.ep_name_edit.setPlaceholderText("e.g. ep.5, Episode Title")
        self._ep_name_label = QLabel("Episode Name:")
        form_layout.addRow(self._ep_name_label, self.ep_name_edit)

        # URLS
        self.urls_edit = QTextEdit()
        self.urls_edit.setPlaceholderText("One URL per line")
        self.urls_edit.setMaximumHeight(60)
        self._urls_label = QLabel("URLS:")
        form_layout.addRow(self._urls_label, self.urls_edit)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Additional comments...")
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow("Notes:", self.notes_edit)

        main_layout.addWidget(form_group)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()

        # log, log+new, clear
        self.log_btn = QPushButton("Log Session")
        self.log_btn.setDefault(True)  # !TODO! user-preference

        self.log_new_btn = QPushButton("Log && New")
        self.log_new_btn.setToolTip("Log this session and clear the form for a new session")

        self.clear_btn = QPushButton("Clear")

        btn_layout.addStretch()  # buttons container to  right
        btn_layout.addWidget(self.log_btn)
        btn_layout.addWidget(self.log_new_btn)
        btn_layout.addWidget(self.clear_btn)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

        self._conditional_fields = [
            ("character_count", self._char_label, self.char_spin),
            ("page_count", self._page_label, self.page_spin),
            ("episode_count", self._episode_label, self.episode_spin),
            ("reading_direction", self._dir_label, self.direction_combo),
            ("volume", self._vol_label, self.volume_edit),
            ("chapter", self._chap_label, self.chapter_edit),
            ("episode_name", self._ep_name_label, self.ep_name_edit),
            ("urls", self._urls_label, self.urls_edit),
        ]

    def _connect_signals(self):  # !TODO!
        # Medium type changes --> show/hide relevant fields
        self.medium_combo.currentIndexChanged.connect(self._update_field_visibility)
        self.medium_combo.currentIndexChanged.connect(self._update_default_activity)
        # self.medium_combo.currentIndexChanged.connect(self._refresh_completer)

        # Stopwatch stopped --> populate duration field

        # Button actions
        self.log_btn.clicked.connect(self._submit)
        self.log_new_btn.clicked.connect(self._submit_and_clear)
        self.clear_btn.clicked.connect(self._clear_form)

    def _update_field_visibility(self):
        """Show/hide  metric fields based on selected medium type."""
        medium = self.medium_combo.currentData()
        visible = MEDIUM_DETAILS[medium].get("fields", set())

        for key, label, field in self._conditional_fields:
            show_field = key in visible
            label.setVisible(show_field)
            field.setVisible(show_field)

    def _update_default_activity(self):
        """Set a relevant default activity type based on selected medium type."""
        medium = self.medium_combo.currentData()
        default_activity = MEDIUM_DETAILS[medium].get("default_act", "reading")

        idx = self.activity_combo.findData(default_activity)
        if idx >= 0:
            self.activity_combo.setCurrentIndex(idx)

    def _refresh_completer(self):  # !TODO!
        """Update the title autocomplete list based on selected medium type."""
        pass

    def _collect_form_data(self):
        """Validate form fields. Returns dict or None if invalid."""
        medium = self.medium_combo.currentData()
        title_text = self.title_edit.text().strip()
        if not title_text:
            QMessageBox.warning(self, "Missing Field", "Please enter a title.")
            return None

        duration = self.duration_spin.value()
        if duration == 0:
            QMessageBox.warning(self, "Missing Field", "Please enter a duration for the session.")
            return None

        # get/create title entry in database
        title_id = repo.get_or_create_title(title_text, medium)  # !TODO!

        # Parse URLS
        urls_text = self.urls_edit.toPlainText().strip()
        urls_json = None
        if urls_text:
            urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
            if urls:
                urls_json = json.dumps(urls)

        return {
            "date_str": self.date_edit.date().toString("yyyy-MM-dd"),
            "title_id": title_id,
            "title_text": title_text,
            "medium_type": medium,
            "activity_type": self.activity_combo.currentData(),
            "duration_minutes": duration,
            "character_count": self.char_spin.value() or None,
            "page_count": self.page_spin.value() or None,
            "episode_count": self.episode_spin.value() or None,
            "reading_direction": self.direction_combo.currentData() or None,
            "volume": self.volume_edit.text().strip() or None,
            "chapter": self.chapter_edit.text().strip() or None,
            "episode_name": self.ep_name_edit.text().strip() or None,
            "urls_json": urls_json,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }

    def _submit(self):
        """Validate and save the session."""
        data = self._collect_form_data()
        if data is None:
            return
        # !! insert session into db + signal
        print(f"SUBMITTING NEW SESSION: {data}")
        repo.add_immersion_session(**data)  # !TODO!
        self.sig_session_logged.emit()

        self.statusbar_message("Session logged!")

    def _submit_and_clear(self):
        """Save, then clear form for next entry."""
        data = self._collect_form_data()
        if data is None:
            return
        # !! insert session into db + signal
        print(f"SUBMITTING NEW SESSION: {data}")
        repo.add_immersion_session(**data)  # !TODO!
        self.sig_session_logged.emit()

        self.statusbar_message("Session logged!")
        self._clear_form(keep_date=True, keep_medium=True)
        self.title_edit.setFocus()

    def _clear_form(self, keep_date=False, keep_medium=False):
        """Reset form. Optionally preserve date and medium for consecutive logs."""
        print("CLEARING FORM")
        if not keep_date:
            self.date_edit.setDate(QDate.currentDate())
        if not keep_medium:
            self.medium_combo.setCurrentIndex(0)
        self.title_edit.clear()
        self.duration_spin.setValue(0)
        self.char_spin.clear()
        self.page_spin.clear()
        self.episode_spin.clear()
        self.direction_combo.clear()
        self.volume_edit.clear()
        self.chapter_edit.clear()
        self.ep_name_edit.clear()
        self.urls_edit.clear()
        self.notes_edit.clear()

    def statusbar_message(self, msg: str):
        """Show a message on main window's status bar."""
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(msg, 3000)
