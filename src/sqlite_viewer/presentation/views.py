from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from sqlite_viewer.models.domain import ColumnInfo, PageResult, QueryResult


class ResultTableModel(QAbstractTableModel):
    def __init__(self, result: PageResult | QueryResult | None = None) -> None:
        super().__init__()
        self._columns = result.columns if result else ()
        self._rows = result.rows if result else ()

    def set_result(self, result: PageResult | QueryResult) -> None:
        self.beginResetModel()
        self._columns = result.columns
        self._rows = result.rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            value = self._rows[index.row()][index.column()]
            return "" if value is None else str(value)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section]
        return None


class DataView(QWidget):
    page_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._page_number = 1
        self.table = QTableView()
        self.model = ResultTableModel()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.page_label = QLabel()
        self.previous_button.clicked.connect(self._previous_page)
        self.next_button.clicked.connect(self._next_page)
        controls = QHBoxLayout()
        controls.addWidget(self.previous_button)
        controls.addWidget(self.page_label)
        controls.addWidget(self.next_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(controls)
        self.set_page(PageResult((), (), 1, 100, False, 0))

    def set_page(self, page: PageResult) -> None:
        self._page_number = page.page_number
        self.model.set_result(page)
        self.page_label.setText(f"Page {page.page_number}")
        self.previous_button.setEnabled(page.page_number > 1)
        self.next_button.setEnabled(page.has_next_page)

    def _previous_page(self) -> None:
        self.page_requested.emit(self._page_number - 1)

    def _next_page(self) -> None:
        self.page_requested.emit(self._page_number + 1)


class StructureView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Primary key", "Not null", "Default"])
        self.create_sql = QPlainTextEdit()
        self.create_sql.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.create_sql)

    def set_structure(self, columns: tuple[ColumnInfo, ...], create_sql: str) -> None:
        self.table.setRowCount(len(columns))
        for row_index, column in enumerate(columns):
            values = (column.name, column.declared_type, str(column.is_primary_key), str(column.is_not_null), column.default_value or "")
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.create_sql.setPlainText(create_sql)


class SqlView(QWidget):
    execute_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.editor = QPlainTextEdit()
        self.execute_button = QPushButton("Execute")
        self.error_label = QLabel()
        self.status_label = QLabel()
        self.result_table = QTableView()
        self.model = ResultTableModel()
        self.result_table.setModel(self.model)
        self.execute_button.clicked.connect(lambda: self.execute_requested.emit(self.editor.toPlainText()))
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addWidget(self.execute_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.result_table)

    def show_result(self, result: QueryResult) -> None:
        self.model.set_result(result)
        capped = " (truncated)" if result.was_capped else ""
        self.status_label.setText(f"{result.elapsed_ms:.1f} ms{capped}")
        self.error_label.clear()

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
