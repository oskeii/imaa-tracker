from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

from db import init_db
from widgets import LogForm, SessionHistoryWidget, DashboardContainer
from widgets.dashboard import DailySummaryCard, AllTimeTotalsCard
from widgets.charts_mpl import TimeByMediumPieChart, TimeByMediumBarChart, ActivityRatioChart
from widgets.charts_pyqtgraph import ImmersionTimeTrend, ReadingSpeedTrend


def create_dashboard() -> DashboardContainer:
    """
    Factory function that assembles the modular dashboard with all its cards
    """
    dashboard = DashboardContainer()
    dashboard.add_card(DailySummaryCard())
    dashboard.add_card(AllTimeTotalsCard())

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
        self.tabs.addTab(self.session_history, "History")
        self.tabs.addTab(self.dashboard, "Dashboard")

        # --- Cross-tab communication ---
        # new session logged -> refresh session history table + dashboard
        self.log_form.sig_session_logged.connect(self.session_history.refresh)
        self.log_form.sig_session_logged.connect(self.dashboard.refresh_all)

        # --- Status bar ---
        self.statusBar().showMessage("Ready")


def main():
    init_db()

    app = QApplication([])
    app.setStyle("Fusion")

    # Create a Qt widget for the window
    window = MainWindow()
    window.show()

    # Start event loop
    app.exec()


if __name__ == "__main__":
    main()
