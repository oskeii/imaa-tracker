from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class SessionHistoryWidget(QWidget):
    """
    Filterable table showing logged immersion sessions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.label = QLabel("<h1>Session History table goes here</h1>")
        layout.addWidget(self.label)
