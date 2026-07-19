from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

from migrations import open_database
from widgets import LogForm, SessionHistoryWidget, DashboardContainer
from widgets.summary_cards import DailySummaryCard, AllTimeTotalsCard, WeeklySummaryCard
from widgets.charts_mpl import TimeByMediumPieChart, ActivityRatioChart
from widgets.charts_pyqtgraph import ImmersionTimeTrend, ReadingSpeedTrend

from widgets.snapshot_export import save_dashboard_snapshot
from widgets.backup_action import save_database_backup


def create_dashboard() -> DashboardContainer:
    """
    Factory function that assembles the modular dashboard with all its cards
    """
    dashboard = DashboardContainer()
    # dashboard.add_card(DailySummaryCard())
    # dashboard.add_card(AllTimeTotalsCard())
    dashboard.add_cards_hbox(DailySummaryCard(), AllTimeTotalsCard())
    dashboard.add_card(WeeklySummaryCard())

    dashboard.add_card(TimeByMediumPieChart())
    dashboard.add_card(ActivityRatioChart())

    dashboard.add_card(ReadingSpeedTrend())
    dashboard.add_card(ImmersionTimeTrend())
    return dashboard


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immersion Tracker")
        self.setMinimumSize(600, 600)

        # --- Central Widget: Tab Container ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Create tab widgets ---
        self.log_form = LogForm()
        self.session_history = SessionHistoryWidget()
        self.dashboard = create_dashboard()

        self.tabs.addTab(self.log_form, "Log Session")
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.session_history, "History")

        # --- Cross-tab communication ---
        # new session logged -> refresh session history table + dashboard
        self.log_form.sig_session_logged.connect(self.session_history.refresh)
        self.log_form.sig_session_logged.connect(self.dashboard.refresh_all)

        # --- Status bar ---
        self.statusBar().showMessage("Ready")

        # --- Actions ---
        export_action = QAction("Export as PNG", self)
        export_action.triggered.connect(lambda: save_dashboard_snapshot(self.dashboard, self))

        backup_action = QAction("Back Up Database...", self)
        backup_action.triggered.connect(lambda : save_database_backup(self))

        # --- Menu ---
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(backup_action)


def main():
    open_database()

    app = QApplication([])
    app.setStyle("Fusion")

    # Create a Qt widget for the window
    window = MainWindow()
    window.show()

    # Start event loop
    app.exec()


if __name__ == "__main__":
    main()
