from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class LogForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.label = QLabel("<h1>Log Form goes here</h1>")
        layout.addWidget(self.label)
