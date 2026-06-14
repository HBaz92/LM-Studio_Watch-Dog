from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import asdict

try:
    from PySide6.QtCore import QObject, Qt, QTimer, Signal
    from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QStackedWidget,
        QSystemTrayIcon,
        QTabBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - user environment guard
    raise SystemExit(
        "PySide6 is required for the WinUI-style desktop app. "
        "Run: python -m pip install -r requirements.txt"
    ) from exc

from . import __version__
from .config import (
    AppConfig,
    PROJECT_TYPES,
    is_custom_project_type,
    load_config,
    normalize_custom_presets,
    save_config,
)
from .discovery import discover_rule_candidates, empty_rule_candidates
from .pipeline import PipelineResult, run_pipeline
from .presets import preset_rule_lists
from .watcher import PollingWatcher
from .win_mica import apply_mica_window


RULE_CATEGORIES = (
    "exclude_dirs",
    "exclude_files",
    "exclude_globs",
    "exclude_extensions",
    "include_files",
    "include_extensions",
)

APP_QSS = """
QMainWindow {
    background: #f3f6fb;
}
QWidget#Root {
    background: #f3f6fb;
    color: #1f1f1f;
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 10pt;
}
QWidget#Content,
QStackedWidget#PageStack,
QScrollArea#SettingsScroll,
QScrollArea#RulesScroll,
QWidget#SettingsPage,
QWidget#RulesPage,
QWidget#OutputPage {
    background: #f3f6fb;
}
QWidget#Root[watcherState="running"],
QWidget#Content[watcherState="running"],
QStackedWidget#PageStack[watcherState="running"],
QScrollArea#SettingsScroll[watcherState="running"],
QScrollArea#RulesScroll[watcherState="running"],
QWidget#SettingsPage[watcherState="running"],
QWidget#RulesPage[watcherState="running"],
QWidget#OutputPage[watcherState="running"],
QTabBar[watcherState="running"] {
    background: #edfdf4;
}
QFrame#Sidebar {
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 14px;
}
QFrame#Sidebar[watcherState="running"] {
    background: rgba(236, 253, 243, 0.80);
    border: 1px solid #75e0a7;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #d8dee8;
    border-radius: 12px;
}
QFrame#HeaderCard {
    background: rgba(255, 255, 255, 0.54);
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 14px;
}
QFrame#HeaderCard[watcherState="running"] {
    background: rgba(236, 253, 243, 0.86);
    border: 1px solid #75e0a7;
}
QFrame#RunningNotice {
    background: #dcfae6;
    border: 1px solid #75e0a7;
    border-radius: 12px;
}
QFrame#StatusChip {
    background: #eaf4ff;
    border: 1px solid #c9e3ff;
    border-radius: 10px;
}
QFrame#StatusChip[watcherState="running"] {
    background: #dcfae6;
    border: 1px solid #75e0a7;
}
QLabel#AppTitle {
    color: #111827;
    font-size: 22pt;
    font-weight: 700;
}
QLabel#AppSubtitle,
QLabel#Caption,
QLabel#FieldLabel {
    color: #667085;
}
QLabel#SectionTitle {
    color: #111827;
    font-size: 13pt;
    font-weight: 650;
}
QLabel#MetricValue {
    color: #111827;
    font-size: 11pt;
    font-weight: 650;
}
QLabel#MetricValue[watcherState="running"],
QLabel#RunningNoticeTitle {
    color: #027a48;
    font-weight: 750;
}
QLabel#RuleItemText {
    color: #111827;
    background: transparent;
    font-family: "Cascadia Mono", Consolas;
    font-size: 10pt;
}
QLabel#RunningNoticeText {
    color: #05603a;
}
QLabel#BrandMark {
    background: #0067c0;
    color: white;
    border-radius: 12px;
    font-size: 13pt;
    font-weight: 750;
}
QLineEdit,
QComboBox,
QPlainTextEdit {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #d0d5dd;
    border-radius: 8px;
    color: #1f2937;
    selection-background-color: #0067c0;
    selection-color: white;
}
QLineEdit,
QComboBox {
    min-height: 36px;
    padding: 6px 10px;
}
QLineEdit:disabled,
QComboBox:disabled,
QListWidget#RuleList:disabled,
QListWidget#RuleDiscoveryList:disabled,
QPlainTextEdit#RuleBox:disabled {
    background: #eef2f6;
    border: 1px solid #d0d5dd;
    color: #667085;
}
QLineEdit:focus,
QComboBox:focus,
QPlainTextEdit:focus {
    border: 2px solid #0067c0;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #98a2b3;
    color: #111827;
    selection-background-color: #eaf4ff;
    selection-color: #0067c0;
    outline: 0;
    padding: 4px;
}
QCheckBox {
    color: #1f2937;
    spacing: 8px;
}
QCheckBox:disabled {
    color: #667085;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #98a2b3;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #0067c0;
    border: 1px solid #0067c0;
}
QPushButton {
    min-height: 36px;
    padding: 7px 14px;
    border-radius: 8px;
    border: 1px solid #d0d5dd;
    background: rgba(255, 255, 255, 0.92);
    color: #1f2937;
    font-weight: 600;
}
QPushButton:hover {
    background: #ffffff;
    border-color: #98a2b3;
}
QPushButton:pressed {
    background: #eef2f6;
}
QPushButton#PrimaryButton {
    background: #0067c0;
    border: 1px solid #0067c0;
    color: white;
}
QPushButton#PrimaryButton:hover {
    background: #005ba8;
}
QPushButton#PrimaryButton:disabled {
    background: #f2f4f7;
    border: 1px solid #e4e7ec;
    color: #98a2b3;
}
QPushButton#StopButton {
    background: #fee4e2;
    border: 1px solid #fda29b;
    color: #b42318;
}
QPushButton#StopButton:hover {
    background: #fecdca;
    border-color: #f97066;
}
QPushButton#DangerButton {
    color: #b42318;
}
QPushButton:disabled {
    background: #f2f4f7;
    border: 1px solid #e4e7ec;
    color: #98a2b3;
}
QPushButton#StopButton:disabled {
    background: #f2f4f7;
    border: 1px solid #e4e7ec;
    color: #98a2b3;
}
QPushButton#DeleteRuleButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    border-radius: 6px;
    color: #b42318;
    background: #fff5f4;
    border: 1px solid #fecdca;
}
QPushButton#DeleteRuleButton:hover {
    background: #fee4e2;
    border-color: #fda29b;
}
QTabBar {
    background: #f3f6fb;
}
QTabBar[watcherState="running"] {
    background: #edfdf4;
}
QTabBar::tab {
    min-height: 34px;
    padding: 7px 18px;
    margin-right: 6px;
    border-radius: 8px;
    color: #667085;
    background: transparent;
    font-weight: 650;
}
QTabBar::tab:selected {
    color: #0067c0;
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(0, 0, 0, 0.08);
}
QScrollArea {
    border: 0;
    background: transparent;
}
QScrollBar:vertical {
    background: #e6ebf2;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #8b98aa;
    min-height: 32px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #667085;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: 0;
    height: 0;
}
QScrollBar:horizontal {
    background: #e6ebf2;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #8b98aa;
    min-width: 32px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal:hover {
    background: #667085;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    border: 0;
    width: 0;
}
QPlainTextEdit#Terminal {
    background: #101828;
    border: 0;
    border-radius: 10px;
    color: #d0e7ff;
    padding: 12px;
    font-family: "Cascadia Mono", Consolas;
    font-size: 10pt;
}
QPlainTextEdit#RuleBox {
    padding: 10px;
    font-family: "Cascadia Mono", Consolas;
    font-size: 10pt;
}
QListWidget#RuleList {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    color: #1f2937;
    padding: 6px;
    outline: 0;
}
QListWidget#RuleList::item {
    border: 0;
    margin: 2px 0;
}
QListWidget#RuleDiscoveryList {
    background: #f7fbff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    color: #1f2937;
    padding: 5px;
    outline: 0;
}
QListWidget#RuleDiscoveryList::item {
    border: 0;
    margin: 2px 0;
}
QFrame#RuleItem {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
}
QFrame#RuleSuggestionItem {
    background: #eaf4ff;
    border: 1px solid #b8d8fb;
    border-radius: 7px;
}
QFrame#RuleItem[searchMatch="true"] {
    background: #fff5c2;
    border: 1px solid #fdb022;
}
QLineEdit#RuleSearchInput,
QLineEdit#RuleAddInput {
    min-height: 36px;
}
QPushButton#AddSuggestionButton {
    min-width: 32px;
    min-height: 28px;
    padding: 2px 8px;
    color: #00539b;
    background: #ffffff;
    border: 1px solid #b8d8fb;
    border-radius: 6px;
    font-weight: 750;
}
"""


