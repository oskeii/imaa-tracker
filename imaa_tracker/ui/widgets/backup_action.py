""""Back Up Database..." File menu action"""
from datetime import datetime
from pathlib import Path
import logging

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from imaa_tracker.core import db, paths
from imaa_tracker.core.migrations import open_database

logger = logging.getLogger(__name__)


def save_database_backup(parent=None):
    """
    Prompt user for DB backup file save location.
    Returns saved filepath, or None if cancelled.
    """
    suggested = f"imaa_tracker_{datetime.now():%Y%m%d-%H-%M}.db"
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Back Up Database",
        suggested,
        "SQLite Database (*.db);;All Files (*)",
    )

    if not path:
        return None

    try:
        db.backup_database(path)
    except Exception as e:
        QMessageBox.critical(
            parent, "Backup Failed",
            f"Could not back up the database\n{e}",
        )
        return None

    size_mb = Path(path).stat().st_size / (1024*1024)
    QMessageBox.information(
        parent, "Backup Complete",
        f"Database backed up to:\n{path}\n({size_mb:.1f} MB)",
    )
    return path


def restore_database_from_backup(parent=None):
    path, _ = QFileDialog.getOpenFileName(
        parent, "Restore From Backup", str(paths.BACKUP_DIR),
        "SQLite Database (*.db);;All Files (*)",
    )
    if not path:
        return False

    logger.info("restore requested: %s", str(path))
    try:
        info = db.inspect_backup(path)
    except ValueError as e:
        logger.warning("backup rejected: %s — %s", str(path), e)
        QMessageBox.critical(parent, "Invalid Backup", str(e))
        return False

    logger.info("backup file validated: schema v%s, %s sessions",
                info["schema_version"], info["session_count"])
    confirm = QMessageBox.warning(
        parent, "Replace Current Database?",
        f"This backup holds {info['session_count']} immersion sessions "
        f"(schema v{info['schema_version']}).\n\n"
        "Your current data will be REPLACED. A safety copy is saved first.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        defaultButton=QMessageBox.StandardButton.Cancel
    )
    if confirm != QMessageBox.StandardButton.Yes:
        logger.info("restore cancelled by user")
        return False

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safety = paths.BACKUP_DIR / f"pre-restore-{stamp}.db"
    try:
        db.backup_database(str(safety))
        logger.info("safety copy written: %s", str(safety))
        db.restore_database(path)
        open_database()  # migrate restored DB forward
    except Exception as e:
        logger.exception("restore failed; previous database saved to %s", str(safety))
        QMessageBox.critical(
            parent, "Restore Failed",
            f"{e}\n\n Your previous database was saved to: \n{safety}",
        )
        return False

    logger.info("restore succeeded from %s", str(path))
    QMessageBox.information(
        parent, "Restore Complete",
        f"Restored {info['session_count']} sessions.\n"
        f"Previous database saved to: \n{safety}",
    )
    return True

