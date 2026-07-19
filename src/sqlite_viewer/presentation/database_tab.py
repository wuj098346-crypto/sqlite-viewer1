from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from sqlite_viewer.models.domain import DatabaseIdentity
from sqlite_viewer.models.errors import SQLiteViewerError
from sqlite_viewer.presentation.views import DataView, SqlView, StructureView
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.query import QueryService
from sqlite_viewer.services.schema import SchemaService


class DatabaseTab(QWidget):
    def __init__(self, identity: DatabaseIdentity, connections: ConnectionManager) -> None:
        super().__init__()
        self.identity = identity
        self._connections = connections
        self._schema = SchemaService(connections)
        self._query = QueryService(connections)
        self.connection_id: str | None = None
        self.object_tree = QTreeWidget()
        self.object_tree.setHeaderHidden(True)
        self.error_label = QLabel()
        self.data_view = DataView()
        self.structure_view = StructureView()
        self.sql_view = SqlView()
        self.content_tabs = QTabWidget()
        self.content_tabs.addTab(self.data_view, "Data")
        self.content_tabs.addTab(self.structure_view, "Structure")
        self.content_tabs.addTab(self.sql_view, "SQL")
        layout = QVBoxLayout(self)
        body = QHBoxLayout()
        body.addWidget(self.object_tree, 1)
        body.addWidget(self.content_tabs, 4)
        layout.addWidget(self.error_label)
        layout.addLayout(body)
        self.object_tree.itemActivated.connect(self._activated_object)
        self.data_view.page_requested.connect(self._load_page)
        self.sql_view.execute_requested.connect(self.execute_sql)

    def open(self) -> None:
        try:
            self.connection_id = self._connections.open(self.identity)
            self._populate_objects()
            self.error_label.clear()
        except SQLiteViewerError as error:
            self._show_error(error)

    def close_connection(self) -> None:
        if self.connection_id is not None:
            self._connections.close(self.connection_id)
            self.connection_id = None

    def show_table(self, table_name: str) -> None:
        if self.connection_id is None:
            return
        try:
            self.data_view.set_page(self._query.fetch_table_page(self.connection_id, table_name, 1))
            self.structure_view.set_structure(
                self._schema.table_columns(self.connection_id, table_name),
                self._schema.create_sql(self.connection_id, table_name),
            )
            self.error_label.clear()
        except SQLiteViewerError as error:
            self._show_error(error)

    def execute_sql(self, statement: str) -> None:
        if self.connection_id is None:
            return
        try:
            self.sql_view.show_result(self._query.execute_read_only(self.connection_id, statement))
        except SQLiteViewerError as error:
            self.sql_view.show_error(str(error))

    def _populate_objects(self) -> None:
        if self.connection_id is None:
            return
        self.object_tree.clear()
        groups = {kind: QTreeWidgetItem([label]) for kind, label in (("table", "Tables"), ("view", "Views"), ("index", "Indexes"))}
        for group in groups.values():
            group.setFlags(group.flags() & ~Qt.ItemIsSelectable)
            self.object_tree.addTopLevelItem(group)
        for database_object in self._schema.list_objects(self.connection_id):
            item = QTreeWidgetItem([database_object.name])
            item.setData(0, Qt.UserRole, database_object)
            groups[database_object.object_type].addChild(item)
        self.object_tree.expandAll()

    def _activated_object(self, item: QTreeWidgetItem) -> None:
        database_object = item.data(0, Qt.UserRole)
        if database_object and database_object.object_type == "table":
            self.show_table(database_object.name)

    def _load_page(self, page_number: int) -> None:
        current = self.object_tree.currentItem()
        database_object = current.data(0, Qt.UserRole) if current else None
        if self.connection_id and database_object and database_object.object_type == "table":
            try:
                self.data_view.set_page(self._query.fetch_table_page(self.connection_id, database_object.name, page_number))
            except SQLiteViewerError as error:
                self._show_error(error)

    def _show_error(self, error: SQLiteViewerError) -> None:
        self.error_label.setText(str(error))
