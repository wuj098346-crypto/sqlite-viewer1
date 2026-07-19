import csv
import sqlite3

import pytest

from sqlite_viewer.models.errors import DatabaseQueryError, ExportError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.export import ExportService
from sqlite_viewer.services.query import QueryService


@pytest.fixture
def paged_connection(tmp_path):
    database_path = tmp_path / "paged.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)")
        connection.executemany(
            "INSERT INTO records VALUES (?, ?)",
            ((number, f"value-{number}") for number in range(1, 206)),
        )

    manager = ConnectionManager()
    connection_id = manager.open_read_only(database_path)
    yield QueryService(manager), connection_id
    manager.close_all()


def test_table_paging_reads_one_hundred_rows_at_a_time(paged_connection):
    service, connection_id = paged_connection

    first_page = service.fetch_table_page(connection_id, "records", 1)
    second_page = service.fetch_table_page(connection_id, "records", 2)
    last_page = service.fetch_table_page(connection_id, "records", 3)

    assert first_page.columns == ("id", "value")
    assert len(first_page.rows) == 100
    assert first_page.rows[0] == (1, "value-1")
    assert first_page.has_next_page is True
    assert first_page.total_rows == 205
    assert second_page.rows[0] == (101, "value-101")
    assert second_page.has_next_page is True
    assert len(last_page.rows) == 5
    assert last_page.rows[-1] == (205, "value-205")
    assert last_page.has_next_page is False


@pytest.mark.parametrize("page_number", [0, -1])
def test_table_paging_rejects_non_positive_page_numbers(paged_connection, page_number):
    service, connection_id = paged_connection

    with pytest.raises(DatabaseQueryError):
        service.fetch_table_page(connection_id, "records", page_number)


def test_table_paging_quotes_table_identifiers(tmp_path):
    database_path = tmp_path / "quoted-name.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute('CREATE TABLE "records with space" (id INTEGER)')
        connection.execute('INSERT INTO "records with space" VALUES (1)')

    manager = ConnectionManager()
    connection_id = manager.open_read_only(database_path)

    result = QueryService(manager).fetch_table_page(connection_id, "records with space", 1)

    assert result.rows == ((1,),)


def test_csv_export_writes_utf8_headers_and_normalizes_nulls(tmp_path):
    destination = tmp_path / "export.csv"

    ExportService().write_csv(
        destination,
        ("id", "name", "note"),
        ((1, "Alice", None), (2, "李雷", "comma, retained")),
    )

    assert destination.read_bytes().decode("utf-8").startswith("id,name,note")
    with destination.open(newline="", encoding="utf-8") as exported_file:
        assert list(csv.reader(exported_file)) == [
            ["id", "name", "note"],
            ["1", "Alice", ""],
            ["2", "李雷", "comma, retained"],
        ]


def test_csv_export_wraps_file_system_errors(tmp_path):
    with pytest.raises(ExportError):
        ExportService().write_csv(tmp_path, ("id",), ((1,),))
