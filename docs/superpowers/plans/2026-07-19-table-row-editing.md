# Table Row Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Allow users to add rows and edit non-primary-key values from a table data page, writing directly back to SQLite.

**Architecture:** Make `ConnectionManager` open validated databases read-write while retaining SQL-editor validation. A dedicated `RowWriteService` owns parameterized insert and update statements. `QueryService` retains an internal `rowid` for tables without declared primary keys, and `RowEditorDialog` supplies validated values to `DatabaseTab`.

**Tech Stack:** Python 3.12, sqlite3, PySide6, pytest, pytest-qt.

---

## File Structure

- `src/sqlite_viewer/services/connection.py`: validated read-write connection lifecycle.
- `src/sqlite_viewer/models/domain.py`: page-level internal row identities.
- `src/sqlite_viewer/services/query.py`: paged rows plus optional `rowid` identities.
- `src/sqlite_viewer/services/row_write.py`: parameterized insert/update implementation.
- `src/sqlite_viewer/models/errors.py`: write error type.
- `src/sqlite_viewer/presentation/views.py`: data actions and form dialog.
- `src/sqlite_viewer/presentation/database_tab.py`: dialog and write coordination.

### Task 1: Enable writable connections

**Files:**
- Modify: `src/sqlite_viewer/services/connection.py`
- Modify: `src/sqlite_viewer/presentation/database_tab.py`
- Modify: `tests/services/test_connection.py`

- [ ] Write the failing test:

```python
def test_open_returns_writable_connection(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)

    manager.get(connection_id).execute("UPDATE students SET name = 'Changed' WHERE id = 1")

    assert manager.get(connection_id).execute(
        "SELECT name FROM students WHERE id = 1"
    ).fetchone()["name"] == "Changed"
```

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/services/test_connection.py -v`.
Expected: FAIL because `ConnectionManager.open` does not exist.

- [ ] Replace `open_read_only` with `open`, retaining database-header validation, `sqlite3.Row`, schema probe, connection registration, closing, and error wrapping:

```python
connection = sqlite3.connect(path, check_same_thread=False)
connection.row_factory = sqlite3.Row
```

Change `DatabaseTab.open()` and all fixtures/tests to call `open`. Do not change `QueryService.validate_read_only_statement`.

- [ ] Run the same test command.
Expected: PASS.

- [ ] Commit: `git add src/sqlite_viewer/services/connection.py src/sqlite_viewer/presentation/database_tab.py tests/services/test_connection.py` then `git commit -m "feat: open databases for row editing"`.

### Task 2: Retain internal identity for keyless table rows

**Files:**
- Modify: `src/sqlite_viewer/models/domain.py`
- Modify: `src/sqlite_viewer/services/query.py`
- Modify: `tests/services/test_paging_and_export.py`

- [ ] Write the failing test:

```python
def test_keyless_table_retains_hidden_rowids(tmp_path):
    path = tmp_path / "notes.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE notes (body TEXT)")
        connection.executemany("INSERT INTO notes VALUES (?)", (("one",), ("two",)))
    manager = ConnectionManager()

    result = QueryService(manager).fetch_table_page(manager.open(path), "notes", 1)

    assert result.columns == ("body",)
    assert result.rows == (("one",), ("two",))
    assert result.row_ids == (1, 2)
```

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/services/test_paging_and_export.py -v`.
Expected: FAIL because `PageResult.row_ids` is absent.

- [ ] Add `row_ids: tuple[int | None, ...] = ()` to `PageResult`. In `fetch_table_page`, inspect `PRAGMA table_info`; for keyless tables select `rowid, *`, split the leading result into `row_ids`, and expose only actual columns. For tables with declared primary keys, select `*` and return `None` per displayed row.

- [ ] Run the same test command.
Expected: PASS.

- [ ] Commit: `git add src/sqlite_viewer/models/domain.py src/sqlite_viewer/services/query.py tests/services/test_paging_and_export.py` then `git commit -m "feat: retain row identity for editable tables"`.

### Task 3: Implement parameterized inserts and updates

**Files:**
- Create: `src/sqlite_viewer/services/row_write.py`
- Modify: `src/sqlite_viewer/models/errors.py`
- Create: `tests/services/test_row_write.py`

- [ ] Write failing tests for automatic integer keys, required text keys, explicit nulls, immutable primary keys, and keyless updates:

