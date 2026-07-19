from PySide6.QtCore import Qt

from sqlite_viewer.models.domain import ColumnInfo, PageResult, QueryResult
from sqlite_viewer.presentation.views import DataView, ResultTableModel, RowEditorDialog, SqlView, StructureView


def test_result_model_exposes_page_columns_and_rows():
    model = ResultTableModel(PageResult(("id", "name"), ((1, "Alice"),), 1, 100, False, 1))

    assert model.rowCount() == 1
    assert model.columnCount() == 2
    assert model.data(model.index(0, 1), Qt.DisplayRole) == "Alice"
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "id"


def test_data_view_emits_requested_next_page(qtbot):
    view = DataView()
    qtbot.addWidget(view)
    view.set_page(PageResult(("id",), ((1,),), 1, 100, True, 101))

    with qtbot.waitSignal(view.page_requested) as signal:
        qtbot.mouseClick(view.next_button, Qt.LeftButton)

    assert signal.args == [2]


def test_data_view_enables_edit_for_selected_row(qtbot):
    view = DataView()
    qtbot.addWidget(view)
    view.set_page(PageResult(("id",), ((1,),), 1, 100, False, 1, (None,)))

    assert view.edit_button.isEnabled() is False
    view.table.selectRow(0)
    assert view.edit_button.isEnabled() is True


def test_data_view_disables_row_actions_without_selected_table(qtbot):
    view = DataView()
    qtbot.addWidget(view)

    view.set_row_actions_enabled(False)

    assert view.add_button.isEnabled() is False
    assert view.edit_button.isEnabled() is False


def test_editor_makes_primary_key_read_only_and_omits_generated_key(qtbot):
    columns = (ColumnInfo("id", "INTEGER", True, True, None), ColumnInfo("note", "TEXT", False, False, None))
    edit_dialog = RowEditorDialog("Edit row", columns, {"id": 1, "note": ""}, is_new=False)
    add_dialog = RowEditorDialog("Add row", columns, {}, is_new=True)
    qtbot.addWidget(edit_dialog)
    qtbot.addWidget(add_dialog)

    assert edit_dialog.inputs["id"].isReadOnly() is True
    assert "note" in edit_dialog.null_controls
    assert "id" not in add_dialog.inputs


def test_structure_view_displays_columns_and_create_sql(qtbot):
    view = StructureView()
    qtbot.addWidget(view)
    view.set_structure(
        (ColumnInfo("id", "INTEGER", True, True, None),),
        "CREATE TABLE students (id INTEGER PRIMARY KEY)",
    )

    assert view.table.item(0, 0).text() == "id"
    assert "CREATE TABLE students" in view.create_sql.toPlainText()


def test_sql_view_emits_text_and_displays_query_status(qtbot):
    view = SqlView()
    qtbot.addWidget(view)
    view.editor.setPlainText("SELECT 1")

    with qtbot.waitSignal(view.execute_requested) as signal:
        qtbot.mouseClick(view.execute_button, Qt.LeftButton)

    view.show_result(QueryResult(("value",), ((1,),), 1.5, True))
    view.show_error("invalid SQL")

    assert signal.args == ["SELECT 1"]
    assert "1.5" in view.status_label.text()
    assert "truncated" in view.status_label.text().lower()
    assert view.error_label.text() == "invalid SQL"
