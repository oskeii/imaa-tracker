from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
import repo


class SessionHistoryWidget(QWidget):
    """
    Filterable table showing logged immersion sessions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("<h1>Session History table goes here</h1>")
        layout.addWidget(self.label)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

    def refresh(self):
        print("Refreshing session history table...")
        sessions = repo.get_immersion_sessions()
        print("RECENT SESSIONS:\n", sessions)

        # Update summary
        total_min = sum(s.get("duration_minutes", 0) or 0 for s in sessions)
        total_char = sum(s.get("character_count", 0) or 0 for s in sessions)
        self.summary_label.setText(
            f"{len(sessions)} sessions  |  "
            f"{total_min} minutes total  |  "
            f"{total_char:,} characters"
        )
