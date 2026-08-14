from unicodedata import name
import enum
from PyQt6.QtWidgets import (
    QWidget, QFrame, QDialog, QVBoxLayout, QHBoxLayout,
    QProgressBar, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QObject

from imaa_tracker.core.utils.formatting import format_metric_unit

class GoalsStrip(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 8)
        self._layout.setSpacing(4)
        self.refresh()

    def refresh(self):
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from imaa_tracker.core.services import goals_service as gs
        goals = gs.get_log_strip_goals()

        if not goals:
            self.setVisible(False)
            return
        self.setVisible(True)

        for goal in goals:
            self._layout.addWidget(self._make_row(goal))

        
    def _make_row(self,  goal: dict) -> QWidget:
        row = QFrame()
        row.setFrameStyle(QFrame.Shape.NoFrame)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        name = QLabel(goal["name"])
        name.setStyleSheet("font-size: 11px;")
        name.setFixedWidth(180)
        layout.addWidget(name)

        progress = goal["progress"]
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(min(int(progress["progress_pct"] * 100), 100))
        pb.setTextVisible(False)
        pb.setFixedHeight(12)
        layout.addWidget(pb, stretch=1)

        unit = format_metric_unit(goal["metric"])
        val_label = QLabel(
            f"{progress['current_value']:,}/{progress['target_value']:,} {unit}"
        )
        val_label.setStyleSheet("font-size: 10px; color: palette(mid);")
        val_label.setFixedWidth(140)
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(val_label)

        return row


class AchievementNotifier(QObject):
    """
    Route achievement events to appropriate UI
    """
    def __init__(self, main_window: QWidget):
        super().__init__(main_window)
        self._main_window = main_window
        self._active_toasts: list[QFrame] = []

    def notify(self, achievements: list[dict]):
        for a in achievements:
            if a["type"] == "lifetime":
                self._show_modal(a)
            elif a["type"] == "recurring":
                self._show_toast(a)

    def _show_modal(self, achievement: dict):
        goal = achievement["goal"]
        progress = achievement["progress"]
        unit = format_metric_unit(goal["metric"])

        dlg = QDialog(self._main_window)
        dlg.setWindowTitle("Goal achieved!")
        dlg.setMinimumWidth(420)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("🎉 Goal Achieved!")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        name = QLabel(goal["name"])
        name.setStyleSheet("font-size: 16px;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        detail = QLabel(
            f"You reached <b>{progress['current_value']:,} {unit}</b><br>"
            f"(target was {progress['target_value']:,})"
        )
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setStyleSheet("color: palette(mid);")
        layout.addWidget(detail)

        note = QLabel(
            "A milestone has been added to your Accomplishments."
        )
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet("font-size: 10px; color: palette(mid);")
        layout.addWidget(note)

        btn = QPushButton("Nice!")
        btn.setDefault(True)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)

        dlg.exec()

    def _show_toast(self, achievement: dict):
        goal = achievement["goal"]

        toast = QFrame(self._main_window)
        toast.setStyleSheet("""
            QFrame {
                background: #5AD8A6;
                border-radius: 6px;
            }
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        inner = QHBoxLayout(toast)
        inner.setContentsMargins(10, 10, 10, 10)
        inner.addWidget(QLabel(f"✓  {goal['name']} — done!"))

        toast.adjustSize()
        self._position_toast(toast, active=self._active_toasts)
        toast.show()
        toast.raise_()

        self._active_toasts.append(toast)
        QTimer.singleShot(3500, lambda t=toast: self._remove_toast(t))

    def _position_toast(self, toast: QFrame, active: list[QFrame]):
        """Stack toasts bottom-right, offset upward for each active toast"""
        mw = self._main_window
        margin = 20
        offset = sum(t.height() + 8 for t in active)
        x = mw.width() - toast.width() - margin
        y = mw.height() - toast.height() - margin - offset
        toast.move(max(0, x), max(0, y))


    def _remove_toast(self, toast: QFrame):
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
        toast.deleteLater()

        # re-stack remaining toasts
        for i, t in enumerate(self._active_toasts):
            self._position_toast(t, active=self._active_toasts[:i])
