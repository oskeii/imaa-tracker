"""Goal and milestone dialogs"""
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit,
    QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QDate

from imaa_tracker.core.constants import ENUMS
# GoalDialog: guided creation/edit. Fields adapt based on goal_type.
#   - Editing an existing goal locks fields that would corrupt history
#   (metric, period, filters, goal_type) — only name/target/notes/window are freely editable.

# MilestoneDialog: simple title + date + notes for manually logged achievements.

class GoalDialog(QDialog):
    """Goal creation/edit dialogue."""

    def __init__(self, existing: dict = None, parent=None):
        super().__init__(parent)
        self.existing = existing

        self.setWindowTitle("Edit Goal" if existing else "New Goal")
        self.setMinimumWidth(480)

        self._build_ui()
        self._prefill(goal=self.existing)
        self._update_conditional_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Notice label on immutable fields
        self._lock_notice = QLabel(
            "Metric, period, and filter fields are locked after creation "
            "to preserve acurracy of recorded logs. "
            "Delete and recreate the goal if you must change them."
        )
        self._lock_notice.setWordWrap(True)
        self._lock_notice.setStyleSheet(
            "font-size: 10px; color: palette(mid); margin-top: 8px;"
        )
        self._lock_notice.setVisible(False)
        layout.addWidget(self._lock_notice)

        form = self._build_form()
        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _build_form(self) -> QFormLayout:
        form = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Daily reading goal")
        form.addRow("Name:", self._name_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItem("Recurring", "recurring")
        self._type_combo.addItem("Lifetime", "lifetime")
        self._type_combo.currentIndexChanged.connect(self._update_conditional_fields)
        form.addRow("Type:", self._type_combo)

        self._period_combo = QComboBox()
        for p in ENUMS["GOAL_PERIODS"]:
            self._period_combo.addItem(p.capitalize(), p)
        self._period_label = QLabel("Period:")
        form.addRow(self._period_label, self._period_combo)

        self._metric_combo = QComboBox()
        for m in ENUMS["GOAL_METRICS"]:
            self._metric_combo.addItem(m.replace("_", " ").title(), m)
        form.addRow("Metric:", self._metric_combo)

        self._target_spin = QSpinBox()
        self._target_spin.setRange(1, 999_999_999)
        self._target_spin.setValue(1)
        self._target_spin.setGroupSeparatorShown(True)
        form.addRow("Target value:", self._target_spin)

        # Optional filters
        self._medium_combo = QComboBox()
        self._medium_combo.addItem("All media", None)
        for m in ENUMS["MEDIUM_TYPES"]:
            self._medium_combo.addItem(m.replace("_", " ").title(), m)
        form.addRow("Medium:", self._medium_combo)

        self._activity_combo = QComboBox()
        self._activity_combo.addItem("All activities", None)
        for a in ENUMS["ACTIVITY_TYPES"]:
            self._activity_combo.addItem(a.capitalize(), a)
        form.addRow("Activity:", self._activity_combo)

        # Health window (for recurring)
        self._health_spin = QSpinBox()
        self._health_spin.setRange(7, 365)
        self._health_spin.setValue(60)
        self._health_spin.setSuffix(" days")
        self._health_label = QLabel("Health window:")
        form.addRow(self._health_label, self._health_spin)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(60)
        form.addRow("Notes:", self._notes_edit)
        return(form)


    def _update_conditional_fields(self):
        is_recurring = self._type_combo.currentData() == "recurring"
        self._period_label.setVisible(is_recurring)
        self._period_combo.setVisible(is_recurring)
        self._health_label.setVisible(is_recurring)
        self._health_spin.setVisible(is_recurring)

    def _prefill(self, goal: dict = None):
        if not goal:
            return

        self._name_edit.setText(goal["name"])

        combos = [
            (self._type_combo, "goal_type"),
            (self._period_combo, "period"),
            (self._metric_combo, "metric"),
            (self._medium_combo, "medium_type"),
            (self._activity_combo, "activity_type"),
        ]
        
        for c, k in combos:
            idx = c.findData(goal[k])
            if idx >= 0:
                c.setCurrentIndex(idx)

        self._target_spin.setValue(goal["target_value"])
        self._health_spin.setValue(goal.get("health_window_days", 60))
        self._notes_edit.setPlainText(goal.get("notes", ""))

        # Lock immutable fields
        for c, k in combos:
            c.setEnabled(False)
        self._lock_notice.setVisible(True)


    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing", "Please enter a name for your goal.")
            return

        goal_type = self._type_combo.currentData()
        payload = {
            "name": name,
            "goal_type": goal_type,
            "metric": self._metric_combo.currentData(),
            "target_value": self._target_spin.value(),
            "period": self._period_combo.currentData() if goal_type=="recurring" else None,
            "medium_type": self._medium_combo.currentData(),
            "activity_type": self._activity_combo.currentData(),
            "health_window_days": (
                self._health_spin.value() if goal_type=="recurring" else 60
            ),
            "notes": self._notes_edit.toPlainText().strip() or None,
        }

        from imaa_tracker.core import repo
        if self.existing:
            allowed = {"name", "target_value", "health_window_days", "notes"}
            updates = {k: v for k, v in payload.items() if k in allowed}

            if updates.get("target_value") != self.existing.get("target_value"):
                confirm = QMessageBox.question(
                    self, "Change target?",
                    f"Change target from {self.existing['target_value']:,} to {updates['target_value']:,}?\n\n"
                    "Past goal_log entries will keep their original target, so your streak history stays accurate. "
                    "The current period will be re-evaluated against the new target.",
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return
            repo.update_goal(self.existing["id"], **updates)
        else:
            repo.add_goal(**payload)

        self.accept()



class MilestoneDialog(QDialog):
    """Milestone create/edit dialogue"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Milestone")
        self.setMinimumWidth(400)
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. Finished my first light novel")
        form.addRow("Title:", self._title_edit)

        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.currentDate())
        form.addRow("Date:", self._date_edit)

        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", self._notes_edit)
        
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)



    def _on_save(self):
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing", "Please enter a title.")
            return
        
        from imaa_tracker.core import repo
        repo.add_milestone(
            title,
            date_str=self._date_edit.date().toString("yyyy-MM-dd"),
            notes=self._notes_edit.toPlainText().strip() or None
        )
        self.accept()


