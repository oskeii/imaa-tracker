import logging
import sys
import argparse

from PyQt6.QtWidgets import QApplication

from imaa_tracker.core.logging_config import setup_logging
from imaa_tracker.core import db
from imaa_tracker.core.migrations import open_database
from imaa_tracker.core.paths import DB_PATH, DEMO_DB_PATH, LOG_DIR, ensure_dirs
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="imaa-tracker")
    parser.add_argument("--demo", action="store_true",
                        help="Open the app with the demo database loaded instead of your real data.")
    parser.add_argument("--drop", action="store_true",
                        help="Clear your database. (Will create a backup file first)")
    args, qt_args = parser.parse_known_args(argv)

    ensure_dirs()
    setup_logging(LOG_DIR)
    _install_excepthook()

    if args.drop:
        logger.info("Database clear requested.")
        db.drop_database(DB_PATH)
    if args.demo:
        db.set_database_path(DEMO_DB_PATH)

    logger.info("imaa-tracker starting")
    logger.info("database: %s", db.DB_NAME)
    logger.info("log directory: %s", LOG_DIR)

    app = QApplication([sys.argv[0]] + qt_args)
    # app.setStyle("Fusion")

    try:
        open_database()
    except Exception:
        logger.exception("database failed to open")
        raise

    # Create a Qt widget for the window
    window = MainWindow()
    if args.demo:
        window.setWindowTitle(window.windowTitle() + "  ——  DEMO DATA")
    window.show()

    # Start event loop
    exit_code = app.exec()
    logger.info("imaa-tracker exiting (code %s)", exit_code)
    return exit_code


if __name__ == "__main__":
    main()
