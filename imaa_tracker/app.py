import sys

from PyQt6.QtWidgets import QApplication

from imaa_tracker.core.migrations import open_database
from imaa_tracker.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    open_database()

    # Create a Qt widget for the window
    window = MainWindow()
    window.show()

    # Start event loop
    app.exec()


if __name__ == "__main__":
    main()
