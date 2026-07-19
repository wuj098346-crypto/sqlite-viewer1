import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from sqlite_viewer.models.errors import DatabaseOpenError
from sqlite_viewer.services.connection import ConnectionManager, build_read_only_uri


def test_read_only_uri_uses_absolute_path_and_mode_ro(sqlite_db_path):
    uri = build_read_only_uri(sqlite_db_path)

    assert uri.startswith("file:")
    assert sqlite_db_path.resolve().as_posix() in uri
    assert "mode=ro" in uri


def test_open_read_only_returns_id_and_configures_row_factory(sqlite_db_path):
    manager = ConnectionManager()

    connection_id = manager.open_read_only(sqlite_db_path)
    connection = manager.get(connection_id)

    assert str(UUID(connection_id)) == connection_id
    assert connection.row_factory is sqlite3.Row
    assert connection.execute("SELECT name FROM students WHERE id = 1").fetchone()["name"] == "Alice"


def test_closed_connection_cannot_be_retrieved(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open_read_only(sqlite_db_path)

    manager.close(connection_id)

    with pytest.raises(DatabaseOpenError):
        manager.get(connection_id)


@pytest.mark.parametrize("contents", [b"not a database", b""])
def test_missing_or_non_sqlite_file_is_rejected(tmp_path: Path, contents: bytes):
    manager = ConnectionManager()
    candidate = tmp_path / "invalid.sqlite"
    candidate.write_bytes(contents)

    with pytest.raises(DatabaseOpenError):
        manager.open_read_only(candidate)

    with pytest.raises(DatabaseOpenError):
        manager.open_read_only(tmp_path / "missing.sqlite")


def test_header_spoofed_database_file_is_rejected(tmp_path: Path):
    manager = ConnectionManager()
    candidate = tmp_path / "header-only.sqlite"
    candidate.write_bytes(b"SQLite format 3\x00")

    with pytest.raises(DatabaseOpenError):
        manager.open_read_only(candidate)


def test_sqlite_rejects_writes_and_keeps_source_rows(sqlite_db_path, read_students):
    manager = ConnectionManager()
    connection_id = manager.open_read_only(sqlite_db_path)

    with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
        manager.get(connection_id).execute("UPDATE students SET name = 'Changed' WHERE id = 1")

    assert read_students(sqlite_db_path)[0][1] == "Alice"


def test_close_all_releases_every_connection(sqlite_db_path):
    manager = ConnectionManager()
    first_id = manager.open_read_only(sqlite_db_path)
    second_id = manager.open_read_only(sqlite_db_path)

    manager.close_all()

    with pytest.raises(DatabaseOpenError):
        manager.get(first_id)
    with pytest.raises(DatabaseOpenError):
        manager.get(second_id)
