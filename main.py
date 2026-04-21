from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget

from widgets import LogForm, SessionHistoryWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immersion Tracker")
        self.setMinimumSize(600, 400)

        # --- Tab Container ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Create tab widgets ---
        self.log_form = LogForm()
        self.session_history = SessionHistoryWidget()

        self.tabs.addTab(self.log_form, "Log Session")
        self.tabs.addTab(self.session_history, "History")

        # --- Status bar ---
        self.statusBar().showMessage("Ready")


def main():
    app = QApplication([])
    app.setStyle("Fusion")

    # Create a Qt widget for the window
    window = MainWindow()
    window.show()

    # Start event loop
    app.exec()


if __name__ == "__main__":
    main()
