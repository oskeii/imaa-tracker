"""Goals tab w/subtabs: Active, Accomplishments"""

# Active: goal cards, sorted pinned-first then by period. + New Goal button
# Accomplishments: milestone timeline. + New Milestone button
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QMessageBox,
    QFrame, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .goal_dialogs import GoalDialog, MilestoneDialog
from .goal_cards import RecurringGoalCard, LifetimeGoalCard
from imaa_tracker.core.utils.formatting import format_metric_value


class GoalsTab(QWidget):

    sig_goals_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_active_subtab(), "Active")
        self._tabs.addTab(self._build_accomplishments_subtab(), "Accomplishments")
        layout.addWidget(self._tabs)

    # --- Active subtab ---
    def _build_active_subtab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        header = QHBoxLayout()
        header.addStretch()
        new_btn = QPushButton("+ New Goal")
        new_btn.clicked.connect(self._new_goal)
        header.addWidget(new_btn)
        layout.addLayout(header)

        self._active_scroll = QScrollArea()
        self._active_scroll.setWidgetResizable(True)
        self._active_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._active_container = QWidget()
        self._active_layout = QVBoxLayout(self._active_container)
        self._active_layout.setSpacing(12)
        self._active_layout.addStretch()

        self._active_scroll.setWidget(self._active_container)
        layout.addWidget(self._active_scroll)
        return w

    def _refresh_active(self):
        while self._active_layout.count() > 1:
            item = self._active_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from imaa_tracker.core.services import goals_service as gs
        goals = gs.get_active_goals_with_progress()

        if not goals:
            empty = QLabel("No active goals. Click '+ New Goal' to create one.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: palette(mid); padding: 40px;")
            self._active_layout.insertWidget(0, empty)
            return
        
        for g in goals:
            if g["goal_type"] == "recurring":
                card = RecurringGoalCard(g)
            else:
                card = LifetimeGoalCard(g)
            card.sig_pin_toggled.connect(self._on_pin_toggled)
            card.sig_show_on_log_toggled.connect(self._on_show_on_log_toggled)
            card.sig_edit_requested.connect(self._on_edit_requested)
            card.sig_deactivate_requested.connect(self._on_deactivate_requested)
            self._active_layout.insertWidget(self._active_layout.count() -1, card)

    # --- Accomplishments subtab ---
    def _build_accomplishments_subtab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        header = QHBoxLayout()
        header.addStretch()
        new_btn = QPushButton("+ New Milestone")
        new_btn.clicked.connect(self._new_milestone)
        header.addWidget(new_btn)
        layout.addLayout(header)

        self._acc_scroll = QScrollArea()
        self._acc_scroll.setWidgetResizable(True)
        # self._acc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._acc_container = QWidget()
        self._acc_layout = QVBoxLayout(self._acc_container)
        self._acc_layout.setSpacing(6)
        self._acc_layout.addStretch()

        self._acc_scroll.setWidget(self._acc_container)
        layout.addWidget(self._acc_scroll)
        return w

    def _refresh_accomplishments(self):
        while self._acc_layout.count() > 1:
            item = self._acc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        from imaa_tracker.core import repo
        milestones = repo.get_milestones(limit=100)

        if not milestones:
            empty = QLabel("Looks like you haven't hit any milestones yet. 🤔")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: palette(mid); padding: 40px;")
            self._acc_layout.insertWidget(0, empty)
            return

        for m in milestones:
            row = MilestoneRow(m)
            self._acc_layout.insertWidget(self._acc_layout.count() -1, row)

    # --- Refresh ---
    def refresh(self):
        self._refresh_active()
        self._refresh_accomplishments()

    # --- Actions ---
    def _new_goal(self):
        dlg = GoalDialog(parent=self)
        if dlg.exec():
            self.refresh()
        self.sig_goals_changed.emit()


    def _new_milestone(self):
        dlg = MilestoneDialog(parent=self)
        if dlg.exec():
            self._refresh_accomplishments()

    def _on_pin_toggled(self, goal_id: int):
        from imaa_tracker.core import repo
        repo.toggle_pinned(goal_id)
        self._refresh_active()
        self.sig_goals_changed.emit()

    def _on_show_on_log_toggled(self, goal_id: int):
        from imaa_tracker.core import repo
        repo.toggle_show_on_log(goal_id)
        self._refresh_active()
        self.sig_goals_changed.emit()

    def _on_edit_requested(self, goal_id: int):
        from imaa_tracker.core import repo
        goal = repo.get_goal_by_id(goal_id)
        if goal:
            dlg = GoalDialog(existing=goal, parent=self)
            if dlg.exec():
                self.refresh()
        self.sig_goals_changed.emit()

    def _on_deactivate_requested(self, goal_id: int):
        confirm = QMessageBox.question(
            self,
            "Deactivate goal?",
            "This goal won't appear on the Active tab anymore, "
            "and will no longer be evaluated when you log sessions. "
            "You can find achieved goals under Accomplishments.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            from imaa_tracker.core import repo
            repo.update_goal(goal_id, is_active=0)
            self.refresh()
        self.sig_goals_changed.emit()


class MilestoneRow(QFrame):
    """Single-row display for milestones"""

    def __init__(self, milestone: dict, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        date_label = QLabel(milestone["date"])
        date_label.setStyleSheet("font-size: 10px; color: palette(mid);")
        date_label.setFixedWidth(90)
        layout.addWidget(date_label)

        title_label = QLabel(milestone["title"])
        title_label.setStyleSheet("font-size: 12px;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if milestone.get("metric") and milestone.get("metric_value"):
            info = QLabel(format_metric_value(
                milestone["metric_value"], milestone["metric"]
            ))
            info.setStyleSheet("font-size: 10px; color: palette(mid);")
            layout.addWidget(info)
