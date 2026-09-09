from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from .widgets import LogForm, SessionHistoryWidget, DashboardContainer, GoalsTab
from .widgets.summary_cards import DailySummaryCard, AllTimeTotalsCard, WeeklySummaryCard
from .widgets.charts_mpl import TimeByMediumPieChart, ActivityRatioChart
from .widgets.charts_pyqtgraph import ImmersionTimeTrend, ReadingSpeedTrend
from .widgets.goal_notifs import GoalsStrip, AchievementNotifier

from .widgets.snapshot_export import save_dashboard_snapshot
from .widgets.backup_action import save_database_backup, restore_database_from_backup


def create_dashboard() -> DashboardContainer:
    """Assembles the modular dashboard with all its cards"""
    dashboard = DashboardContainer()
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
        self.goals_tab = GoalsTab()
        self.goals_strip = GoalsStrip()
        self.achievement_notifier = AchievementNotifier(self)

        # Wrap goals strip and log form
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)
        log_tab_layout.setContentsMargins(0, 0, 0, 0)
        log_tab_layout.addWidget(self.goals_strip)
        log_tab_layout.addWidget(self.log_form)

        self.tabs.addTab(log_tab, "Log Session")
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.session_history, "History")
        self.tabs.addTab(self.goals_tab, "Goals")

        # --- Cross-tab communication ---
        self.log_form.sig_session_logged.connect(self._on_sessions_changed)
        self.session_history.sig_sessions_changed.connect(self._on_sessions_changed)
        self.goals_tab.sig_goals_changed.connect(self._on_goals_changed)

        # --- Status bar ---
        self.statusBar().showMessage("Ready")

        # --- Actions ---
        export_action = QAction("Dashboard: Export as PNG", self)
        export_action.triggered.connect(lambda: save_dashboard_snapshot(self.dashboard, self))

        backup_action = QAction("Back Up Database...", self)
        backup_action.triggered.connect(lambda: save_database_backup(self))

        restore_action = QAction("Restore from Backup...", self)
        restore_action.triggered.connect(self._on_restore_requested)

        # --- Menu ---
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(backup_action)
        file_menu.addAction(restore_action)

    def _refresh_all_views(self):
        self.goals_strip.refresh()
        self.goals_tab.refresh()
        self.session_history.refresh()
        self.dashboard.refresh_all()

    def _on_sessions_changed(self, affected_dates: list[str] = None):
        """Session data added, edited, or deleted"""
        from imaa_tracker.core.services import goals_service as gs
        events: list[dict] = []

        # Re-evaluate any related past goal periods, without notifications
        for d in (affected_dates or []):
            events.extend(
                e for e in gs.check_and_log_goals(as_of_date=d)
                if e["type"] == "lifetime_regression"
            )
            # gs.check_and_log_goals(as_of_date=d)

        # Evaluate any current goal periods against newly-updated session data, to notify
        events.extend(gs.check_and_log_goals())
        self.achievement_notifier.notify(events)

        self._refresh_all_views()

    def _on_goals_changed(self):
        """A goal was created, edited, pinned, or deactivated"""
        from imaa_tracker.core.services import goals_service as gs

        events = gs.check_and_log_goals()
        self.achievement_notifier.notify(events)

        self._refresh_all_views()

    def _on_restore_requested(self):
        if restore_database_from_backup(self):
            # !! maybe re-evaluate goals here too
            self._refresh_all_views()
            self.statusBar().showMessage("Database restored.", 5000)