```python
def test_insert_omits_integer_primary_key(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    columns = SchemaService(manager).table_columns(connection_id, "students")

    RowWriteService(manager).insert(
        connection_id, "students", columns,
        {"name": "Dana", "course_id": "1", "enrolled_at": None},
    )

    assert manager.get(connection_id).execute(
        "SELECT id FROM students WHERE name = 'Dana'"
    ).fetchone()[0] == 4


def test_update_keeps_primary_key_unchanged(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    columns = SchemaService(manager).table_columns(connection_id, "students")

    RowWriteService(manager).update(
        connection_id, "students", columns, (1,), None,
        {"name": "Alicia", "course_id": "1", "enrolled_at": None},
    )

    assert manager.get(connection_id).execute(
        "SELECT id, name FROM students WHERE id = 1"
    ).fetchone() == (1, "Alicia")
```

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/services/test_row_write.py -v`.
Expected: FAIL because `RowWriteService` does not exist.

- [ ] Add `DatabaseWriteError(SQLiteViewerError)`. Implement `RowWriteService.insert` and `.update` using `quote_identifier` and parameter values. Omit exactly one `INTEGER PRIMARY KEY` on insert. Require nonempty values for new primary keys and for non-nullable fields. Keep empty strings as strings; accept `None` only for nullable columns. Updates construct `SET` only from non-key fields and locate rows with all primary-key fields, or `rowid = ?` for keyless tables. Wrap `sqlite3.Error` as `DatabaseWriteError`, and commit after successful statements.

- [ ] Add and run tests asserting text primary keys reject `""`, `("", None)` persists as empty string and SQL NULL, and keyless rows update with `rowid`:

```python
assert manager.get(connection_id).execute(
    "SELECT empty, missing FROM comments"
).fetchone() == ("", None)
```

Run: `python -m pytest --basetemp .pytest-tmp tests/services/test_row_write.py -v`
Expected: PASS.

- [ ] Commit: `git add src/sqlite_viewer/services/row_write.py src/sqlite_viewer/models/errors.py tests/services/test_row_write.py` then `git commit -m "feat: add parameterized row writes"`.

### Task 4: Add data actions and the editor dialog

**Files:**
- Modify: `src/sqlite_viewer/presentation/views.py`
- Modify: `tests/presentation/test_views.py`

- [ ] Write failing UI tests:

```python
def test_edit_is_disabled_until_row_selection(qtbot):
    view = DataView()
    qtbot.addWidget(view)
    view.set_page(PageResult(("id",), ((1,),), 1, 100, False, 1, (None,)))

    assert view.edit_button.isEnabled() is False
    view.table.selectRow(0)
    assert view.edit_button.isEnabled() is True


def test_edit_dialog_makes_primary_keys_read_only(qtbot):
    dialog = RowEditorDialog(
        "Edit row", (ColumnInfo("id", "INTEGER", True, True, None),), {"id": 1}, is_new=False,
    )
    qtbot.addWidget(dialog)

    assert dialog.inputs["id"].isReadOnly() is True
```

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/presentation/test_views.py -v`.
Expected: FAIL because the buttons and dialog do not exist.

- [ ] Implement `DataView.add_requested`, `DataView.edit_requested`, an always available `add_button`, and an `edit_button` enabled only for a selected row. Implement `RowEditorDialog(QDialog)` with `QFormLayout`, per-column `QLineEdit`, `NULL` checkboxes for nullable fields, and Save/Cancel buttons. Omit the generated integer key when adding; make all keys read-only when editing. Its `values()` returns `None` for checked NULL controls and raw strings otherwise. Validate missing non-nullable and new key fields before `accept()`.

- [ ] Run the same test command.
Expected: PASS.

- [ ] Commit: `git add src/sqlite_viewer/presentation/views.py tests/presentation/test_views.py` then `git commit -m "feat: add row editor dialog"`.

### Task 5: Coordinate dialog writes and table refreshes

**Files:**
- Modify: `src/sqlite_viewer/presentation/database_tab.py`
- Modify: `tests/presentation/test_database_tab.py`

- [ ] Write failing integration tests:

```python
def test_tab_adds_row_and_refreshes_data(qtbot, sqlite_db_path):
    tab = DatabaseTab(DatabaseIdentity(sqlite_db_path, "sample.sqlite"), ConnectionManager())
    qtbot.addWidget(tab)
    tab.open()
    tab.show_table("students")

    tab._add_row({"name": "Dana", "course_id": "1", "enrolled_at": None})

    assert tab.data_view.model.rowCount() == 4
    assert tab.data_view.model.data(tab.data_view.model.index(3, 1)) == "Dana"
```

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/presentation/test_database_tab.py -v`.
Expected: FAIL because the tab does not coordinate row writes.

- [ ] Store current table name and `SchemaService.table_columns` on `show_table`; instantiate `RowWriteService`. Connect `DataView` signals to add/edit dialogs. For an edit, derive original primary-key values from the selected visible row and pass its `PageResult.row_ids` entry for keyless tables. On `DatabaseWriteError`, set the dialog error label and keep it open. On success, reload the current table page and close the dialog. Do not expose these actions for views, indexes, or before table selection.

- [ ] Run `python -m pytest --basetemp .pytest-tmp tests/presentation -v`.
Expected: PASS.

- [ ] Commit: `git add src/sqlite_viewer/presentation/database_tab.py tests/presentation/test_database_tab.py` then `git commit -m "feat: edit table rows from data page"`.

### Task 6: Document and verify the feature

**Files:**
- Modify: `README.md`
- Test: `tests/`

- [ ] Replace read-only claims with the actual boundary: table data pages can add and update rows, all primary keys remain immutable during edits, single `INTEGER PRIMARY KEY` values are generated by SQLite, and the SQL page remains read-only. Document the explicit `NULL` control.

- [ ] Run `python -m pytest --basetemp .pytest-tmp -v`.
Expected: PASS with no unexpected warnings.

- [ ] Run `python -m sqlite_viewer.app` and manually verify adding a row, changing a non-key value, primary-key read-only behavior, NULL versus empty string, refresh after save, and SQL-page rejection of `UPDATE`.

- [ ] Commit: `git add README.md` then `git commit -m "docs: describe table row editing"`.
