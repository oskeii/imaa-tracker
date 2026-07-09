from PyQt6.QtWidgets import (
    QWidget, QFrame, QDialog, QLayout, QHBoxLayout, QVBoxLayout, QFormLayout, QScrollArea,
    QLabel, QPushButton, QDateEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QDate
from datetime import date, timedelta
from db import ENUMS

SENTINEL_DATE = QDate(1970, 1, 1)


# ------ Helpers for UI ------
class _JumpToTodayOnOpen(QObject):
    """Event filter for QCalendarWidget that jumps to today's date when opened,
    ONLY if the parent QDateEdit is at the sentinel date value."""

    def __init__(self, date_edit: QDateEdit, sentinel: QDate):
        super().__init__(date_edit)  # parenting handles event filter lifetime
        self._edit = date_edit
        self._sentinel = sentinel

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and (self._edit.date() == self._sentinel):
            obj.setSelectedDate(QDate.currentDate())
            obj.showToday()
        return False


def _make_date_edit(current_iso: str = None) -> QDateEdit:
    """
    Builds a QDateEdit that can represent 'no filter' explicitly.
    When the widget value equals SENTINEL_DATE, it displays "Any date"
    """
    edit = QDateEdit()
    edit.setCalendarPopup(True)
    edit.setMinimumDate(SENTINEL_DATE)
    edit.setSpecialValueText("Any date")

    if current_iso:
        edit.setDate(QDate.fromString(current_iso, "yyyy-MM-dd"))
    else:
        edit.setDate(SENTINEL_DATE)

    calendar = edit.calendarWidget()
    f = _JumpToTodayOnOpen(edit, SENTINEL_DATE)
    calendar.installEventFilter(f)

    return edit


def _date_edit_value(edit: QDateEdit) -> str:
    """Read a date edit, return None if equal to SENTINEL_DATE"""
    d = edit.date()
    if d == SENTINEL_DATE:
        return None
    return d.toString("yyyy-MM-dd")


def _clear_date_button(edit: QDateEdit) -> QPushButton:
    """Button to reset a date edit to SENTINEL_DATE ('Any date')"""
    btn = QPushButton("✕")
    btn.setFixedSize(20, 20)
    btn.setToolTip("Clear")
    btn.setStyleSheet("QPushButton { padding: 0; font-size: 10px; }")
    btn.clicked.connect(lambda: edit.setDate(SENTINEL_DATE))
    return btn


def _date_row(edit: QDateEdit) -> QWidget:
    """Pack date edit and clear button side by side"""
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    row.addWidget(edit, stretch=1)
    row.addWidget(_clear_date_button(edit))
    return container


def _period_label(iso_date: str, period: str = "day") -> str:
    """
    Format an ISO date as a semantic label relative to current date.
        period="day":   "Today" | "Yesterday" | (e.g. "Jul 05, 2026")
        period="week":   "This week" | "Last week" | (e.g."Week of Jun 29" )
        period="month":   "This month" | "Last month" | (e.g. "May 2026")
    Returns "All time" when iso_date is None.
    """
    if iso_date is None:
        return "All time"
    target = date.fromisoformat(iso_date)
    today = date.today()

    if period == "day":
        if target == today:
            return "Today"
        if target == today - timedelta(days=1):
            return "Yesterday"
        return target.strftime("%b %d, %Y")

    if period == "week":
        target_monday = target - timedelta(days=target.weekday())
        curr_monday = today - timedelta(days=today.weekday())
        weeks_past = (curr_monday - target_monday).days // 7
        if weeks_past == 0:
            return "This week"
        if weeks_past == 1:
            return "Last week"
        return f"Week of {target_monday.strftime('%b %d')}"

    if period == "month":
        # if (target.year, target.month) == (today.year, today.month):
        #     return "This month"
        # last_month = today.replace(day=1) - timedelta(days=1)
        # if (target.year, target.month) == (last_month.year, last_month.month):
        #     return "Last month"
        return target.strftime("%B %Y")

    return iso_date


class DashboardCard(QFrame):
    """
    Base class for dashboard widgets.
    Class attrs to override:
        SUPPORTED_FILTERS:  set of filter keys the card recognizes
        DEFAULT_FILTERS:    dict of filter values
        STEP_PERIOD:        "day" | "week" | "month" | None. Adds prev/next arrows
        STEP_FILTER:         filter key the arrows modify (e.g. "target_date")
    Subclasses must implement:
        refresh(self)
    """

    SUPPORTED_FILTERS: set[str] = set()
    DEFAULT_FILTERS: dict = {}
    STEP_PERIOD: str = None
    STEP_FILTER: str = None

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.card_title = title
        self.filters: dict = dict(self.DEFAULT_FILTERS)
        print(self.card_title)
        print("DEFAULT FILTERS:", self.DEFAULT_FILTERS)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        # !! is this even doing anything?
        # self.setLineWidth(1)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)

        self._build_header()  # title, arrows, filter button, active filter chips

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(6)

        self._title_label = QLabel(self.card_title)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self._title_label)
        header.addStretch()

        # Prev/Next arrows
        if self.STEP_FILTER and self.STEP_PERIOD:
            self._prev_btn = self._icon_button("‹", "Previous")
            self._prev_btn.clicked.connect(lambda: self._step(-1))
            self._next_btn = self._icon_button("›", "Next")
            self._next_btn.clicked.connect(lambda: self._step(1))
            header.addWidget(self._prev_btn)
            header.addWidget(self._next_btn)

        # Filter config button
        if self.SUPPORTED_FILTERS:
            self._filter_btn = self._icon_button("⚙", "Filter")
            self._filter_btn.clicked.connect(self._open_filter_popover)
            header.addWidget(self._filter_btn)

        self._layout.addLayout(header)

        # Chip strip - line summary of active filters
        self._chip_strip = QLabel()
        self._chip_strip.setStyleSheet(
            "font-size: 10px; color: palette(mid); margin-bottom: 2px;"
        )
        self._chip_strip.setWordWrap(True)
        self._layout.addWidget(self._chip_strip)
        self._update_chip_strip()

    @staticmethod
    def _icon_button(text: str, tooltip: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(22, 22)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("QPushButton { padding: 0; font-size: 14px; }")
        return btn

    def add_content_widget(self, widget: QWidget):
        self._layout.addWidget(widget)

    def add_content_layout(self, layout: QLayout):
        self._layout.addLayout(layout)

    # Filter state management
    def apply_filter_update(self, partial: dict):
        """
        Merge partial filter changes into self.filters and refresh.
        Ignores keys not in SUPPORTED_FILTERS
        """
        has_changes = False
        for k, v in partial.items():
            if k in self.SUPPORTED_FILTERS and self.filters.get(k) != v:
                self.filters[k] = v
                has_changes = True
        if has_changes:
            self._update_chip_strip()
            self.refresh()

    def reset_filters(self):
        """Restore card to its DEFAULT_FILTERS"""
        new_state = {k: None for k in self.SUPPORTED_FILTERS}
        new_state.update(self.DEFAULT_FILTERS)

        self.filters = new_state
        self._update_chip_strip()
        self.refresh()

    def _step(self, direction: int):
        """Shift STEP_FILTER by one STEP_PERIOD in the given direction (+1 or -1)"""
        current = self.filters.get(self.STEP_FILTER)
        d = date.fromisoformat(current) if current else date.today()

        if self.STEP_PERIOD == "day":
            new_d = d + timedelta(days=direction)
        elif self.STEP_PERIOD == "week":
            new_d = d + timedelta(weeks=direction)
        elif self.STEP_PERIOD == "month":
            month = d.month + direction
            year = d.year
            if month < 1:  # current date is in January; new date is in prev December
                month += 12
                year -= 1
            elif month > 12:  # current date in December; new date in January next year
                month -= 12
                year += 1
            new_d = date(year, month, day=1)
        else:
            return

        self.apply_filter_update({self.STEP_FILTER: new_d.isoformat()})

    def _open_filter_popover(self):
        popover = FilterPopover(self, self.window())
        popover.sig_filters_applied.connect(self.apply_filter_update)
        popover.sig_reset_requested.connect(self.reset_filters)

        btn_pos = self._filter_btn.mapToGlobal(self._filter_btn.rect().bottomLeft())
        popover.move(btn_pos)
        popover.show()

    def _update_chip_strip(self):
        chips = self._get_active_chips()
        if not chips:
            self._chip_strip.setText("")
            self._chip_strip.setVisible(False)
        else:
            self._chip_strip.setText(" · ".join(chips))
            self._chip_strip.setVisible(True)

    def _get_active_chips(self) -> list[str]:
        """Override for custom chips"""
        chips = []

        # Date-range
        if "start_date" in self.SUPPORTED_FILTERS or "end_date" in self.SUPPORTED_FILTERS:
            chips.append(self._format_date_range())

        # Single-date
        if "target_date" in self.SUPPORTED_FILTERS:
            chips.append(_period_label(
                iso_date=self.filters.get("target_date"),
                period=self.STEP_PERIOD or self.filters.get("group_by") or "day"
            ))

        # Categorical filters
        for key, default_label in [
            ("medium_type", "All media"),
            ("activity_type", "All activities")
        ]:
            if key in self.SUPPORTED_FILTERS:
                val: str = self.filters.get(key)
                chips.append(val.replace("_", " ").title() if val else default_label)

        return chips

    def _format_date_range(self) -> str:
        start = self.filters.get("start_date")
        end = self.filters.get("end_date")
        period = self.STEP_PERIOD or self.filters.get("group_by") or "day"
        if not start and not end:
            return "All time"

        if start and end:
            return f"{self._format_date(start, period)} → {self._format_date(end, period)}"
        return f"Since {self._format_date(start, period)}" if start else f"Until {self._format_date(end, period)}"

    @staticmethod
    def _format_date(iso_date: str, period: str) -> str:
        d = date.fromisoformat(iso_date)
        if period == "day":
            return d.strftime("%b %d, %Y")
        if period == "week":
            monday = d - timedelta(days=d.weekday())
            return f"Week of {monday.strftime('%b %d')}"
        if period == "month":
            return d.strftime("%B %Y")

        return iso_date

    def refresh(self):
        """Must be implemented by subclass. Called when data is updated or filters changed."""
        raise NotImplementedError


class FilterPopover(QDialog):
    """
    Card filters configuration dialog.
    Signals:
        sig_filters_applied: emitted on Apply
        sig_reset_requested: emitted on Reset
    """

    sig_filters_applied = pyqtSignal(dict)
    sig_reset_requested = pyqtSignal()

    def __init__(self, card: DashboardCard, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self._card = card
        self._controls: dict = {}
        self._build_ui()

    def _build_ui(self):
        self.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        supported = self._card.SUPPORTED_FILTERS
        current = self._card.filters

        form = QFormLayout()
        layout.addLayout(form)

        # Date range
        if "start_date" in supported:
            start = _make_date_edit(current.get("start_date"))
            form.addRow("From:", _date_row(start))
            self._controls["start_date"] = start

        if "end_date" in supported:
            end = _make_date_edit(current.get("end_date"))
            form.addRow("To:", _date_row(end))
            self._controls["end_date"] = end

        if "target_date" in supported:
            target = QDateEdit()
            target.setCalendarPopup(True)
            v = current.get("target_date")
            if v:
                target.setDate(QDate.fromString(v, "yyyy-MM-dd"))
            else:
                target.setDate(QDate.currentDate())
            form.addRow("Date:", target)
            self._controls["target_date"] = target

        # Categorical
        if "medium_type" in supported:
            medium = QComboBox()
            medium.addItem("All", userData=None)
            for mt in ENUMS["MEDIUM_TYPES"]:
                medium.addItem(mt.replace("_", " ").title(), userData=mt)
            v = current.get("medium_type")
            if v:
                idx = medium.findData(v)
                if idx >= 0:
                    medium.setCurrentIndex(idx)
            form.addRow("Medium:", medium)
            self._controls["medium_type"] = medium

        if "activity_type" in supported:
            activity = QComboBox()
            activity.addItem("All", userData=None)
            for at in ENUMS["ACTIVITY_TYPES"]:
                activity.addItem(at.replace("_", " ").title(), userData=at)
            v = current.get("activity_type")
            if v:
                idx = activity.findData(v)
                if idx >= 0:
                    activity.setCurrentIndex(idx)
            form.addRow("Activity:", activity)
            self._controls["activity_type"] = activity

        if "group_by" in supported:
            group = QComboBox()
            for gb in ["month", "week"]:
                group.addItem(gb.capitalize(), userData=gb)
            v = current.get("group_by", "month")
            idx = group.findData(v)
            if idx >= 0:
                group.setCurrentIndex(idx)
            form.addRow("Group by:", group)
            self._controls["group_by"] = group

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(reset_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

    def _on_apply(self):
        result = {}
        for key, ctrl in self._controls.items():
            if isinstance(ctrl, QDateEdit):
                if key == "target_date":
                    result[key] = ctrl.date().toString("yyyy-MM-dd")
                else:
                    result[key] = _date_edit_value(ctrl)  # None if sentinel
            elif isinstance(ctrl, QComboBox):
                result[key] = ctrl.currentData()

        self.sig_filters_applied.emit(result)
        self.close()

    def _on_reset(self):
        self.sig_reset_requested.emit()
        self.close()


class DashboardContainer(QWidget):
    """The main dashboard tab (container)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[DashboardCard] = []
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        self._reset_btn = QPushButton("Reset All")
        filter_layout.addWidget(self._reset_btn)
        filter_layout.addWidget(self._refresh_btn)
        main_layout.addLayout(filter_layout)

        # Scrollable area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setSpacing(12)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        main_layout.addWidget(self._scroll)

    def _connect_signals(self):
        self._refresh_btn.clicked.connect(self.refresh_all)
        self._reset_btn.clicked.connect(self._reset_all)

    def add_card(self, card: DashboardCard):
        self._cards.append(card)
        # Insert widget before stretch
        self._card_layout.insertWidget(self._card_layout.count() - 1, card)
        card.refresh()

    def add_cards_hbox(self, *cards: DashboardCard):
        hbox = QHBoxLayout()

        self._card_layout.insertLayout(self._card_layout.count() - 1, hbox)
        for c in cards:
            self._cards.append(c)
            hbox.addWidget(c)
            c.refresh()

    def remove_card(self, title: str):
        for card in self._cards:
            if card.card_title == title:
                self._card_layout.removeWidget(card)
                card.deleteLater()
                self._cards.remove(card)
                break

    def refresh_all(self):
        """Trigger refresh on all cards (with current filters)"""
        print("REFRESHING DASHBOARD....")
        for card in self._cards:
            print(card.card_title)
            card.refresh()

    def _reset_all(self):
        for card in self._cards:
            card.reset_filters()
