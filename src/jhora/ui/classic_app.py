"""ASTROSOFT Classic desktop shell for the PyJHora application."""

import json
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QFontDatabase, QPainter, QKeySequence
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jhora import const, utils
from jhora.ui.horo_chart_tabs import ChartTabbed


_FILE_FILTER = "ASTROSOFT horoscope (*.astrosoft.json);;JSON files (*.json)"


def _preferred_application_font():
    available = set(QFontDatabase().families())
    for family in ("Noto Sans Sinhala", "Iskoola Pota", "Nirmala UI"):
        if family in available:
            return QFont(family, 9)
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)


class AstrosoftMainWindow(QMainWindow):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)
        self.language = language if language in const.available_languages else "English"
        self._documents = {}
        self.setWindowTitle("ASTROSOFT - Classic Edition")
        self.setWindowIcon(QApplication.windowIcon())
        self.resize(1280, 820)
        self.setMinimumSize(900, 600)
        QApplication.setFont(_preferred_application_font())

        self._build_workspace()
        self._build_menus()
        self._build_toolbar()
        self._connect_document_events()
        self._new_horoscope()
        self.statusBar().showMessage("Ready", 3000)

    def _build_workspace(self):
        self.workspace = QSplitter(Qt.Orientation.Horizontal, self)
        self.workspace.setChildrenCollapsible(False)

        self.navigation = QTreeWidget()
        self.navigation.setHeaderHidden(True)
        self.navigation.setMinimumWidth(175)
        self.navigation.setMaximumWidth(360)
        self.navigation.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.navigation.customContextMenuRequested.connect(self._show_navigation_menu)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)
        birth_group = QGroupBox("Birth Details")
        birth_layout = QFormLayout(birth_group)
        self.birth_values = {}
        for label in ("Name", "Date", "Time", "Place", "Latitude", "Longitude", "Time zone"):
            value = QLabel("-")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            birth_layout.addRow(label + ":", value)
            self.birth_values[label] = value
        left_layout.addWidget(birth_group)
        nav_group = QGroupBox("Horoscope Views")
        nav_layout = QVBoxLayout(nav_group)
        nav_layout.addWidget(self.navigation)
        left_layout.addWidget(nav_group, 1)

        self.documents = QTabWidget()
        self.documents.setDocumentMode(False)
        self.documents.setTabsClosable(True)
        self.documents.setMovable(True)
        self.documents.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.documents.customContextMenuRequested.connect(self._show_document_menu)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        self.positions = QTableWidget(0, 3)
        self.positions.setHorizontalHeaderLabels(["Planet", "House", "Sign / Position"])
        self.positions.setAlternatingRowColors(True)
        self.positions.setSortingEnabled(True)
        self.positions.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.positions.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.positions.horizontalHeader().setStretchLastSection(True)
        self.positions.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.positions.customContextMenuRequested.connect(self._show_positions_menu)
        position_group = QGroupBox("Planetary Positions")
        position_layout = QVBoxLayout(position_group)
        position_layout.addWidget(self.positions)
        right_layout.addWidget(position_group, 1)
        self.details = QLabel("Calculate a horoscope to view chart details.")
        self.details.setWordWrap(True)
        detail_group = QGroupBox("Selected Chart")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(self.details)
        right_layout.addWidget(detail_group)

        self.workspace.addWidget(left_panel)
        self.workspace.addWidget(self.documents)
        self.workspace.addWidget(right_panel)
        self.workspace.setStretchFactor(0, 0)
        self.workspace.setStretchFactor(1, 1)
        self.workspace.setStretchFactor(2, 0)
        self.workspace.setSizes([220, 780, 280])
        self.setCentralWidget(self.workspace)

    def _action(self, text, slot, shortcut=None, icon=None, checkable=False):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if icon is not None:
            action.setIcon(self.style().standardIcon(icon))
        action.setCheckable(checkable)
        return action

    def _build_menus(self):
        bar = self.menuBar()
        self.file_menu = bar.addMenu("&File")
        self.edit_menu = bar.addMenu("&Edit")
        self.view_menu = bar.addMenu("&View")
        self.charts_menu = bar.addMenu("&Charts")
        self.calculations_menu = bar.addMenu("&Calculations")
        self.dasha_menu = bar.addMenu("&Dasha")
        self.panchangam_menu = bar.addMenu("&Panchangam")
        self.reports_menu = bar.addMenu("&Reports")
        self.tools_menu = bar.addMenu("&Tools")
        self.settings_menu = bar.addMenu("&Settings")
        self.help_menu = bar.addMenu("&Help")

        self.new_action = self._action("New Horoscope", self._new_horoscope, "Ctrl+N")
        self.open_action = self._action("Open Horoscope...", self._open_horoscope, "Ctrl+O")
        self.save_action = self._action("Save Horoscope", self._save_horoscope, "Ctrl+S")
        self.save_as_action = self._action("Save Horoscope As...", self._save_horoscope_as, "Ctrl+Shift+S")
        self.print_action = self._action("Print...", self._print_horoscope, "Ctrl+P")
        self.preview_action = self._action("Print Preview...", self._print_preview)
        self.pdf_action = self._action("Export PDF...", self._export_pdf)
        self.file_menu.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
        self.file_menu.addSeparator()
        self.file_menu.addActions([self.preview_action, self.print_action, self.pdf_action])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self._action("Exit", self.close, "Alt+F4"))

        self.edit_menu.addAction(self._action("Compute Horoscope", self._compute_horoscope, "F5"))
        self.edit_menu.addAction(self._action("Close Horoscope", self._close_current_document, "Ctrl+W"))
        self.view_menu.addAction(self._action("Refresh View", self._refresh_active_view, "F6"))
        self.view_menu.addAction(self._action("Reset Panel Sizes", self._reset_panel_sizes))

        self.charts_menu.addAction(self._action("D1 Rasi", lambda: self._select_chart_factor(1)))
        self.charts_menu.addAction(self._action("D9 Navamsa", lambda: self._select_chart_factor(9)))
        divisional_menu = self.charts_menu.addMenu("Divisional Charts")
        for style, label in (
            (const.CHART_STYLE.SOUTH_INDIAN_REGULAR, "South Indian"),
            (const.CHART_STYLE.NORTH_INDIAN, "North Indian"),
            (const.CHART_STYLE.EAST_INDIAN_WITH_FRAME, "East Indian"),
        ):
            divisional_menu.addAction(
                self._action(label, lambda _checked=False, value=style: self._set_chart_style(value))
            )
        divisional_menu.addSeparator()
        factors = (
            (2, "D2 Hora"), (3, "D3 Drekkana"), (4, "D4 Chaturthamsa"),
            (7, "D7 Saptamsa"), (10, "D10 Dasamsa"), (12, "D12 Dwadasamsa"),
            (16, "D16 Shodasamsa"), (20, "D20 Vimsamsa"), (24, "D24 Chaturvimsamsa"),
            (27, "D27 Nakshatramsa"), (30, "D30 Trimsamsa"), (40, "D40 Khavedamsa"),
            (45, "D45 Akshavedamsa"), (60, "D60 Shashtiamsa"),
        )
        for factor, label in factors:
            divisional_menu.addAction(
                self._action(label, lambda _checked=False, value=factor: self._select_chart_factor(value))
            )

        self.calculations_menu.addAction(self._action("Compute Horoscope", self._compute_horoscope, "F5"))
        self.calculations_menu.addAction(self._action("Planetary Positions", self._show_positions))
        self.dasha_menu.addAction(self._action("Dasha Periods", lambda: self._select_view("vimsottari_str")))
        self.panchangam_menu.addAction(self._action("Panchangam", lambda: self._select_view("panchangam_str")))
        self.reports_menu.addActions([self.preview_action, self.print_action, self.pdf_action])
        self.tools_menu.addAction(self._action("Options...", self._open_options))

        language_menu = self.settings_menu.addMenu("Language")
        self.language_actions = {}
        for name in ("English", "Sinhala"):
            action = self._action(name, lambda _checked=False, value=name: self._set_language(value), checkable=True)
            self.language_actions[name] = action
            language_menu.addAction(action)
        self.language_actions[self.language].setChecked(True)
        self.settings_menu.addAction(self._action("Application Settings...", self._open_options))
        self.help_menu.addAction(self._action("About ASTROSOFT", self._about))

    def _build_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        style = self.style().StandardPixmap
        for tooltip, action, icon in (
            ("New Horoscope", self.new_action, style.SP_FileIcon),
            ("Open Horoscope", self.open_action, style.SP_DialogOpenButton),
            ("Save Horoscope", self.save_action, style.SP_DialogSaveButton),
            ("Print", self.print_action, style.SP_FileIcon),
        ):
            action.setIcon(self.style().standardIcon(icon))
            action.setToolTip(tooltip)
            toolbar.addAction(action)
        toolbar.addSeparator()
        for tooltip, slot, icon in (
            ("Rasi Chart", lambda: self._select_chart_factor(1), style.SP_FileDialogDetailedView),
            ("Navamsa Chart", lambda: self._select_chart_factor(9), style.SP_FileDialogContentsView),
            ("Divisional Charts", lambda: self._select_view("raasi_str"), style.SP_DirOpenIcon),
            ("Planetary Positions", self._show_positions, style.SP_ComputerIcon),
            ("Dasha", lambda: self._select_view("vimsottari_str"), style.SP_BrowserReload),
            ("Panchangam", lambda: self._select_view("panchangam_str"), style.SP_FileDialogInfoView),
        ):
            action = self._action(tooltip, slot, icon=icon)
            action.setToolTip(tooltip)
            toolbar.addAction(action)

    def _connect_document_events(self):
        self.documents.currentChanged.connect(self._active_document_changed)
        self.documents.tabCloseRequested.connect(self._close_document_at)
        self.navigation.itemDoubleClicked.connect(self._navigate_to_view)

    def _new_horoscope(self):
        chart = ChartTabbed(language=self.language, use_internet_for_location_check=False)
        self._documents[chart] = {"path": None, "dirty": False}
        index = self.documents.addTab(chart, "Untitled Horoscope")
        self.documents.setCurrentIndex(index)
        for field in (chart._name_text, chart._dob_text, chart._tob_text, chart._place_text,
                      chart._lat_text, chart._long_text, chart._tz_text):
            field.textChanged.connect(lambda _text, current=chart: self._document_edited(current))
        chart.tabWidget.currentChanged.connect(lambda _index: self._active_document_changed())
        self._active_document_changed()
        return chart

    def _active_chart(self):
        return self.documents.currentWidget()

    def _document_edited(self, chart):
        record = self._documents.get(chart)
        if record is None:
            return
        record["dirty"] = True
        title = chart._name_text.text().strip() or "Untitled Horoscope"
        index = self.documents.indexOf(chart)
        self.documents.setTabText(index, title + " *")
        if chart is self._active_chart():
            self._update_birth_details(chart)

    def _update_birth_details(self, chart):
        if chart is None:
            return
        values = {
            "Name": chart._name_text.text(),
            "Date": chart._dob_text.text(),
            "Time": chart._tob_text.text(),
            "Place": chart._place_text.text(),
            "Latitude": chart._lat_text.text(),
            "Longitude": chart._long_text.text(),
            "Time zone": chart._tz_text.text(),
        }
        for label, value in values.items():
            self.birth_values[label].setText(value or "-")

    def _active_document_changed(self, *_args):
        chart = self._active_chart()
        self.navigation.clear()
        if chart is None:
            self.positions.setRowCount(0)
            return
        root = QTreeWidgetItem(["Horoscope"])
        self.navigation.addTopLevelItem(root)
        for index in range(chart.tabWidget.count()):
            item = QTreeWidgetItem([chart.tabWidget.tabText(index)])
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            root.addChild(item)
        root.setExpanded(True)
        self._update_birth_details(chart)
        self._populate_positions(chart)
        self._update_chart_details(chart)

    def _navigate_to_view(self, item, _column):
        index = item.data(0, Qt.ItemDataRole.UserRole)
        chart = self._active_chart()
        if chart is not None and index is not None:
            chart.tabWidget.setCurrentIndex(index)

    def _select_view(self, resource_key):
        chart = self._active_chart()
        if chart is None:
            return
        index = next((i for i, key in enumerate(chart.tabNames) if key == resource_key), None)
        if index is None:
            index = next((i for i in range(chart.tabWidget.count())
                          if chart.tabWidget.tabText(i) == chart.resources.get(resource_key)), None)
        if index is not None and index < chart.tabWidget.count():
            chart.tabWidget.setCurrentIndex(index)

    def _select_chart_factor(self, factor):
        chart = self._active_chart()
        if chart is None:
            return
        try:
            index = const.division_chart_factors.index(factor)
        except ValueError:
            return
        self._select_view("raasi_str")
        chart._kundali_chart_combo.setCurrentIndex(index)

    def _set_chart_style(self, style):
        chart = self._active_chart()
        if chart is not None:
            chart.chart_type(style)
            chart._mark_inputs_changed("chart style changed")

    def _show_positions(self):
        self._select_view("raasi_str")
        self.positions.setFocus()

    def _populate_positions(self, chart):
        self.positions.setSortingEnabled(False)
        self.positions.setRowCount(0)
        info = getattr(chart, "_kundali_info", {}) or {}
        chart_data = getattr(chart, "_kundali_chart", []) or []
        for planet in utils.PLANET_NAMES[:9]:
            position = next((value for key, value in info.items() if planet in str(key)), None)
            if position is None:
                continue
            house = ""
            for house_index, contents in enumerate(chart_data, start=1):
                if planet in str(contents):
                    house = str(house_index)
                    break
            row = self.positions.rowCount()
            self.positions.insertRow(row)
            for column, value in enumerate((planet, house, str(position))):
                self.positions.setItem(row, column, QTableWidgetItem(value))
        self.positions.setSortingEnabled(True)

    def _update_chart_details(self, chart):
        selected = chart.tabWidget.tabText(chart.tabWidget.currentIndex()) if chart.tabWidget.count() else ""
        self.details.setText(selected or "No chart selected")

    def _compute_horoscope(self):
        chart = self._active_chart()
        if chart is None:
            return
        self.statusBar().showMessage("Calculating horoscope...")
        QApplication.processEvents()
        chart.compute_horoscope()
        self._documents[chart]["dirty"] = True
        self._populate_positions(chart)
        self._update_birth_details(chart)
        self._update_chart_details(chart)
        self.statusBar().showMessage("Horoscope calculation complete", 5000)

    def _document_data(self, chart):
        return {
            "format": "astrosoft-horoscope",
            "version": 1,
            "name": chart._name_text.text(),
            "date_of_birth": chart._dob_text.text(),
            "time_of_birth": chart._tob_text.text(),
            "place": chart._place_text.text(),
            "latitude": chart._lat_text.text(),
            "longitude": chart._long_text.text(),
            "timezone": chart._tz_text.text(),
            "gender": chart._gender_combo.currentIndex(),
            "chart_style": int(chart._chart_type),
            "calculation_type": chart._calculation_type,
            "language": self.language,
        }

    def _save_horoscope(self):
        chart = self._active_chart()
        if chart is None:
            return False
        path = self._documents[chart]["path"]
        if not path:
            return self._save_horoscope_as()
        return self._write_document(chart, path)

    def _save_horoscope_as(self):
        chart = self._active_chart()
        if chart is None:
            return False
        path, _ = QFileDialog.getSaveFileName(self, "Save Horoscope", "", _FILE_FILTER)
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".astrosoft.json"
        return self._write_document(chart, path)

    def _write_document(self, chart, path):
        try:
            with open(path, "w", encoding="utf-8") as output:
                json.dump(self._document_data(chart), output, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Save Horoscope", str(error))
            return False
        self._documents[chart] = {"path": path, "dirty": False}
        self._update_document_title(chart)
        self.statusBar().showMessage("Saved " + os.path.basename(path), 4000)
        return True

    def _open_horoscope(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Horoscope", "", _FILE_FILTER)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as source:
                data = json.load(source)
            if data.get("format") != "astrosoft-horoscope" or data.get("version") != 1:
                raise ValueError("Unsupported horoscope file format.")
            chart = self._new_horoscope()
            chart.name(data.get("name", ""))
            chart.date_of_birth(data.get("date_of_birth", chart._dob_text.text()))
            chart.time_of_birth(data.get("time_of_birth", chart._tob_text.text()))
            chart.place(
                data.get("place", ""),
                float(data.get("latitude", 0)),
                float(data.get("longitude", 0)),
                float(data.get("timezone", 0)),
            )
            chart.gender(int(data.get("gender", 0)))
            chart.chart_type(data.get("chart_style", const.default_chart_type))
            chart._calculation_type = data.get("calculation_type", "drik")
            self._documents[chart] = {"path": path, "dirty": False}
            chart.compute_horoscope()
            self._populate_positions(chart)
            self._update_document_title(chart)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Open Horoscope", str(error))

    def _update_document_title(self, chart):
        index = self.documents.indexOf(chart)
        if index < 0:
            return
        record = self._documents[chart]
        title = chart._name_text.text().strip() or "Untitled Horoscope"
        if record["path"]:
            title = os.path.basename(record["path"])
        self.documents.setTabText(index, title + (" *" if record["dirty"] else ""))

    def _confirm_document_close(self, chart):
        if not self._documents.get(chart, {}).get("dirty"):
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved Horoscope",
            "Save changes to this horoscope?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            self.documents.setCurrentWidget(chart)
            return self._save_horoscope()
        return True

    def _close_document_at(self, index):
        chart = self.documents.widget(index)
        if chart is None or not self._confirm_document_close(chart):
            return
        self.documents.removeTab(index)
        self._documents.pop(chart, None)
        chart.deleteLater()
        if self.documents.count() == 0:
            self._new_horoscope()

    def _close_current_document(self):
        index = self.documents.currentIndex()
        if index >= 0:
            self._close_document_at(index)

    def _set_language(self, language):
        self.language = language
        utils.set_language(const.available_languages[language])
        for name, action in self.language_actions.items():
            action.setChecked(name == language)
        QApplication.setFont(_preferred_application_font())
        for chart in self._documents:
            chart.language(language)
            chart.compute_horoscope()
        self._active_document_changed()

    def _open_options(self):
        chart = self._active_chart()
        if chart is not None:
            chart._open_options_dialog()

    def _export_pdf(self):
        chart = self._active_chart()
        if chart is not None:
            chart.save_as_pdf()

    def _print_horoscope(self):
        chart = self._active_chart()
        if chart is None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self._paint_chart(printer, chart)

    def _print_preview(self):
        chart = self._active_chart()
        if chart is None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(lambda current_printer: self._paint_chart(current_printer, chart))
        dialog.exec()

    @staticmethod
    def _paint_chart(printer, chart):
        pixmap = chart.grab()
        if pixmap.isNull():
            return
        painter = QPainter(printer)
        page = printer.pageRect(QPrinter.Unit.DevicePixel)
        scaled = pixmap.scaled(
            int(page.width()),
            int(page.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = page.x() + (page.width() - scaled.width()) / 2
        y = page.y() + (page.height() - scaled.height()) / 2
        painter.drawPixmap(int(x), int(y), scaled)
        painter.end()

    def _refresh_active_view(self):
        self._active_document_changed()

    def _reset_panel_sizes(self):
        self.workspace.setSizes([220, 780, 280])

    def _show_navigation_menu(self, position):
        item = self.navigation.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        menu.addAction("Show View", lambda: self._navigate_to_view(item, 0))
        menu.addAction("Compute Horoscope", self._compute_horoscope)
        menu.exec(self.navigation.viewport().mapToGlobal(position))

    def _show_document_menu(self, position):
        menu = QMenu(self)
        menu.addAction(self.save_action)
        menu.addAction("Close Horoscope", self._close_current_document)
        menu.exec(self.documents.mapToGlobal(position))

    def _show_positions_menu(self, position):
        item = self.positions.itemAt(position)
        menu = QMenu(self)
        if item is not None:
            menu.addAction("Copy Cell", lambda: QApplication.clipboard().setText(item.text()))
        menu.addAction("Refresh Positions", self._refresh_active_view)
        menu.exec(self.positions.viewport().mapToGlobal(position))

    def _about(self):
        QMessageBox.about(
            self,
            "About ASTROSOFT",
            "ASTROSOFT Classic Edition\nTraditional desktop interface powered by PyJHora.",
        )

    def closeEvent(self, event):
        for chart in list(self._documents):
            if not self._confirm_document_close(chart):
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ASTROSOFT")
    app.setOrganizationName("ASTROSOFT")
    window = AstrosoftMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())