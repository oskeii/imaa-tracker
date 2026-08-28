import logging
import sys

from PyQt6.QtWidgets import QApplication

from imaa_tracker.core.logging_config import setup_logging
from imaa_tracker.core.migrations import open_database
from imaa_tracker.core.paths import DB_PATH, LOG_DIR, ensure_dirs
from imaa_tracker.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _install_excepthook():
    """Catch any tracebacks from unhandled exceptions"""
    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = hook


def main() -> int:
    ensure_dirs()
    setup_logging(LOG_DIR)
    _install_excepthook()

    logger.info("imaa-tracker starting")
    logger.info("database: %s", DB_PATH)
    logger.info("log directory: %s", LOG_DIR)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        open_database()
    except Exception:
        logger.exception("database failed to open")
        raise

    # Create a Qt widget for the window
    window = MainWindow()
    window.show()

    # Start event loop
    exit_code = app.exec()
    logger.info("imaa-tracker exiting (code %s)", exit_code)
    return exit_code


if __name__ == "__main__":
    main()
