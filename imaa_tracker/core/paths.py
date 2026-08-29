"""Filesystem locations for app data."""
from pathlib import Path

import platformdirs

APP_NAME = "imaa-tracker"

DATA_DIR = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))
LOG_DIR = Path(platformdirs.user_log_dir(APP_NAME, appauthor=False))
CACHE_DIR = Path(platformdirs.user_cache_dir(APP_NAME, appauthor=False))

DB_PATH = DATA_DIR / "imaa_tracker.db"
DEMO_DB_PATH = DATA_DIR / "demo.db"
BACKUP_DIR = DATA_DIR / "backups"


def ensure_dirs():
    """Create app directories. Call at startup"""
    for d in (DATA_DIR, LOG_DIR, BACKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)
