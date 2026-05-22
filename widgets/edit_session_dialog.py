from PyQt6.QtWidgets import QDialog


class EditSessionDialog(QDialog):
    """Modal dialog for editing sessions"""
    def __init__(self, sessions: list[dict], parent=None):
        super().__init__(parent)
        if not sessions:
            raise ValueError("EditSessionDialog requires at least one session")

        self.sessions = sessions
        self.is_batch = len(sessions) > 1

        self.setWindowTitle(
            "Edit Session" if not self.is_batch
            else f"Edit {len(sessions)} Sessions"
        )
        self.setMinimumWidth(480)



