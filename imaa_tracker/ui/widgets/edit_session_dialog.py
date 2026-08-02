from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDateEdit, QComboBox, QLineEdit, QSpinBox, QTextEdit,
    QLabel, QPushButton, QMessageBox, QCheckBox, QCompleter,
    QDialogButtonBox, QWidget,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QStringListModel
import json

from .log_form import MEDIUM_DETAILS
from constants import ENUMS
import repo

# Fields that are universal (always editable, even across mixed mediums)
UNIVERSAL_FIELDS = {
    "date", "activity_type", "duration_minutes", "notes"
}


# Sentinel class: "selected sessions have differing values for this field"
class _Mixed:
    def __repr__(self): return "<MIXED>"


MIXED = _Mixed()


# !TODO! return focus to parent window
# !TODO! refresh dashboard
class EditSessionDialog(QDialog):
    """Modal dialog for editing sessions"""
    def __init__(self, sessions: list[dict], parent=None):
        super().__init__(parent)
        if not sessions:
            raise ValueError("EditSessionDialog requires at least one session")

        self.sessions = sessions
        self.is_batch = len(sessions) > 1

        self._mediums = {s["medium_type"] for s in sessions}
        self.is_mixed_medium = self.is_batch and len(self._mediums) > 1

        self._field_widgets: dict[str, QWidget] = {}
        self._field_labels: dict[str, QLabel] = {}
        self._field_checkboxes: dict[str, QCheckBox] = {}

        self.setWindowTitle(
            "Edit Session" if not self.is_batch
            else f"Edit {len(sessions)} Sessions"
        )
        self.setMinimumWidth(480)
        self._build_ui()
        self._connect_signals()
        self._populate_fields()
        self._update_field_visibility()
        self._update_default_activity()
        self._refresh_completer()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Edit mode indicator/hint
        if self.is_batch:
            hint = QLabel(
                f"Editing {len(self.sessions)} sessions."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet("color: gray; padding: 4px;")
            main_layout.addWidget(hint)

            if self.is_mixed_medium:
                warn = QLabel(
                    f"⚠ Mixed mediums selected ({', '.join(sorted(self._mediums))}). "
                    f" Medium and title cannot be batch-edited."
                )
                warn.setWordWrap(True)
                warn.setStyleSheet("color: #c25c00; padding: 4px;")
                main_layout.addWidget(warn)

        # --- Form group ---
        form_group = QGroupBox("Session" if not self.is_batch else "Fields to apply")
        form_layout = QFormLayout(form_group)

        # date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self._add_field("date", "Date:", self.date_edit, form_layout)

        # duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 1440)
        self.duration_spin.setSuffix(" min")
        self._add_field("duration_minutes", "Duration:", self.duration_spin, form_layout)

        # medium
        self.medium_combo = QComboBox()
        for mt in ENUMS["MEDIUM_TYPES"]:
            self.medium_combo.addItem(MEDIUM_DETAILS[mt].get("display_name", mt), userData=mt)
        self._add_field("medium_type", "Medium:", self.medium_combo, form_layout)

        # title w/ autocomplete
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Start typing to search titles...")
        self.title_completer = QCompleter()
        self.title_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.title_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.title_edit.setCompleter(self.title_completer)
        self.title_edit.focusInEvent = self._on_title_focus
        self._add_field("title_text", "Title:", self.title_edit, form_layout)

        # activity
        self.activity_combo = QComboBox()
        for at in ENUMS["ACTIVITY_TYPES"]:
            self.activity_combo.addItem(at.capitalize(), userData=at)
        self._add_field("activity_type", "Activity:", self.activity_combo, form_layout)

        # character count
        self.char_spin = QSpinBox()
        self.char_spin.setRange(0, 5_000_000)
        self.char_spin.setSpecialValueText("-")
        self._add_field("character_count", "Characters:", self.char_spin, form_layout)
        # page_count
        self.page_spin = QSpinBox()
        self.page_spin.setRange(0, 14400)
        self.page_spin.setSpecialValueText("-")
        self._add_field("page_count", "Pages:", self.page_spin, form_layout)
        # episode_count
        self.episode_spin = QSpinBox()
        self.episode_spin.setRange(0, 200)
        self.episode_spin.setSpecialValueText("-")
        self._add_field("episode_count", "Episodes:", self.episode_spin, form_layout)

        # reading_direction
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("-", userData=None)
        self.direction_combo.addItem("Horizontal", userData="horizontal")
        self.direction_combo.addItem("Vertical", userData="vertical")
        self._add_field("reading_direction", "Reading Direction:", self.direction_combo, form_layout)

        # volume
        self.volume_edit = QLineEdit()
        self.volume_edit.setPlaceholderText("e.g. Vol. 3")
        self._add_field("volume", "Volume:", self.volume_edit, form_layout)
        # chapter
        self.chapter_edit = QLineEdit()
        self.chapter_edit.setPlaceholderText("e.g. Ch. 12, 1-1")
        self._add_field("chapter", "Chapter:", self.chapter_edit, form_layout)
        # episode_name
        self.ep_name_edit = QLineEdit()
        self.ep_name_edit.setPlaceholderText("e.g. ep.5")
        self._add_field("episode_name", "Episode Name:", self.ep_name_edit, form_layout)
        # urls
        self.urls_edit = QTextEdit()
        self.urls_edit.setPlaceholderText("One URL per line")
        self.urls_edit.setMaximumHeight(60)
        self._add_field("urls", "URLs:", self.urls_edit, form_layout)
        # notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Additional comments...")
        self.notes_edit.setMaximumHeight(60)
        self._add_field("notes", "Notes:", self.notes_edit, form_layout)

        main_layout.addWidget(form_group)

        # --- Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _add_field(self, key: str, label_text: str, widget: QWidget, form_layout: QFormLayout):
        """
        Add a labeled field to the form layout.
        Prefixes label with an "Apply" checkbox in batch mode
        """
        self._field_widgets[key] = widget
        label = QLabel(label_text)
        self._field_labels[key] = label

        if self.is_batch:
            # Wrap label + checkbox in HBox
            checkbox = QCheckBox()
            checkbox.setToolTip("Apply this field to all selected sessions")
            self._field_checkboxes[key] = checkbox

            label_widget = QWidget()
            hbox = QHBoxLayout(label_widget)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addWidget(checkbox)
            hbox.addWidget(label)
            hbox.addStretch()

            form_layout.addRow(label_widget, widget)
        else:
            form_layout.addRow(label, widget)

    def _connect_signals(self):
        self.medium_combo.currentIndexChanged.connect(self._update_field_visibility)
        self.medium_combo.currentIndexChanged.connect(self._update_default_activity)
        self.medium_combo.currentIndexChanged.connect(self._refresh_completer)

        if self.is_batch:
            for k, w in self._field_widgets.items():
                widget_type = type(w)
                if widget_type is QDateEdit:
                    self._wire_auto_check(w, k, w.dateChanged)
                elif widget_type is QSpinBox:
                    self._wire_auto_check(w, k, w.valueChanged)
                elif widget_type is QComboBox:
                    self._wire_auto_check(w, k, w.currentIndexChanged)
                elif widget_type in (QTextEdit, QLineEdit):
                    self._wire_auto_check(w, k, w.textChanged)

    def _wire_auto_check(self, widget, key, signal):
        """Tick the Apply checkbox when widget value is changed."""
        cb = self._field_checkboxes.get(key)
        if cb is None:
            return
        # Only auto-check, not auto-uncheck
        signal.connect(lambda *_: cb.setChecked(True))

    # ========== POPULATE FIELDS ==========
    def _get_common_value(self, key: str):
        """Return the shared value across all selected sessions, or MIXED."""
        db_key = "urls_json" if key == "urls" else key
        raw_value = self.sessions[0].get(db_key)
        first_value = self._urls_json_to_text(raw_value) if db_key == "urls_json" else raw_value

        if not self.is_batch:
            return first_value

        for s in self.sessions[1:]:
            v = self._urls_json_to_text(s.get(db_key)) if db_key == "urls_json" else s.get(db_key)
            if v != first_value:
                return MIXED
        return first_value

    @staticmethod
    def _urls_json_to_text(urls_json: str) -> str:
        if not urls_json:
            return ""
        try:
            return "/n".join(json.loads(urls_json))
        except (json.JSONDecodeError, TypeError):
            return ""

    def _populate_fields(self):
        """
        Fill widgets with current values.
        Batch mode: Blocks widget signals during field population
        """
        for w in self._field_widgets.values():
            w.blockSignals(True)

        try:
            self._do_populate()
        finally:
            for w in self._field_widgets.values():
                w.blockSignals(False)
        self._refresh_completer()  # medium_combo signals are suppressed during populate

    def _do_populate(self):
        """Field population logic; to be called inside blockSignals window"""
        for k, w in self._field_widgets.items():
            v = self._get_common_value(k)
            widget_type = type(w)

            if widget_type is QDateEdit:
                if v not in (None, MIXED):
                    w.setDate(QDate.fromString(v, Qt.DateFormat.ISODate))
                else:
                    w.setDate(QDate.currentDate())
                    if v is MIXED:
                        w.setSpecialValueText("(mixed)")
            elif widget_type is QSpinBox:
                if v not in (None, MIXED):
                    w.setValue(v or 0)
            elif widget_type is QComboBox:
                if v not in (None, MIXED):
                    idx = w.findData(v)
                    if idx >= 0:
                        w.setCurrentIndex(idx)
                if k == "medium_type" and self.is_mixed_medium:
                    self._lock_field("medium_type", "(mixed mediums - locked)")
                    self._lock_field("title_text", "(cannot batch-edit across mixed mediums)")
            elif widget_type is QTextEdit:
                if v not in (None, MIXED):
                    w.setPlainText(v or "")
                elif v is MIXED:
                    w.setPlaceholderText("(mixed)")
            elif widget_type is QLineEdit:
                if v not in (None, MIXED):
                    w.setText(v or "")
                elif v is MIXED:
                    w.setPlaceholderText("(mixed)")

    def _lock_field(self, key: str, reason: str):
        """Disable a field and its checkbox (for batch w/mixed-medium)"""
        widget = self._field_widgets.get(key)
        cb = self._field_checkboxes.get(key)
        for w in (widget, cb):
            if w:
                w.setEnabled(False)
                w.setToolTip(reason)

    def _update_field_visibility(self):
        """Show/hide  metric fields based on selected medium type."""
        # Batch mode with mixed medium: user may need to clear a value across all sessions
        # !!
        if self.is_mixed_medium:
            return

        medium = self.medium_combo.currentData()
        if not medium:
            return
        visible = MEDIUM_DETAILS[medium].get("fields", set())

        conditional_keys = [
            "character_count", "page_count", "episode_count",
            "reading_direction", "volume", "chapter",
            "episode_name", "urls",
        ]
        for key in conditional_keys:
            show_field = key in visible
            widget = self._field_widgets.get(key)
            label = self._field_labels.get(key)
            checkbox = self._field_checkboxes.get(key)
            for w in (widget, label, checkbox):
                if w is not None:
                    w.setVisible(show_field)
            # Batch mode: hide parent label-widget container
            if checkbox is not None:
                parent_container = checkbox.parentWidget()
                if parent_container is not None:
                    parent_container.setVisible(show_field)

    def _update_default_activity(self):
        """Set a relevant default activity type based on selected medium type."""
        medium = self.medium_combo.currentData()
        default_activity = MEDIUM_DETAILS[medium].get("default_act", "reading")

        idx = self.activity_combo.findData(default_activity)
        if idx >= 0:
            self.activity_combo.setCurrentIndex(idx)

    def _refresh_completer(self):
        """Update the title autocomplete list based on selected medium type."""
        medium = self.medium_combo.currentData()
        titles = repo.get_all_titles(medium_type=medium)
        names = [t["name"] for t in titles]
        self.title_completer.setModel(QStringListModel(names))

    def _on_title_focus(self, event):
        QLineEdit.focusInEvent(self.title_edit, event)
        self.title_completer.setCompletionPrefix(self.title_edit.text() or "")
        self.title_completer.complete()

    # ========== SAVE ==========
    def _collect_field_value(self, key: str):
        """Returns current value of a field, normalized to the DB column type"""
        field_widget = self._field_widgets.get(key)
        widget_type = type(field_widget)
        if widget_type is QDateEdit:
            return field_widget.date().toString("yyyy-MM-dd")
        elif widget_type is QSpinBox:
            return field_widget.value() or None
        elif widget_type is QComboBox:
            return field_widget.currentData()
        elif widget_type is QLineEdit:
            return field_widget.text().strip() or None
        elif widget_type is QTextEdit and key != "urls":
            return field_widget.toPlainText().strip() or None

        elif key == "urls":
            # collect as urls_json
            text = field_widget.toPlainText().strip()
            if not text:
                return None
            urls = [url.strip() for url in text.splitlines() if url.strip()]
            return json.dumps(urls) if urls else None

        return None

    def _collect_changes(self):
        """
        Build the dict of fields to apply.
        Single edit: full overwrite (minus non-visible fields)
        Batch edits: returns only fields where "Apply" checkbox is ticked
        """
        changes = {}
        for k, w in self._field_widgets.items():
            value = None
            if self.is_batch:
                checkbox = self._field_checkboxes.get(k)
                if checkbox is None or not checkbox.isChecked() or not checkbox.isEnabled():
                    continue
            if w.isVisible():  # non-visible fields are None, retaining current value
                value = self._collect_field_value(k)

            db_key = "urls_json" if k == "urls" else k
            changes[db_key] = value
        return changes

    def _on_save(self):
        changes = self._collect_changes()

        if not changes:
            QMessageBox.information(
                self, "No changes",
                "No fields were modified." if not self.is_batch
                else "No fields were marked to apply.",
            )
            return

        if "title_text" in changes.keys() and not changes["title_text"]:
            QMessageBox.warning(self, "Invalid", "Title cannot be empty.")
            return

        if "title_text" in changes.keys() or "medium_type" in changes.keys():
            self._resolve_title_id(changes)

        try:
            if self.is_batch:
                ids = [s["id"] for s in self.sessions]
                print(f"ARGUMENTS: \n\t{ids} \n\t{changes}")
                count = repo.bulk_update_immersion_sessions(ids, **changes)
                self._show_status(f"Updated {count} sessions.")
            else:
                print(f"ARGUMENTS: \n\t{self.sessions[0]} \n\t{changes}")
                repo.update_immersion_session(self.sessions[0]["id"], **changes)
                self._show_status("Session updated.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _resolve_title_id(self, changes: dict):
        if self.is_mixed_medium:
            return
        title_text = changes.get("title_text", self.sessions[0]["title_text"])
        medium = changes.get("medium_type", self.sessions[0]["medium_type"])
        if title_text and medium:
            changes["title_id"] = repo.get_or_create_title(title_text, medium)

    def _show_status(self, msg: str):
        """Show a message on main window's status bar."""
        parent_window = self.parent().window()
        if hasattr(parent_window, "statusBar"):
            parent_window.statusBar().showMessage(msg, 3000)
