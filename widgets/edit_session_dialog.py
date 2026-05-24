from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDateEdit, QComboBox, QLineEdit, QSpinBox, QTextEdit,
    QLabel, QPushButton, QMessageBox, QCheckBox, QCompleter,
    QDialogButtonBox, QWidget,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QStringListModel
import json

from .log_form import MEDIUM_DETAILS
from db import ENUMS
import repo


class EditSessionDialog(QDialog):
    """Modal dialog for editing sessions"""
    def __init__(self, sessions: list[dict], parent=None):
        super().__init__(parent)
        if not sessions:
            raise ValueError("EditSessionDialog requires at least one session")

        self.sessions = sessions
        self.is_batch = len(sessions) > 1

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
        self._refresh_completer()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Edit mode indicator/hint
        if self.is_batch:
            hint = QLabel(
                f"Editing {len(self.sessions)} sessions."
            )
            # hint.setWordWrap(True)
            hint.setStyleSheet("color: gray; padding: 4px;")
            main_layout.addWidget(hint)

        # --- Form group ---
        form_group = QGroupBox("Session")
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
            checkbox = QCheckBox()
            checkbox.setToolTip("Apply this field to all selected sessions")
            self._field_checkboxes[key] = checkbox

            label_widget = QWidget()
            hbox = QHBoxLayout(label_widget)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addWidget(checkbox)
            hbox.addWidget(label)
            hbox.addStretch()

            # Disable field until checkbox ticked
            widget.setEnabled(False)
            checkbox.toggled.connect(widget.setEnabled)

            form_layout.addRow(label_widget, widget)
        else:
            form_layout.addRow(label, widget)

    def _connect_signals(self):
        self.medium_combo.currentIndexChanged.connect(self._update_field_visibility)
        self.medium_combo.currentIndexChanged.connect(self._refresh_completer)

    def _populate_fields(self):
        """
        Fill widgets with current values.
        Batch mode: Blocks widget signals during field population
        """
        for w in self._field_widgets.values():
            w.blockSignals(True)

        try:
            for k, w in self._field_widgets.items():
                values = list(s.get(k) for s in self.sessions)
                if not values[0]:
                    continue

                v = values[0]
                if type(w) is QDateEdit:
                    w.setDate(QDate.fromString(v, Qt.DateFormat.ISODate))
                elif type(w) is QSpinBox:
                    w.setValue(v or 0)
                elif type(w) is QComboBox:
                    idx = w.findData(v)
                    if idx >= 0:
                        w.setCurrentIndex(idx)
                elif type(w) is QTextEdit:
                    w.setPlainText(v or "")
                elif type(w) is QLineEdit:
                    w.setText(v or "")
                else:
                    continue

        finally:
            for w in self._field_widgets.values():
                w.blockSignals(False)

    def _update_field_visibility(self):
        """Show/hide  metric fields based on selected medium type."""
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

    def _collect_field_value(self, key: str):
        """Returns current value of a field, normalized to the DB column type"""
        field_widget = self._field_widgets.get(key)
        if type(field_widget) is QDateEdit:
            return field_widget.date().toString("yyyy-MM-dd")
        elif type(field_widget) is QSpinBox:
            return field_widget.value() or None
        elif type(field_widget) is QComboBox:
            return field_widget.currentData()
        elif type(field_widget) is QLineEdit:
            return field_widget.text().strip() or None
        elif type(field_widget) is QTextEdit and key != "urls":
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
        Single edit: full overwrite
        Batch edits: returns only fields where "Apply" checkbox is ticked
        """
        changes = {}

        for k, w in self._field_widgets.items():
            if self.is_batch:
                return changes
                # checkbox = self._field_checkboxes.get(k)
                # if checkbox is None or not checkbox.isChecked() or not checkbox.isEnabled():
                #     continue
            if not w.isVisible():
                value = self.sessions[0].get(k)
            else:
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

        if "title_text" in changes.keys() or "medium_title" in changes.keys():
            self._resolve_title_id(changes)

        try:
            if self.is_batch:
                raise NotImplementedError
                # ids = [s["id"] for s in self.sessions]
                # results = repo.bulk_update_immersion_sessions(ids, **changes)
                # self._show_status(f"Updated {results['count']} sessions.")
            else:
                print(f"ARGUMENTS: \n\t{self.sessions[0]} \n\t{changes}")
                repo.update_immersion_session(self.sessions[0]["id"], **changes)
                self._show_status("Session updated.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _resolve_title_id(self, changes: dict):
        title_text = changes.get("title_text")
        medium = changes.get("medium_type")
        if title_text and medium:
            changes["title_id"] = repo.get_or_create_title(title_text, medium)

    def _show_status(self, msg: str):  # !!
        """Show a message on main window's status bar."""
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(msg, 3000)
