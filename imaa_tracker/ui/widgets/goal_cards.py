"""
Goal card widgets
Variants:
    RecurringGoalCard   - progress bar + habit dot strip + streak/health
    LifetimeGoalCard    - cumulative progress bar w/ numbers

Plus:
    HabitDotStrip       - small colored dots for the last N periods
    format_metric_unit  - shor unit labels for metric values
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

from imaa_tracker.core.utils.formatting import format_metric_unit, format_metric_value

DOT_COLORS = {
    "achieved": "#5AD8A6",
    "missed":   "#E86452",
    "none":     "#DDDDDD",
}


class HabitDotStrip(QWidget):
    """
    Row of small colored dots, one per goal period within the..
    """
    def __init__(self, parent=None):
        super().__init__(parent)


class BaseGoalCard(QFrame):
    """
    Base shell for goal cards. Handles the header (name, badge, action buttons) and filter chips.
    Subclasses implement _build_content()
    """

    sig_pin_toggled = pyqtSignal(int)  # goal_id
    sig_show_on_log_toggled = pyqtSignal(int) 
    sig_edit_requested = pyqtSignal(int)
    sig_deactivate_requested = pyqtSignal(int)

    def __init__(self, goal: dict, parent=None):
        super().__init__(parent)
        self.goal = goal
        self.goal_id = goal["id"]

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMinimumWidth(320)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        self._build_header()
        self._build_filter_chips()
        self._build_content()


    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(4)

        title = QLabel(self.goal["name"])
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()

        # Achieved badge for recently-completed lifetime goals
        if self.goal.get("achieved_at") and not self.goal.get("is_active"):
            badge = QLabel("✓ Achieved")
            badge.setStyleSheet(
                "background: #5AD8A6; color: white; padding: 2px 8px; "
                "border-radius: 4px; font-size: 10px; font-weight: bold;"  
            )
            header.addWidget(badge)

        # Actions
        pin_symbol = "★" if self.goal.get("pinned") else "☆"
        pin_btn = self._make_action_btn(pin_symbol, "Pin/unpin",
            lambda: self.sig_pin_toggled.emit(self.goal_id))
        header.addWidget(pin_btn)

        if self.goal.get("is_active"):
            log_symbol = "◉" if self.goal.get("show_on_log") else "○"
            log_btn = self._make_action_btn(log_symbol, "Show on log tab",
                lambda: self.sig_show_on_log_toggled.emit(self.goal_id))
            header.addWidget(log_btn)
        
        edit_btn = self._make_action_btn("✎", "Edit",
            lambda: self.sig_edit_requested.emit(self.goal_id))
        header.addWidget(edit_btn)

        if self.goal["is_active"]:
            del_btn = self._make_action_btn("×", "Deactivate",
                lambda: self.deactivate_requested.emit(self.goal_id))
            header.addWidget(del_btn)

        self._layout.addLayout(header)

    def _build_filter_chips(self):
        chips = []
        if self.goal.get("medium_type"):
            chips.append(self.goal["medium_type"].replace("_", " ").title())
        if self.goal.get("activity_type"):
            chips.append(self.goal["activity_type"].capitalize())

        if chips:
            label = QLabel(" · ". join(chips))
            label.setStyleSheet("font-size: 10px; color: palette(mid);")
            self._layout.addWidget(label)
    
    def _build_content(self):
        raise NotImplementedError

    @staticmethod
    def _make_action_btn(text: str, tooltip: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(24, 24)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(
            "QPushButton { padding: 0; font-size: 13px; border: none; }"
            "QPushButton:hover { background: palette(mid); border-radius: 4px; }"
        )
        btn.clicked.connect(callback)
        return btn

    
class RecurringGoalCard(BaseGoalCard):
    """Progress bar for the current period, habit dot strip, and streak/health stats."""

    def _build_content(self):
        progress = self.goal["progress"]
        health = self.goal.get("habit_health", {})

        # Current period progress
        header = QHBoxLayout()
        period_text = self.goal["period"].capitalize()
        header.addWidget(QLabel(f"{period_text} progress"))
        header.addStretch()

        value_label = QLabel(
            f"{progress['current_value']:,} / {progress['target_value']:,}"
            f"{format_metric_unit(self.goal['metric'])}"
        )
        value_label.setStyleSheet("font-size: 10px; color: palette(mid);")
        header.addWidget(value_label)
        self._layout.addLayout(header)

        pb = QProgressBar()
        pb.setRange(0, 100) 
        pb.setValue(min(int(progress["progress_pct"]*100), 100))
        pb.setTextVisible(False)
        pb.setFixedHeight(10)
        self._layout.addWidget(pb)

        # Habit stats
        stats = QHBoxLayout()
        health_pct = health.get("health_pct", 0)
        streak = health.get("current_streak", 0)
        best = health.get("best_streak", 0)

        health_label = QLabel(f"<b>{health_pct:.0f}%</b> health")
        # Color code health label
        if health_pct >= 80:
            color = "#5AD8A6"
        elif health_pct >= 60:
            color = "#F6BD16"
        else:
            color = "#E86452"
        health_label.setStyleSheet(f"color: {color};")
        stats.addWidget(health_label)

        stats.addWidget(QLabel(f"Current streak: <b>{streak}</b>"))
        stats.addWidget(QLabel(f"Best: <b>{best}</b>"))
        stats.addStretch()
        self._layout.addLayout(stats)
    

class LifetimeGoalCard(BaseGoalCard):
    """Cumulative progress bar toward the target value."""

    def _build_content(self):
        progress = self.goal["progress"]
        unit = format_metric_unit(self.goal["metric"])

        pb = QProgressBar()
        pb.setRange(0, 100)  # !! roundabout?
        pb.setValue(min(int(progress["progress_pct"]*100), 100))
        pb.setTextVisible(True)
        pb.setFormat(f"{progress['progress_pct']:.1%}")
        pb.setFixedHeight(18)
        self._layout.addWidget(pb)

        info = QLabel(
            f"{progress['current_value']:,} / {progress['target_value']:,} {unit}"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("font-size: 11px; color: palette(mid);")
        self._layout.addWidget(info)


