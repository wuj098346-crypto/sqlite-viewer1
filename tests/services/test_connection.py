import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from sqlite_viewer.models.errors import DatabaseOpenError
from sqlite_viewer.services.connection import ConnectionManager


def test_open_returns_id_and_configures_row_factory(sqlite_db_path):
    manager = ConnectionManager()

    connection_id = manager.open(sqlite_db_path)
    connection = manager.get(connection_id)

    assert str(UUID(connection_id)) == connection_id
    assert connection.row_factory is sqlite3.Row
    assert connection.execute("SELECT name FROM students WHERE id = 1").fetchone()["name"] == "Alice"


def test_open_returns_writable_connection(sqlite_db_path):
    manager = ConnectionManager()

    connection_id = manager.open(sqlite_db_path)
    connection = manager.get(connection_id)
    connection.execute("UPDATE students SET name = 'Changed' WHERE id = 1")

    assert connection.execute(
        "SELECT name FROM students WHERE id = 1"
    ).fetchone()["name"] == "Changed"


def test_closed_connection_cannot_be_retrieved(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)

    manager.close(connection_id)

    with pytest.raises(DatabaseOpenError):
        manager.get(connection_id)


@pytest.mark.parametrize("contents", [b"not a database", b""])
def test_missing_or_non_sqlite_file_is_rejected(tmp_path: Path, contents: bytes):
    manager = ConnectionManager()
    candidate = tmp_path / "invalid.sqlite"
    candidate.write_bytes(contents)

    with pytest.raises(DatabaseOpenError):
        manager.open(candidate)

    with pytest.raises(DatabaseOpenError):
        manager.open(tmp_path / "missing.sqlite")


def test_header_spoofed_database_file_is_rejected(tmp_path: Path):
    manager = ConnectionManager()
    candidate = tmp_path / "header-only.sqlite"
    candidate.write_bytes(b"SQLite format 3\x00")

    with pytest.raises(DatabaseOpenError):
        manager.open(candidate)


def test_sqlite_accepts_writes(sqlite_db_path, read_students):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)

    manager.get(connection_id).execute("UPDATE students SET name = 'Changed' WHERE id = 1")
    manager.get(connection_id).commit()

    assert read_students(sqlite_db_path)[0][1] == "Changed"


def test_close_all_releases_every_connection(sqlite_db_path):
    manager = ConnectionManager()
    first_id = manager.open(sqlite_db_path)
    second_id = manager.open(sqlite_db_path)

    manager.close_all()

    with pytest.raises(DatabaseOpenError):
        manager.get(first_id)
    with pytest.raises(DatabaseOpenError):
        manager.get(second_id)
