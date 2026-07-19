import sqlite3

import pytest

from sqlite_viewer.models.errors import DatabaseWriteError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.row_write import RowWriteService
from sqlite_viewer.services.schema import SchemaService


def test_insert_omits_integer_primary_key(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    columns = SchemaService(manager).table_columns(connection_id, "students")

    RowWriteService(manager).insert(
        connection_id,
        "students",
        columns,
        {"name": "Dana", "course_id": "1", "enrolled_at": None},
    )

    assert tuple(manager.get(connection_id).execute(
        "SELECT id, name, course_id, enrolled_at FROM students WHERE name = 'Dana'"
    ).fetchone()) == (4, "Dana", 1, None)


def test_insert_requires_text_primary_key(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    manager.get(connection_id).execute("CREATE TABLE tags (code TEXT PRIMARY KEY, label TEXT)")
    columns = SchemaService(manager).table_columns(connection_id, "tags")

    with pytest.raises(DatabaseWriteError, match="code is required"):
        RowWriteService(manager).insert(
            connection_id, "tags", columns, {"code": "", "label": "New"}
        )


def test_update_only_changes_non_primary_key_values(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    columns = SchemaService(manager).table_columns(connection_id, "students")

    RowWriteService(manager).update(
        connection_id,
        "students",
        columns,
        (1,),
        None,
        {"name": "Alicia", "course_id": "1", "enrolled_at": None},
    )

    assert tuple(manager.get(connection_id).execute(
        "SELECT id, name, course_id, enrolled_at FROM students WHERE id = 1"
    ).fetchone()) == (1, "Alicia", 1, None)


def test_delete_removes_row_by_primary_key(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    columns = SchemaService(manager).table_columns(connection_id, "students")

    RowWriteService(manager).delete(connection_id, "students", columns, (2,), None)

    assert tuple(tuple(row) for row in manager.get(connection_id).execute(
        "SELECT id FROM students ORDER BY id"
    ).fetchall()) == ((1,), (3,))


def test_delete_removes_row_with_null_text_primary_key(tmp_path):
    path = tmp_path / "records.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE records (code TEXT PRIMARY KEY, value TEXT)")
        connection.executemany(
            "INSERT INTO records VALUES (?, ?)",
            ((None, "first"), ("second", "second")),
        )
    manager = ConnectionManager()
    connection_id = manager.open(path)
    columns = SchemaService(manager).table_columns(connection_id, "records")

    RowWriteService(manager).delete(connection_id, "records", columns, (None,), None)

    assert tuple(tuple(row) for row in manager.get(connection_id).execute(
        "SELECT code, value FROM records"
    ).fetchall()) == (("second", "second"),)


def test_delete_rejects_ambiguous_null_text_primary_key(tmp_path):
    path = tmp_path / "records.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE records (code TEXT PRIMARY KEY, value TEXT)")
        connection.executemany(
            "INSERT INTO records VALUES (?, ?)",
            ((None, "first"), (None, "second")),
        )
    manager = ConnectionManager()
    connection_id = manager.open(path)
    columns = SchemaService(manager).table_columns(connection_id, "records")

    with pytest.raises(DatabaseWriteError, match="Row identity is required"):
        RowWriteService(manager).delete(connection_id, "records", columns, (None,), None)

    assert tuple(tuple(row) for row in manager.get(connection_id).execute(
        "SELECT value FROM records ORDER BY value"
    ).fetchall()) == (("first",), ("second",))


def test_update_keyless_table_uses_rowid(tmp_path):
    path = tmp_path / "notes.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE notes (body TEXT)")
        connection.execute("INSERT INTO notes VALUES ('old')")
    manager = ConnectionManager()
    connection_id = manager.open(path)
    columns = SchemaService(manager).table_columns(connection_id, "notes")

    RowWriteService(manager).update(connection_id, "notes", columns, (), 1, {"body": "new"})

    assert manager.get(connection_id).execute("SELECT body FROM notes").fetchone()[0] == "new"


def test_delete_keyless_table_uses_rowid(tmp_path):
    path = tmp_path / "notes.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE notes (body TEXT)")
        connection.execute("INSERT INTO notes VALUES ('first')")
        connection.execute("INSERT INTO notes VALUES ('second')")
    manager = ConnectionManager()
    connection_id = manager.open(path)
    columns = SchemaService(manager).table_columns(connection_id, "notes")

    RowWriteService(manager).delete(connection_id, "notes", columns, (), 1)

    assert tuple(tuple(row) for row in manager.get(connection_id).execute(
        "SELECT body FROM notes"
    ).fetchall()) == (("second",),)


def test_insert_preserves_empty_string_and_null(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    manager.get(connection_id).execute(
        "CREATE TABLE comments (id INTEGER PRIMARY KEY, empty TEXT, missing TEXT)"
    )
    columns = SchemaService(manager).table_columns(connection_id, "comments")

    RowWriteService(manager).insert(
        connection_id, "comments", columns, {"empty": "", "missing": None}
    )

    assert tuple(manager.get(connection_id).execute(
        "SELECT empty, missing FROM comments"
    ).fetchone()) == ("", None)
