import shutil

from sqlite_viewer.presentation.main_window import MainWindow


def test_two_database_read_only_workflow(qtbot, sqlite_db_path, tmp_path):
    second_database = tmp_path / "second.sqlite"
    shutil.copy(sqlite_db_path, second_database)
    export_path = tmp_path / "result.csv"
    window = MainWindow()
    qtbot.addWidget(window)

    window.open_database(sqlite_db_path)
    window.open_database(second_database)
    first = window.database_tabs.widget(0)
    second = window.database_tabs.widget(1)
    first.show_table("students")
    first.execute_sql("SELECT id, name FROM students ORDER BY id")
    first._query_result = first._query.execute_read_only(first.connection_id, "SELECT id, name FROM students ORDER BY id")
    from sqlite_viewer.services.export import ExportService
    ExportService().write_csv(export_path, first._query_result.columns, first._query_result.rows)
    first.execute_sql("UPDATE students SET name = 'Changed'")
    window._close_tab(0)
    second.show_table("students")

    assert export_path.exists()
    assert "read-only" in first.sql_view.error_label.text().lower()
    assert second.data_view.model.rowCount() == 3
