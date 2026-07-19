from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from sqlite_viewer.models.domain import DatabaseIdentity
from sqlite_viewer.models.errors import DatabaseWriteError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.presentation.database_tab import DatabaseTab


def test_database_tab_opens_objects_and_loads_selected_table(qtbot, sqlite_db_path):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)

    tab.open()
    tab.show_table("students")

    assert tab.connection_id is not None
    assert tab.object_tree.topLevelItemCount() == 3
    assert tab.data_view.model.rowCount() == 3
    assert tab.structure_view.table.item(0, 0).text() == "id"


def test_closing_one_database_tab_keeps_other_connection_available(qtbot, sqlite_db_path):
    manager = ConnectionManager()
    first = DatabaseTab(DatabaseIdentity(sqlite_db_path, "first.sqlite"), manager)
    second = DatabaseTab(DatabaseIdentity(sqlite_db_path, "second.sqlite"), manager)
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.open()
    second.open()

    first.close_connection()
    second.show_table("students")

    assert first.connection_id is None
    assert second.connection_id is not None
    assert second.data_view.model.rowCount() == 3


def test_rejected_sql_stays_in_current_tab_editor(qtbot, sqlite_db_path):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)
    tab.open()
    tab.sql_view.editor.setPlainText("UPDATE students SET name = 'Changed'")

    tab.execute_sql(tab.sql_view.editor.toPlainText())

    assert "read-only" in tab.sql_view.error_label.text().lower()
    assert tab.sql_view.editor.toPlainText().startswith("UPDATE")


def test_database_tab_adds_row_and_refreshes_table(qtbot, sqlite_db_path):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)
    tab.open()
    tab.show_table("students")

    tab._add_row({"name": "Dana", "course_id": "1", "enrolled_at": None})

    assert tab.data_view.model.rowCount() == 4
    assert tab.data_view.model.data(tab.data_view.model.index(3, 1)) == "Dana"


def test_database_tab_deletes_confirmed_selected_row_and_refreshes_table(qtbot, sqlite_db_path, read_students, monkeypatch):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)
    tab.open()
    tab.show_table("students")
    tab.data_view.table.selectRow(1)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)

    qtbot.mouseClick(tab.data_view.delete_button, Qt.LeftButton)

    assert tab.data_view.model.rowCount() == 2
    assert tuple(row[0] for row in read_students(sqlite_db_path)) == (1, 3)


def test_database_tab_does_not_delete_row_when_confirmation_is_rejected(qtbot, sqlite_db_path, read_students, monkeypatch):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)
    tab.open()
    tab.show_table("students")
    tab.data_view.table.selectRow(1)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)

    qtbot.mouseClick(tab.data_view.delete_button, Qt.LeftButton)

    assert tuple(row[0] for row in read_students(sqlite_db_path)) == (1, 2, 3)


def test_database_tab_shows_write_error_when_row_delete_fails(qtbot, sqlite_db_path, monkeypatch):
    manager = ConnectionManager()
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), manager)
    qtbot.addWidget(tab)
    tab.open()
    tab.show_table("students")
    tab.data_view.table.selectRow(1)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)

    def fail_delete(*args):
        raise DatabaseWriteError("cannot delete row")

    monkeypatch.setattr(tab._writes, "delete", fail_delete)

    qtbot.mouseClick(tab.data_view.delete_button, Qt.LeftButton)

    assert tab.error_label.text() == "cannot delete row"
