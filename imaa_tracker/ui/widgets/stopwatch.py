from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, QTimer, Qt


class Stopwatch(QWidget):
    """
    A stopwatch that emits the elapsed minutes when stopped.

    Signals:
        sig_time_recorded(int): emitted when the user stops the timer,
                            holds the elapsed time in minutes.
    """

    sig_time_recorded = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._elapsed_seconds = 0
        self._running = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)  # what runs after each interval...

        # --- Build the UI ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("00:00:00")
        self._label.setStyleSheet("font-family: monospace; font-size: 16px;")
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.setSpacing(30)
        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._reset_btn = QPushButton("Reset")

        self._stop_btn.setEnabled(False)

        # connect signals
        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)
        self._reset_btn.clicked.connect(self.reset)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addWidget(self._reset_btn)

    def _tick(self):
        """Called every interval while the timer is running."""
        self._elapsed_seconds += 1
        self._update_display()

    def _update_display(self):
        h = self._elapsed_seconds // 3600
        m = (self._elapsed_seconds % 3600) // 60
        s = self._elapsed_seconds % 60
        self._label.setText(f"{h:02}:{m:02}:{s:02}")

    def _start(self):
        print(f"Starting timer at {self.elapsed_minutes()}mins")
        self._timer.start()
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

    def _stop(self):
        self._timer.stop()
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        print(f"Timer stopped at {self.elapsed_minutes()}mins")

        # Emit elapsed minutes for log form
        self.sig_time_recorded.emit(self.elapsed_minutes())

    def reset(self):
        self._timer.stop()
        self._elapsed_seconds = 0
        self._update_display()
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(True)

    def elapsed_minutes(self) -> int:
        return round(self._elapsed_seconds / 60)
