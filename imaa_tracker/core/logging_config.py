import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir, level=logging.INFO, console=None):
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger("imaa_tracker")
    root.setLevel(level)
    root.handlers.clear()

    fh = RotatingFileHandler(
        log_dir / "imaa-tracker.log",
        maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Only attach a console handler if one exists.
    # PyInstaller --windowed gives no console:
    # sys.stderr is None on Windows, and StreamHandler(None) raises.
    if console is None:
        console = sys.stderr is not None
    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)
