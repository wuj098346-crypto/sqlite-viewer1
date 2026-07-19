from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMainWindow, QTabWidget

from sqlite_viewer.models.domain import DatabaseIdentity
from sqlite_viewer.presentation.database_tab import DatabaseTab
from sqlite_viewer.services.connection import ConnectionManager


SUPPORTED_EXTENSIONS = frozenset({".db", ".sqlite", ".sqlite3"})


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._connections = ConnectionManager()
        self._settings = QSettings("SQLite Viewer", "SQLite Viewer")
        self.database_tabs = QTabWidget()
        self.database_tabs.setTabsClosable(True)
        self.database_tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.database_tabs)
        self.setAcceptDrops(True)
        self._create_actions()
        self._restore_settings()

    def open_database(self, path: Path) -> None:
        path = Path(path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.statusBar().showMessage("Unsupported SQLite file", 5_000)
            return
        tab = DatabaseTab(DatabaseIdentity(path, path.name), self._connections)
        tab.open()
        if tab.connection_id is None:
            self.statusBar().showMessage(tab.error_label.text(), 5_000)
            tab.deleteLater()
            return
        self.database_tabs.addTab(tab, path.name)
        self.database_tabs.setCurrentWidget(tab)
        self.remember_recent_file(path)

    def remember_recent_file(self, path: Path) -> None:
        items = [entry for entry in self.recent_files() if entry != path]
        items.insert(0, path)
        self._settings.setValue("recent_files", [str(item) for item in items[:10]])

    def recent_files(self) -> tuple[Path, ...]:
        values = self._settings.value("recent_files", [])
        if isinstance(values, str):
            values = [values]
        return tuple(Path(value) for value in values)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._connections.close_all()
        super().closeEvent(event)

    def dragEnterEvent(self, event) -> None:
        if any(Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.open_database(path)
        event.acceptProposedAction()

    def _create_actions(self) -> None:
        open_action = self.menuBar().addAction("Open…")
        open_action.triggered.connect(self._choose_database)

    def _choose_database(self) -> None:
        start_directory = self._settings.value("last_directory", "")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open SQLite database", start_directory, "SQLite files (*.db *.sqlite *.sqlite3)"
        )
        if filename:
            path = Path(filename)
            self._settings.setValue("last_directory", str(path.parent))
            self.open_database(path)

    def _close_tab(self, index: int) -> None:
        tab = self.database_tabs.widget(index)
        if isinstance(tab, DatabaseTab):
            tab.close_connection()
        self.database_tabs.removeTab(index)
        tab.deleteLater()

    def _restore_settings(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
