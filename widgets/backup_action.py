""""Back Up Database..." File menu action"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox

import db


def save_database_backup(parent=None):
    """
    Prompt user for DB backup file save location.
    Returns saved filepath, or None if cancelled.
    """
    suggested = f"imaa_tracker_{datetime.now():%Y%m%d}.db"
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