class EventBus(QObject):
    log_received = Signal(str, str, str)
    refresh_requested = Signal()


class Field:
    def __init__(self, label: QLabel, widget: QWidget) -> None:
        self.label = label
        self.widget = widget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"LM Studio Watch Dog v{__version__}")
        self.resize(1220, 780)
        self.setMinimumSize(1120, 720)

        self.config = load_config()
        self.config_lock = threading.RLock()
        self.log_queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self.pipeline_lock = threading.Lock()
        self.last_result: PipelineResult | None = None
        self.browse_buttons: list[QPushButton] = []
        self.running_locked_widgets: list[QWidget] = []
        self.stateful_widgets: list[QWidget] = []
        self._last_running_state: bool | None = None
        self._watcher_running = False
        self._loading_form = False
        self._updating_rule_editors = False
        self._form_dirty = False
        self._saved_form_state: dict[str, object] | None = None
        self.custom_presets: dict[str, dict[str, object]] = {}
        self.rule_add_inputs: dict[str, QLineEdit] = {}
        self.rule_search_inputs: dict[str, QLineEdit] = {}
        self.rule_search_labels: dict[str, QLabel] = {}
        self.rule_discovery_lists: dict[str, QListWidget] = {}
        self.rule_item_widgets: dict[str, dict[str, QFrame]] = {}
        self.rule_candidates: dict[str, list[str]] = empty_rule_candidates()
        self.default_icon = self.create_app_icon("#0067c0")
        self.running_icon = self.create_app_icon("#027a48")
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_stop_action: QAction | None = None
        self.setWindowIcon(self.default_icon)

        self.bus = EventBus()
        self.bus.log_received.connect(self.append_terminal)
        self.bus.refresh_requested.connect(self.refresh_status)

        self.watcher = PollingWatcher(self.get_config, self.run_pipeline, self.log)

        self.project_root_input = QLineEdit()
        self.project_type_input = QComboBox()
        self.custom_presets = self.clone_custom_presets(self.config.custom_presets)
        self.ensure_default_custom_preset()
        self.rebuild_project_type_options()
        self.project_type_input.setMaxVisibleItems(14)
        self.custom_preset_name_input = QLineEdit()
        self.custom_preset_name_input.setPlaceholderText("custom")
        self.output_dir_input = QLineEdit()
        self.max_file_size_input = QLineEdit()
        self.poll_interval_input = QLineEdit()
        self.debounce_input = QLineEdit()
        self.conversation_path_input = QLineEdit()
        self.sync_lmstudio_input = QCheckBox("Sync first LM Studio message")
        self.backup_conversation_input = QCheckBox("Create backup before first sync")

        self.watcher_value = QLabel("Stopped")
        self.last_run_value = QLabel("Never")
        self.last_change_value = QLabel("Never")
        self.files_merged_value = QLabel("0")
        self.structure_path_output = QLineEdit("-")
        self.merged_path_output = QLineEdit("-")

        self.exclude_dirs_text = self.rule_list()
        self.exclude_files_text = self.rule_list()
        self.exclude_globs_text = self.rule_list()
        self.exclude_extensions_text = self.rule_list()
        self.include_files_text = self.rule_list()
        self.include_extensions_text = self.rule_list()
        self.rule_editors = {
            "exclude_dirs": self.exclude_dirs_text,
            "exclude_files": self.exclude_files_text,
            "exclude_globs": self.exclude_globs_text,
            "exclude_extensions": self.exclude_extensions_text,
            "include_files": self.include_files_text,
            "include_extensions": self.include_extensions_text,
        }
        self.rule_titles = {
            "exclude_dirs": "Excluded folders",
            "exclude_files": "Excluded files",
            "exclude_globs": "Excluded globs",
            "exclude_extensions": "Excluded extensions",
            "include_files": "Included files",
            "include_extensions": "Included merge extensions",
        }
        self.rule_placeholders = {
            "exclude_dirs": "Folder name, e.g. node_modules",
            "exclude_files": "File name, e.g. package-lock.json",
            "exclude_globs": "Glob path, e.g. storage/**",
            "exclude_extensions": "Extension, e.g. .log",
            "include_files": "Relative file path, e.g. storage/app/schema.json",
            "include_extensions": "Extension to merge, e.g. .py",
        }
        self.rule_search_placeholders = {
            "exclude_dirs": "Search rules or discovered folders",
            "exclude_files": "Search rules or discovered files",
            "exclude_globs": "Search rules or discovered paths",
            "exclude_extensions": "Search rules or discovered extensions",
            "include_files": "Search included files or discovered paths",
            "include_extensions": "Search rules or discovered extensions",
        }
        self.rule_discovery_titles = {
            "exclude_dirs": "Discovered folders",
            "exclude_files": "Discovered files",
            "exclude_globs": "Discovered paths",
            "exclude_extensions": "Discovered extensions",
            "include_files": "Discovered files",
            "include_extensions": "Discovered extensions",
        }
        self.terminal = QPlainTextEdit()
        self.terminal.setObjectName("Terminal")
        self.terminal.setReadOnly(True)
        self.running_locked_widgets = [
            self.project_root_input,
            self.project_type_input,
            self.custom_preset_name_input,
            self.output_dir_input,
            self.max_file_size_input,
            self.poll_interval_input,
            self.debounce_input,
            self.conversation_path_input,
            self.sync_lmstudio_input,
            self.backup_conversation_input,
            self.exclude_dirs_text,
            self.exclude_files_text,
            self.exclude_globs_text,
            self.exclude_extensions_text,
            self.include_files_text,
            self.include_extensions_text,
        ]

        self.setStyleSheet(APP_QSS)
        self.setup_tray_icon()
        self.build_ui()
        self.connect_rule_controls()
        self.load_config_to_form(self.config)
        self.refresh_status()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(500)

        self.discovery_timer = QTimer(self)
        self.discovery_timer.setSingleShot(True)
        self.discovery_timer.timeout.connect(self.refresh_rule_suggestions)
        self.schedule_rule_discovery()

        QTimer.singleShot(120, lambda: apply_mica_window(self, dark=False))
        self.log("info", "Native WinUI-style desktop app ready.")

    def build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.stateful_widgets.append(root)
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        layout.addWidget(self.build_sidebar())
        layout.addWidget(self.build_content(), 1)

    def create_app_icon(self, color: str) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(6, 6, 52, 52, 14, 14)

        font = QFont("Segoe UI", 18)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "WD")
        painter.end()
        return QIcon(pixmap)

    def setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self.default_icon, self)
        self.tray_icon.setToolTip(f"LM Studio Watch Dog v{__version__}")

        menu = QMenu(self)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_from_tray)
        self.tray_stop_action = QAction("Stop Watcher", self)
        self.tray_stop_action.triggered.connect(self.stop_watcher)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        menu.addAction(show_action)
        menu.addAction(self.tray_stop_action)
        menu.addSeparator()
        menu.addAction(about_action)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_from_tray()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About LM Studio Watch Dog",
            (
                f"LM Studio Watch Dog\n"
                f"Version {__version__}\n\n"
                "Native PySide6 desktop app for keeping LM Studio project context updated.\n\n"
                "When the watcher is running, settings and rules are locked until it stops."
            ),
        )

    def apply_watcher_ui_state(self, running: bool) -> None:
        if self._last_running_state is running:
            return

        self._watcher_running = running
        state = "running" if running else "stopped"

        for widget in self.stateful_widgets:
            self.apply_style_state(widget, state)

        self.apply_style_state(self.watcher_card, state)
        self.apply_style_state(self.watcher_value, state)
        self.running_notice.setVisible(running)

        for widget in [*self.running_locked_widgets, *self.browse_buttons]:
            widget.setEnabled(not running)

        self.set_rule_delete_buttons_enabled(not running)
        self.set_rule_suggestion_buttons_enabled(not running)
        self.update_custom_preset_name_state()
        self.update_save_button_state()
        self.run_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

        if self.tray_stop_action:
            self.tray_stop_action.setEnabled(running)

        if self.tray_icon:
            if running:
                self.tray_icon.setIcon(self.running_icon)
                self.tray_icon.setToolTip(f"LM Studio Watch Dog v{__version__} - watcher running")
                if not self.tray_icon.isVisible():
                    self.tray_icon.show()
                if self._last_running_state is not True:
                    self.tray_icon.showMessage(
                        "LM Studio Watch Dog",
                        "Watcher is running. Settings are locked until it stops.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3500,
                    )
            else:
                self.tray_icon.setIcon(self.default_icon)
                self.tray_icon.setToolTip(f"LM Studio Watch Dog v{__version__}")
                if self.tray_icon.isVisible():
                    self.tray_icon.hide()

        self._last_running_state = running

    def apply_style_state(self, widget: QWidget, state: str) -> None:
        widget.setProperty("watcherState", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def set_rule_delete_buttons_enabled(self, enabled: bool) -> None:
        for widget in self.rule_editors.values():
            for index in range(widget.count()):
                item_widget = widget.itemWidget(widget.item(index))
                if not item_widget:
                    continue
                for button in item_widget.findChildren(QPushButton, "DeleteRuleButton"):
                    button.setEnabled(enabled)

    def set_rule_suggestion_buttons_enabled(self, enabled: bool) -> None:
        for widget in self.rule_discovery_lists.values():
            for index in range(widget.count()):
                item_widget = widget.itemWidget(widget.item(index))
                if not item_widget:
                    continue
                for button in item_widget.findChildren(QPushButton, "AddSuggestionButton"):
                    button.setEnabled(enabled)

    def build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        self.stateful_widgets.append(sidebar)
        sidebar.setFixedWidth(288)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        brand = QHBoxLayout()
        mark = QLabel("WD")
        mark.setObjectName("BrandMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(48, 48)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        title = QLabel("LM Studio")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Watch Dog")
        subtitle.setObjectName("Caption")
        version = QLabel(f"Version {__version__}")
        version.setObjectName("Caption")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_stack.addWidget(version)
        brand.addWidget(mark)
        brand.addLayout(title_stack)
        brand.addStretch(1)
        layout.addLayout(brand)

        layout.addSpacing(4)
        self.watcher_card = self.metric_card("Watcher", self.watcher_value)
        layout.addWidget(self.watcher_card)
        layout.addWidget(self.metric_card("Last run", self.last_run_value))
        layout.addWidget(self.metric_card("Last change", self.last_change_value))
        layout.addWidget(self.metric_card("Merged files", self.files_merged_value))
        layout.addSpacing(8)

        self.save_button = self.command_button("Save Settings", self.save_settings, primary=True)
        self.run_button = self.command_button("Run Once", self.run_once)
        self.start_button = self.command_button("Start Watcher", self.start_watcher)
        self.stop_button = self.command_button("Stop Watcher", self.stop_watcher)
        self.stop_button.setObjectName("StopButton")
        self.about_button = self.command_button("About", self.show_about)
        self.exit_button = self.command_button("Exit", self.close)
        self.exit_button.setObjectName("DangerButton")

        for button in [
            self.save_button,
            self.run_button,
            self.start_button,
            self.stop_button,
            self.about_button,
            self.exit_button,
        ]:
            layout.addWidget(button)

        layout.addStretch(1)
        return sidebar

    def build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("Content")
        self.stateful_widgets.append(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("HeaderCard")
        self.stateful_widgets.append(header)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(3)
        title = QLabel("Project Context Workspace")
        title.setObjectName("AppTitle")
        caption = QLabel("Build structure, merge allowed files, and sync LM Studio from one native window.")
        caption.setObjectName("AppSubtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(caption)
        content_layout.addWidget(header)

        self.running_notice = QFrame()
        self.running_notice.setObjectName("RunningNotice")
        self.running_notice.setVisible(False)
        notice_layout = QVBoxLayout(self.running_notice)
        notice_layout.setContentsMargins(14, 10, 14, 10)
        notice_layout.setSpacing(2)
        notice_title = QLabel("Watcher is running")
        notice_title.setObjectName("RunningNoticeTitle")
        notice_text = QLabel("Stop the watcher before editing settings or rules.")
        notice_text.setObjectName("RunningNoticeText")
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)
        content_layout.addWidget(self.running_notice)

        tab_bar = QTabBar()
        self.stateful_widgets.append(tab_bar)
        tab_bar.addTab("Settings")
        tab_bar.addTab("Rules")
        tab_bar.addTab("Output & Terminal")
        tab_bar.setExpanding(False)
        content_layout.addWidget(tab_bar)

        stack = QStackedWidget()
        stack.setObjectName("PageStack")
        self.stateful_widgets.append(stack)
        stack.addWidget(self.settings_page())
        stack.addWidget(self.rules_page())
        stack.addWidget(self.output_page())
        tab_bar.currentChanged.connect(stack.setCurrentIndex)
        content_layout.addWidget(stack, 1)
        return content

    def settings_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        self.stateful_widgets.append(scroll)
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("SettingsPage")
        self.stateful_widgets.append(page)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        project = self.card("Project")
        project_grid = QGridLayout()
        project_grid.setContentsMargins(0, 0, 0, 0)
        project_grid.setHorizontalSpacing(10)
        project_grid.setVerticalSpacing(10)
        project.layout().addLayout(project_grid)

        self.add_field(project_grid, 0, "Project folder", self.project_root_input, self.browse_project)
        self.add_field(project_grid, 1, "Output folder", self.output_dir_input)

        numeric_row = QHBoxLayout()
        numeric_row.setSpacing(12)
        numeric_row.addWidget(self.small_field("Max file size KB", self.max_file_size_input))
        numeric_row.addWidget(self.small_field("Poll seconds", self.poll_interval_input))
        numeric_row.addWidget(self.small_field("Debounce seconds", self.debounce_input))
        numeric_row.addStretch(1)
        project.layout().addLayout(numeric_row)

        lmstudio = self.card("LM Studio")
        lm_grid = QGridLayout()
        lm_grid.setContentsMargins(0, 0, 0, 0)
        lm_grid.setHorizontalSpacing(10)
        lm_grid.setVerticalSpacing(10)
        lmstudio.layout().addLayout(lm_grid)
        self.add_field(lm_grid, 0, "Conversation JSON", self.conversation_path_input, self.browse_conversation)
        lmstudio.layout().addWidget(self.sync_lmstudio_input)
        lmstudio.layout().addWidget(self.backup_conversation_input)

        page_layout.addWidget(project)
        page_layout.addWidget(lmstudio)
        page_layout.addStretch(1)
        scroll.setWidget(page)
        return scroll

    def rules_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("RulesScroll")
        self.stateful_widgets.append(scroll)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        page = QWidget()
        page.setObjectName("RulesPage")
        self.stateful_widgets.append(page)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(18)

        page_layout.addWidget(self.preset_card())

        rules_grid = QGridLayout()
        rules_grid.setContentsMargins(0, 0, 0, 0)
        rules_grid.setHorizontalSpacing(18)
        rules_grid.setVerticalSpacing(20)
        rules_grid.addWidget(self.rule_card("exclude_dirs"), 0, 0)
        rules_grid.addWidget(self.rule_card("exclude_files"), 0, 1)
        rules_grid.addWidget(self.rule_card("exclude_globs"), 1, 0)
        rules_grid.addWidget(self.rule_card("exclude_extensions"), 1, 1)
        rules_grid.addWidget(self.rule_card("include_files"), 2, 0, 1, 2)
        rules_grid.addWidget(self.rule_card("include_extensions"), 3, 0, 1, 2)
        rules_grid.setColumnStretch(0, 1)
        rules_grid.setColumnStretch(1, 1)
        page_layout.addLayout(rules_grid)
        scroll.setWidget(page)
        return scroll

    def output_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("OutputPage")
        self.stateful_widgets.append(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        generated = self.card("Generated Files")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        generated.layout().addLayout(grid)

        self.structure_path_output.setReadOnly(True)
        self.merged_path_output.setReadOnly(True)
        self.add_field(grid, 0, "Structure file", self.structure_path_output)
        self.add_field(grid, 1, "Merged file", self.merged_path_output)

        terminal_card = self.card("Terminal")
        terminal_card.layout().addWidget(self.terminal, 1)

        layout.addWidget(generated)
        layout.addWidget(terminal_card, 1)
        return page

    def preset_card(self) -> QFrame:
        frame = self.card("Project Preset")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        frame.layout().addLayout(grid)

        preset_row = QWidget()
        preset_layout = QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(10)
        preset_layout.addWidget(self.project_type_input, 1)
        self.new_custom_preset_button = QPushButton("New Custom")
        self.delete_custom_preset_button = QPushButton("Delete Custom")
        self.new_custom_preset_button.clicked.connect(self.create_custom_preset)
        self.delete_custom_preset_button.clicked.connect(self.delete_custom_preset)
        preset_layout.addWidget(self.new_custom_preset_button)
        preset_layout.addWidget(self.delete_custom_preset_button)
        self.running_locked_widgets.extend(
            [self.new_custom_preset_button, self.delete_custom_preset_button]
        )

        self.add_field(grid, 0, "Project type", preset_row)
        self.custom_preset_name_field = self.add_field(
            grid,
            1,
            "Custom preset name",
            self.custom_preset_name_input,
        )
        return frame

    def card(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        label = QLabel(title)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)
        return frame

    def metric_card(self, title: str, value: QLabel) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatusChip")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("Caption")
        value.setObjectName("MetricValue")
        value.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value)
        return frame

    def command_button(self, text: str, handler, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        button.clicked.connect(handler)
        return button

    def small_field(self, label: str, widget: QLineEdit) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label_widget = QLabel(label)
        label_widget.setObjectName("FieldLabel")
        widget.setFixedWidth(150)
        layout.addWidget(label_widget)
        layout.addWidget(widget)
        return wrapper

    def add_field(self, grid: QGridLayout, row: int, label: str, widget: QWidget, browse_handler=None) -> Field:
        label_widget = QLabel(label)
        label_widget.setObjectName("FieldLabel")
        grid.addWidget(label_widget, row, 0)

        if browse_handler:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            row_layout.addWidget(widget, 1)
            browse = QPushButton("Browse")
            browse.clicked.connect(browse_handler)
            self.browse_buttons.append(browse)
            row_layout.addWidget(browse)
            grid.addWidget(row_widget, row, 1)
        else:
            grid.addWidget(widget, row, 1)

        grid.setColumnStretch(1, 1)
        return Field(label_widget, widget)

    def rule_list(self) -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("RuleList")
        widget.setMinimumHeight(132)
        widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        return widget

    def rule_discovery_list(self) -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("RuleDiscoveryList")
        widget.setMinimumHeight(88)
        widget.setMaximumHeight(120)
        widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        return widget

    def rule_card(self, category: str) -> QFrame:
        editor = self.rule_editors[category]
        frame = self.card(self.rule_titles[category])
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        frame.setMinimumHeight(430)

        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        search_input = QLineEdit()
        search_input.setObjectName("RuleSearchInput")
        search_status = QLabel("")
        search_status.setObjectName("Caption")
        search_input.setPlaceholderText(self.rule_search_placeholders[category])
        search_layout.addWidget(search_input, 1)
        search_layout.addWidget(search_status)
        frame.layout().addWidget(search_row)

        frame.layout().addWidget(editor, 1)

        discovery_label = QLabel(self.rule_discovery_titles[category])
        discovery_label.setObjectName("Caption")
        discovery_list = self.rule_discovery_list()
        frame.layout().addWidget(discovery_label)
        frame.layout().addWidget(discovery_list)

        add_row = QWidget()
        add_layout = QHBoxLayout(add_row)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setSpacing(10)
        add_input = QLineEdit()
        add_input.setObjectName("RuleAddInput")
        add_input.setPlaceholderText(self.rule_placeholders[category])
        add_button = QPushButton("Add")
        add_layout.addWidget(add_input, 1)
        add_layout.addWidget(add_button)
        frame.layout().addWidget(add_row)

        self.rule_search_inputs[category] = search_input
        self.rule_search_labels[category] = search_status
        self.rule_add_inputs[category] = add_input
        self.rule_discovery_lists[category] = discovery_list
        self.running_locked_widgets.extend([add_input, add_button, discovery_list])

        search_input.textChanged.connect(lambda _text, key=category: self.update_rule_search(key))
        discovery_list.itemDoubleClicked.connect(
            lambda item, key=category: self.add_rule_value(key, str(item.data(Qt.ItemDataRole.UserRole) or ""))
        )
        add_button.clicked.connect(lambda _checked=False, key=category: self.add_rule_item(key))
        add_input.returnPressed.connect(lambda key=category: self.add_rule_item(key))

        return frame

    def connect_rule_controls(self) -> None:
        self.project_type_input.currentIndexChanged.connect(
            lambda _index: self.handle_project_type_changed(self.current_project_type())
        )

        text_inputs = [
            self.project_root_input,
            self.output_dir_input,
            self.max_file_size_input,
            self.poll_interval_input,
            self.debounce_input,
            self.conversation_path_input,
        ]
        for widget in text_inputs:
            widget.textChanged.connect(lambda _text: self.mark_form_dirty())
        self.project_root_input.textChanged.connect(lambda _text: self.schedule_rule_discovery())

        self.custom_preset_name_input.textChanged.connect(self.handle_custom_preset_name_changed)
        self.sync_lmstudio_input.stateChanged.connect(lambda _state: self.mark_form_dirty())
        self.backup_conversation_input.stateChanged.connect(lambda _state: self.mark_form_dirty())

    def schedule_rule_discovery(self) -> None:
        if hasattr(self, "discovery_timer"):
            self.discovery_timer.start(300)

    def refresh_rule_suggestions(self) -> None:
        self.rule_candidates = discover_rule_candidates(self.project_root_input.text().strip())
        for category in self.rule_editors:
            self.update_rule_search(category)

    def clone_custom_presets(self, presets: object) -> dict[str, dict[str, object]]:
        normalized = normalize_custom_presets(presets)
        return {
            key: self.custom_preset_payload(str(preset.get("name") or "custom"), preset)
            for key, preset in normalized.items()
        }

    def custom_preset_payload(
        self,
        name: str,
        rules: dict[str, object] | None = None,
    ) -> dict[str, object]:
        rules = rules or {}
        payload: dict[str, object] = {"name": (name.strip() or "custom")[:64]}
        for category in RULE_CATEGORIES:
            values = rules.get(category, [])
            payload[category] = list(values) if isinstance(values, list) else []
        return payload

    def ensure_default_custom_preset(self) -> None:
        if "custom" not in self.custom_presets:
            self.custom_presets["custom"] = self.custom_preset_payload("custom")

    def custom_preset_fallback_name(self, project_type: str) -> str:
        if project_type == "custom":
            return "custom"
        if project_type.startswith("custom:"):
            return project_type.split(":", 1)[1] or "custom"
        return "custom"

    def custom_preset_name_for_key(self, project_type: str) -> str:
        preset = self.custom_presets.get(project_type, {})
        name = str(preset.get("name") or "").strip()
        return name or self.custom_preset_fallback_name(project_type)

    def rebuild_project_type_options(self, selected: str | None = None) -> None:
        current = selected or (self.current_project_type() if self.project_type_input.count() else "generic")
        self.ensure_default_custom_preset()

        self.project_type_input.blockSignals(True)
        try:
            self.project_type_input.clear()
            for project_type in PROJECT_TYPES:
                if project_type == "custom":
                    continue
                self.project_type_input.addItem(project_type, project_type)

            self.project_type_input.insertSeparator(self.project_type_input.count())
            for key, preset in self.custom_presets.items():
                self.project_type_input.addItem(
                    str(preset.get("name") or self.custom_preset_fallback_name(key)),
                    key,
                )

            index = self.project_type_input.findData(current)
            if index < 0:
                index = self.project_type_input.findData("generic")
            self.project_type_input.setCurrentIndex(max(index, 0))
        finally:
            self.project_type_input.blockSignals(False)

    def current_project_type(self) -> str:
        value = self.project_type_input.currentData()
        return str(value or self.project_type_input.currentText() or "generic")

    def set_project_type(self, project_type: str) -> None:
        if is_custom_project_type(project_type) and self.project_type_input.findData(project_type) < 0:
            self.custom_presets[project_type] = self.custom_preset_payload(
                self.custom_preset_fallback_name(project_type)
            )
            self.rebuild_project_type_options(project_type)
            return

        index = self.project_type_input.findData(project_type)
        if index < 0:
            index = self.project_type_input.findData("generic")
        self.project_type_input.setCurrentIndex(max(index, 0))

    def custom_preset_display_name(self) -> str:
        project_type = self.current_project_type()
        return self.custom_preset_name_input.text().strip() or self.custom_preset_fallback_name(project_type)

    def refresh_custom_project_type_label(self) -> None:
        project_type = self.current_project_type()
        if not is_custom_project_type(project_type):
            return

        index = self.project_type_input.findData(project_type)
        if index >= 0:
            self.project_type_input.setItemText(index, self.custom_preset_display_name())

    def handle_custom_preset_name_changed(self, _text: str) -> None:
        if self._loading_form or self._updating_rule_editors:
            return
        if not is_custom_project_type(self.current_project_type()):
            return
        self.sync_current_custom_preset()
        self.refresh_custom_project_type_label()
        self.mark_form_dirty()

    def update_custom_preset_name_state(self) -> None:
        enabled = is_custom_project_type(self.current_project_type())
        self.custom_preset_name_input.setEnabled(enabled and not self._watcher_running)
        if hasattr(self, "custom_preset_name_field"):
            self.custom_preset_name_field.label.setEnabled(enabled)
        if hasattr(self, "new_custom_preset_button"):
            self.new_custom_preset_button.setEnabled(not self._watcher_running)
        if hasattr(self, "delete_custom_preset_button"):
            self.delete_custom_preset_button.setEnabled(
                enabled and not self._watcher_running and len(self.custom_presets) > 1
            )

    def current_form_state(self) -> dict[str, object]:
        return self.form_to_config().to_dict()

    def mark_form_dirty(self) -> None:
        if self._loading_form or self._updating_rule_editors:
            return
        if self._saved_form_state is None:
            self._form_dirty = True
        else:
            self._form_dirty = self.current_form_state() != self._saved_form_state
        self.update_save_button_state()

    def set_form_clean(self) -> None:
        self._saved_form_state = self.current_form_state()
        self._form_dirty = False
        self.update_save_button_state()

    def update_save_button_state(self) -> None:
        if hasattr(self, "save_button"):
            self.save_button.setEnabled((not self._watcher_running) and self._form_dirty)

    def handle_project_type_changed(self, project_type: str) -> None:
        if self._loading_form or self._updating_rule_editors:
            return
        if is_custom_project_type(project_type):
            self.load_custom_preset_rules(project_type)
        elif project_type:
            self.apply_preset_rules(project_type)
        self.update_custom_preset_name_state()
        self.mark_form_dirty()

    def mark_rules_changed(self) -> None:
        if self._loading_form or self._updating_rule_editors:
            return
        if not is_custom_project_type(self.current_project_type()):
            key, name = self.next_custom_preset_identity(prefer_empty_default=True)
            self.custom_presets[key] = self.custom_preset_payload(name, self.current_rule_payload())
            self.rebuild_project_type_options(key)

            self.custom_preset_name_input.blockSignals(True)
            self.custom_preset_name_input.setText(name)
            self.custom_preset_name_input.blockSignals(False)
            self.update_custom_preset_name_state()
            self.refresh_custom_project_type_label()
            self.log("info", "Rules changed; project type switched to custom.")
        else:
            self.sync_current_custom_preset()
            self.refresh_custom_project_type_label()
        self.mark_form_dirty()

    def custom_preset_has_rules(self, project_type: str) -> bool:
        preset = self.custom_presets.get(project_type, {})
        return any(bool(preset.get(category)) for category in RULE_CATEGORIES)

    def can_reuse_default_custom_preset(self) -> bool:
        preset = self.custom_presets.get("custom")
        if not preset:
            return True
        return (
            self.custom_preset_name_for_key("custom").lower() == "custom"
            and not self.custom_preset_has_rules("custom")
        )

    def next_custom_preset_identity(self, prefer_empty_default: bool = False) -> tuple[str, str]:
        if prefer_empty_default and self.can_reuse_default_custom_preset():
            return "custom", "custom"

        existing_keys = set(self.custom_presets)
        existing_names = {
            self.custom_preset_name_for_key(key).strip().lower()
            for key in self.custom_presets
        }
        index = 2
        while True:
            name = f"custom{index}"
            key = f"custom:{name}"
            if key not in existing_keys and name.lower() not in existing_names:
                return key, name
            index += 1

    def current_rule_payload(self) -> dict[str, object]:
        return {category: self.get_rule_lines(category) for category in RULE_CATEGORIES}

    def config_rule_payload(self, config: AppConfig) -> dict[str, object]:
        return {
            "exclude_dirs": list(config.exclude_dirs),
            "exclude_files": list(config.exclude_files),
            "exclude_globs": list(config.exclude_globs),
            "exclude_extensions": list(config.exclude_extensions),
            "include_files": list(config.include_files),
            "include_extensions": list(config.include_extensions),
        }

    def load_custom_presets_from_config(self, config: AppConfig) -> None:
        self.custom_presets = self.clone_custom_presets(config.custom_presets)
        if is_custom_project_type(config.project_type) and config.project_type not in self.custom_presets:
            self.custom_presets[config.project_type] = self.custom_preset_payload(
                config.custom_preset_name,
                self.config_rule_payload(config),
            )
        self.ensure_default_custom_preset()
        self.rebuild_project_type_options(config.project_type)

    def sync_current_custom_preset(self) -> None:
        project_type = self.current_project_type()
        if not is_custom_project_type(project_type):
            return
        self.custom_presets[project_type] = self.custom_preset_payload(
            self.custom_preset_display_name(),
            self.current_rule_payload(),
        )

    def load_custom_preset_rules(self, project_type: str) -> None:
        if project_type not in self.custom_presets:
            self.custom_presets[project_type] = self.custom_preset_payload(
                self.custom_preset_fallback_name(project_type)
            )

        preset = self.custom_presets[project_type]
        self.custom_preset_name_input.blockSignals(True)
        self.custom_preset_name_input.setText(self.custom_preset_name_for_key(project_type))
        self.custom_preset_name_input.blockSignals(False)
        self.refresh_custom_project_type_label()

        self._updating_rule_editors = True
        try:
            for category in RULE_CATEGORIES:
                values = preset.get(category, [])
                self.set_rule_items(category, list(values) if isinstance(values, list) else [])
        finally:
            self._updating_rule_editors = False

        for category in RULE_CATEGORIES:
            self.update_rule_search(category)

    def create_custom_preset(self) -> None:
        if self._watcher_running:
            return

        self.sync_current_custom_preset()
        key, name = self.next_custom_preset_identity(prefer_empty_default=True)
        self.custom_presets[key] = self.custom_preset_payload(name, self.current_rule_payload())
        self.rebuild_project_type_options(key)
        self.load_custom_preset_rules(key)
        self.update_custom_preset_name_state()
        self.mark_form_dirty()
        self.log("info", f"Custom preset created: {name}")

    def delete_custom_preset(self) -> None:
        if self._watcher_running:
            return

        project_type = self.current_project_type()
        if not is_custom_project_type(project_type) or len(self.custom_presets) <= 1:
            return

        name = self.custom_preset_name_for_key(project_type)
        reply = QMessageBox.question(
            self,
            "Delete custom preset",
            f"Delete custom preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.custom_presets.pop(project_type, None)
        self.rebuild_project_type_options("generic")
        self.apply_preset_rules("generic")
        self.custom_preset_name_input.clear()
        self.update_custom_preset_name_state()
        self.mark_form_dirty()
        self.log("info", f"Custom preset deleted: {name}")

    def apply_preset_rules(self, project_type: str) -> None:
        rules = preset_rule_lists(project_type)
        self._updating_rule_editors = True
        try:
            for category in self.rule_editors:
                self.set_rule_items(category, rules.get(category, []))
        finally:
            self._updating_rule_editors = False

        for category in self.rule_editors:
            self.update_rule_search(category)

    def add_rule_value(self, category: str, raw_value: str) -> bool:
        value = self.normalize_rule_item(category, raw_value)
        if not value:
            return False

        existing = {
            self.rule_key(category, line)
            for line in self.get_lines(self.rule_editors[category])
        }
        if self.rule_key(category, value) in existing:
            QMessageBox.warning(
                self,
                "Duplicate rule",
                f"{self.rule_titles[category]} already contains:\n\n{value}",
            )
            self.select_rule_item(category, value)
            return False

        self.append_rule_item(category, value)
        self.mark_rules_changed()
        return True

    def add_rule_item(self, category: str) -> None:
        add_input = self.rule_add_inputs[category]
        if self.add_rule_value(category, add_input.text()):
            add_input.clear()

    def update_rule_search(self, category: str) -> None:
        widget = self.rule_editors[category]
        search_input = self.rule_search_inputs.get(category)
        search_label = self.rule_search_labels.get(category)
        if not search_input:
            return

        query = search_input.text().strip().lower()
        visible_count = 0
        for index in range(widget.count()):
            item = widget.item(index)
            value = str(item.data(Qt.ItemDataRole.UserRole) or "")
            matches = not query or query in value.lower()
            item.setHidden(not matches)
            if matches:
                visible_count += 1

            row_widget = widget.itemWidget(item)
            if row_widget:
                row_widget.setProperty("searchMatch", bool(query and matches))
                row_widget.style().unpolish(row_widget)
                row_widget.style().polish(row_widget)
                row_widget.update()

        if search_label:
            if not query:
                search_label.setText("")
            else:
                search_label.setText(
                    f"{visible_count} item" if visible_count == 1 else f"{visible_count} items"
                )
        self.update_rule_suggestions(category, query)

    def update_rule_suggestions(self, category: str, query: str | None = None) -> None:
        widget = self.rule_discovery_lists.get(category)
        if not widget:
            return

        if query is None:
            search_input = self.rule_search_inputs.get(category)
            query = search_input.text().strip().lower() if search_input else ""

        existing = {
            self.rule_key(category, line)
            for line in self.get_lines(self.rule_editors[category])
        }
        values = []
        seen: set[str] = set()
        for raw_value in self.rule_candidates.get(category, []):
            value = self.normalize_rule_item(category, raw_value)
            key = self.rule_key(category, value)
            if not value or key in existing or key in seen:
                continue
            if query and query not in value.lower():
                continue
            seen.add(key)
            values.append(value)
            if len(values) >= 60:
                break

        widget.clear()
        if not values:
            item = QListWidgetItem("No discovered matches" if query else "No discovered items")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            widget.addItem(item)
            return

        for value in values:
            self.append_rule_suggestion(category, value)

    def append_rule_suggestion(self, category: str, value: str) -> None:
        widget = self.rule_discovery_lists[category]

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, value)

        row = QFrame()
        row.setObjectName("RuleSuggestionItem")
        row.setMinimumHeight(34)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 4, 6, 4)
        row_layout.setSpacing(8)

        label = QLabel(value)
        label.setObjectName("RuleItemText")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)

        add_button = QPushButton("+")
        add_button.setObjectName("AddSuggestionButton")
        add_button.setToolTip("Add discovered rule")
        add_button.clicked.connect(lambda _checked=False, raw=value: self.add_rule_value(category, raw))
        add_button.setEnabled(not self._watcher_running)

        row_layout.addWidget(label, 1)
        row_layout.addWidget(add_button)

        widget.addItem(item)
        item.setSizeHint(row.sizeHint())
        widget.setItemWidget(item, row)

    def normalize_rule_item(self, category: str, value: str) -> str:
        text = value.strip()
        if not text:
            return ""
        if category == "exclude_globs":
            return text.replace("\\", "/")
        if category == "include_files":
            normalized = text.replace("\\", "/")
            while normalized.startswith("./"):
                normalized = normalized[2:]
            return normalized
        if category in {"exclude_extensions", "include_extensions"}:
            normalized = text.lower()
            if not normalized.startswith("."):
                normalized = "." + normalized
            return normalized
        return text

    def rule_key(self, category: str, value: str) -> str:
        return self.normalize_rule_item(category, value).lower()

    def find_duplicate_rule(self) -> tuple[str, str] | None:
        for category, editor in self.rule_editors.items():
            seen: set[str] = set()
            for line in self.get_lines(editor):
                key = self.rule_key(category, line)
                if not key:
                    continue
                if key in seen:
                    return category, self.normalize_rule_item(category, line)
                seen.add(key)
        return None

    def validate_rule_lists(self) -> bool:
        duplicate = self.find_duplicate_rule()
        if not duplicate:
            return True

        category, value = duplicate
        QMessageBox.warning(
            self,
            "Duplicate rule",
            f"{self.rule_titles[category]} has a duplicate entry:\n\n{value}",
        )
        self.select_rule_item(category, value)
        return False

    def select_rule_item(self, category: str, value: str) -> None:
        widget = self.rule_editors[category]
        search_input = self.rule_search_inputs.get(category)
        if search_input:
            search_input.clear()

        target = self.rule_key(category, value)
        for index in range(widget.count()):
            item = widget.item(index)
            if self.rule_key(category, str(item.data(Qt.ItemDataRole.UserRole) or "")) == target:
                widget.setCurrentItem(item)
                widget.scrollToItem(item)
                widget.setFocus()
                return

    def set_rule_items(self, category: str, values: list[str]) -> None:
        widget = self.rule_editors[category]
        widget.clear()
        self.rule_item_widgets[category] = {}

        seen: set[str] = set()
        for raw_value in values:
            value = self.normalize_rule_item(category, raw_value)
            key = self.rule_key(category, value)
            if not value or key in seen:
                continue
            self.append_rule_item(category, value)
            seen.add(key)

    def append_rule_item(self, category: str, value: str) -> None:
        widget = self.rule_editors[category]
        key = self.rule_key(category, value)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, value)

        row = QFrame()
        row.setObjectName("RuleItem")
        row.setMinimumHeight(38)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 8, 6)
        row_layout.setSpacing(8)

        label = QLabel(value)
        label.setObjectName("RuleItemText")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        delete_button = QPushButton("X")
        delete_button.setObjectName("DeleteRuleButton")
        delete_button.setToolTip("Remove rule")
        delete_button.clicked.connect(lambda _checked=False, key=key: self.remove_rule_item(category, key))
        delete_button.setEnabled(not self._watcher_running)

        row_layout.addWidget(label, 1)
        row_layout.addWidget(delete_button)

        widget.addItem(item)
        item.setSizeHint(row.sizeHint())
        widget.setItemWidget(item, row)
        self.rule_item_widgets.setdefault(category, {})[key] = row
        self.update_rule_search(category)

    def remove_rule_item(self, category: str, key: str) -> None:
        widget = self.rule_editors[category]
        for index in range(widget.count()):
            item = widget.item(index)
            if self.rule_key(category, str(item.data(Qt.ItemDataRole.UserRole) or "")) == key:
                widget.takeItem(index)
                self.rule_item_widgets.get(category, {}).pop(key, None)
                self.update_rule_search(category)
                self.mark_rules_changed()
                return

    def load_config_to_form(self, config: AppConfig) -> None:
        self._loading_form = True
        try:
            self.load_custom_presets_from_config(config)
            self.project_root_input.setText(config.project_root)
            self.set_project_type(config.project_type)
            if is_custom_project_type(config.project_type):
                self.load_custom_preset_rules(config.project_type)
            else:
                self.custom_preset_name_input.setText(config.custom_preset_name)
            self.output_dir_input.setText(config.output_dir)
            self.max_file_size_input.setText(str(config.max_file_size_kb))
            self.poll_interval_input.setText(str(config.poll_interval_seconds))
            self.debounce_input.setText(str(config.debounce_seconds))
            self.conversation_path_input.setText(config.conversation_path)
            self.sync_lmstudio_input.setChecked(config.sync_lmstudio)
            self.backup_conversation_input.setChecked(config.backup_conversation)

            has_saved_rules = any(
                [
                    config.exclude_dirs,
                    config.exclude_files,
                    config.exclude_globs,
                    config.exclude_extensions,
                    config.include_files,
                    config.include_extensions,
                ]
            )
            if is_custom_project_type(config.project_type):
                pass
            elif has_saved_rules:
                self.set_rule_items("exclude_dirs", config.exclude_dirs)
                self.set_rule_items("exclude_files", config.exclude_files)
                self.set_rule_items("exclude_globs", config.exclude_globs)
                self.set_rule_items("exclude_extensions", config.exclude_extensions)
                self.set_rule_items("include_files", config.include_files)
                self.set_rule_items("include_extensions", config.include_extensions)
            else:
                self.apply_preset_rules(config.project_type)
        finally:
            self._loading_form = False

        self.update_custom_preset_name_state()
        for category in self.rule_editors:
            self.update_rule_search(category)
        self.set_form_clean()

    def form_to_config(self) -> AppConfig:
        self.sync_current_custom_preset()
        project_type = self.current_project_type()
        custom_preset_name = (
            self.custom_preset_display_name()
            if is_custom_project_type(project_type)
            else self.custom_preset_name_input.text()
        )
        config = AppConfig(
            project_root=self.project_root_input.text(),
            project_type=project_type,
            custom_preset_name=custom_preset_name,
            custom_presets=self.clone_custom_presets(self.custom_presets),
            output_dir=self.output_dir_input.text(),
            conversation_path=self.conversation_path_input.text(),
            sync_lmstudio=self.sync_lmstudio_input.isChecked(),
            backup_conversation=self.backup_conversation_input.isChecked(),
            poll_interval_seconds=self.poll_interval_input.text(),
            debounce_seconds=self.debounce_input.text(),
            max_file_size_kb=self.max_file_size_input.text(),
            exclude_dirs=self.get_rule_lines("exclude_dirs"),
            exclude_files=self.get_rule_lines("exclude_files"),
            exclude_globs=self.get_rule_lines("exclude_globs"),
            exclude_extensions=self.get_rule_lines("exclude_extensions"),
            include_files=self.get_rule_lines("include_files"),
            include_extensions=self.get_rule_lines("include_extensions"),
        )
        config.normalize()
        return config

    def set_lines(self, widget: QWidget, values: list[str]) -> None:
        if isinstance(widget, QListWidget):
            for category, rule_widget in self.rule_editors.items():
                if widget is rule_widget:
                    self.set_rule_items(category, values)
                    return
        widget.setPlainText("\n".join(values))

    def get_lines(self, widget: QWidget) -> list[str]:
        if isinstance(widget, QListWidget):
            return [
                str(widget.item(index).data(Qt.ItemDataRole.UserRole) or "").strip()
                for index in range(widget.count())
                if str(widget.item(index).data(Qt.ItemDataRole.UserRole) or "").strip()
            ]
        return [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]

    def get_rule_lines(self, category: str) -> list[str]:
        lines = []
        seen: set[str] = set()
        for line in self.get_lines(self.rule_editors[category]):
            normalized = self.normalize_rule_item(category, line)
            key = normalized.lower()
            if normalized and key not in seen:
                lines.append(normalized)
                seen.add(key)
        return lines

    def browse_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select project folder")
        if selected:
            self.project_root_input.setText(selected)

    def browse_conversation(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select LM Studio conversation JSON",
            "",
            "Conversation JSON (*.conversation.json);;JSON files (*.json);;All files (*.*)",
        )
        if selected:
            self.conversation_path_input.setText(selected)

    def save_settings(self) -> bool:
        if not self.validate_rule_lists():
            return False
        if not self._form_dirty:
            return True

        try:
            with self.config_lock:
                self.config = self.form_to_config()
                path = save_config(self.config)
        except OSError as exc:
            self.log("error", f"Settings save failed: {exc}")
            QMessageBox.warning(
                self,
                "LM Studio Watch Dog",
                (
                    "Could not save settings.\n\n"
                    f"{exc}\n\n"
                    "Close any editor or another app instance that may be using data/config.json, "
                    "then try again."
                ),
            )
            return False

        self.log("info", f"Settings saved: {path}")
        self.set_form_clean()
        self.refresh_status()
        return True

    def get_config(self) -> AppConfig:
        with self.config_lock:
            return AppConfig.from_dict(self.config.to_dict())

    def run_once(self) -> None:
        if not self.save_settings():
            return
        threading.Thread(target=lambda: self.run_pipeline("manual run"), daemon=True).start()

    def run_pipeline(self, reason: str) -> PipelineResult:
        if not self.pipeline_lock.acquire(blocking=False):
            result = PipelineResult(False, messages=["Pipeline is already running."])
            self.log("warning", "Pipeline skipped: another run is active.")
            return result

        try:
            self.log("info", f"Pipeline started ({reason}).")
            result = run_pipeline(self.get_config(), logger=lambda message: self.log("info", message))
            self.last_result = result
            if result.ok:
                self.log("info", "Pipeline finished successfully.")
            else:
                self.log("error", "Pipeline finished with errors.")
            self.bus.refresh_requested.emit()
            return result
        finally:
            self.pipeline_lock.release()

    def start_watcher(self) -> None:
        if not self.save_settings():
            return
        started = self.watcher.start()
        if not started:
            self.log("warning", "Watcher is already running.")
        self.refresh_status()

    def stop_watcher(self) -> None:
        stopped = self.watcher.stop()
        if not stopped:
            self.log("warning", "Watcher is not running.")
        self.refresh_status()

    def log(self, level: str, message: str) -> None:
        self.log_queue.put((time.strftime("%H:%M:%S"), level.upper(), message))
        self.flush_logs()

    def flush_logs(self) -> None:
        while True:
            try:
                timestamp, level, message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.bus.log_received.emit(timestamp, level, message)

    def append_terminal(self, timestamp: str, level: str, message: str) -> None:
        self.terminal.appendPlainText(f"[{timestamp}] {level} {message}")

    def refresh_status(self) -> None:
        status = self.watcher.status()
        self.watcher_value.setText("Running" if status.running else "Stopped")
        self.last_run_value.setText(status.last_run_at or "Never")
        self.last_change_value.setText(status.last_change_at or "Never")
        self.apply_watcher_ui_state(status.running)

        if self.last_result:
            result = asdict(self.last_result)
            self.files_merged_value.setText(str(result.get("files_merged", 0)))
            self.structure_path_output.setText(result.get("structure_path") or "-")
            self.merged_path_output.setText(result.get("merged_path") or "-")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        try:
            if self.watcher.status().running:
                self.watcher.stop()
            if self.tray_icon:
                self.tray_icon.hide()
            if self._form_dirty:
                with self.config_lock:
                    self.config = self.form_to_config()
                    save_config(self.config)
        except Exception as exc:
            QMessageBox.warning(self, "LM Studio Watch Dog", f"Could not save settings: {exc}")
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LM Studio Watch Dog")
    app.setApplicationVersion(__version__)
    app.setFont(QFont("Segoe UI Variable Text", 10))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
