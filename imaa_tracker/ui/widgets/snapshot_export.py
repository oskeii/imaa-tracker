from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog, QWidget, QScrollArea


def export_scroll_area_snapshot(scroll_area: QScrollArea, filepath: str) -> bool:
    """
    Capture full contents of a QScrollArea as a PNG.
    Returns True on success.
    """
    inner = scroll_area.widget()
    if inner is None:
        return False

    # Ensure content widget is laid out to its full size
    inner.adjustSize()
    size = inner.sizeHint()
    if not size.isValid() or size.width() == 0 or size.height() == 0:
        size = inner.size()

    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.white)
    # QWidget.render() draws the widget into a paint device at any size, regardless of what's currently visible
    inner.render(pixmap, flags=QWidget.RenderFlag.DrawChildren)

    return pixmap.save(filepath, "PNG")


def save_dashboard_snapshot(dashboard_container, parent_window=None) -> str:
    """
    Prompt user for save location to then export the full dashboard as a PNG.
    (default: timestamped filename in home directory)
    Returns saved filepath, or None if cancelled.
    """
    success = False
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    default_name = f"immersion-dashboard_{timestamp}.png"
    default_path = str(Path.home() / default_name)

    filepath, _ = QFileDialog.getSaveFileName(
        parent_window,
        "Save Dashboard Snapshot",
        default_path,
        "PNG Images (*.png)",
    )
    if not filepath:
        return None

    if hasattr(dashboard_container, "_scroll"):
        success = export_scroll_area_snapshot(dashboard_container._scroll, filepath)

    return filepath if success else None
