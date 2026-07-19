import sqlite3

import pytest

from sqlite_viewer.models.errors import DatabaseQueryError, ReadOnlyViolationError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.query import QueryService, normalize_sql, validate_read_only_statement


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT 1",
        "EXPLAIN SELECT * FROM students",
        "PRAGMA table_info('students')",
        "PRAGMA table_xinfo('students')",
        "PRAGMA index_list('students')",
        "PRAGMA index_info('idx_students_course_id')",
        "PRAGMA index_xinfo('idx_students_course_id')",
        "PRAGMA foreign_key_list('students')",
        "PRAGMA database_list",
        "PRAGMA compile_options",
        "PRAGMA page_count",
        "PRAGMA page_size",
        "PRAGMA schema_version",
        "PRAGMA user_version",
    ],
)
def test_read_only_statements_are_allowed(statement):
    assert validate_read_only_statement(statement) == statement


@pytest.mark.parametrize(
    "statement",
    [
        "",
        "-- comments only",
        "SELECT 1; SELECT 2",
        "PRAGMA user_version = 1",
        "WITH rows AS (SELECT 1) SELECT * FROM rows",
        "ATTACH DATABASE 'other.db' AS other",
        "VACUUM",
        "INSERT INTO students VALUES (4, 'Dora', 1)",
        "UPDATE students SET name = 'Changed'",
        "DELETE FROM students",
        "CREATE TABLE copied (id INTEGER)",
        "BEGIN",
    ],
)
def test_unsafe_or_multi_statement_sql_is_rejected_before_execution(statement):
    with pytest.raises(ReadOnlyViolationError):
        validate_read_only_statement(statement)


def test_comment_normalization_preserves_quoted_comment_markers():
    statement = "SELECT '-- literal /* literal */' AS note, \"-- identifier\" -- real comment\n"

    normalized = normalize_sql(statement)

    assert "'-- literal /* literal */'" in normalized
    assert '"-- identifier"' in normalized
    assert "real comment" not in normalized


def test_execute_read_only_returns_columns_rows_and_elapsed_time(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open_read_only(sqlite_db_path)
    service = QueryService(manager)

    result = service.execute_read_only(connection_id, "SELECT id, name FROM students ORDER BY id")

    assert result.columns == ("id", "name")
    assert result.rows == ((1, "Alice"), (2, "Bob"), (3, "Charlie"))
    assert result.elapsed_ms >= 0
    assert result.was_capped is False


def test_execute_read_only_caps_results_at_one_thousand_rows(tmp_path):
    database_path = tmp_path / "many-rows.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE numbers (value INTEGER)")
        connection.executemany("INSERT INTO numbers VALUES (?)", ((number,) for number in range(1001)))

    manager = ConnectionManager()
    connection_id = manager.open_read_only(database_path)

    result = QueryService(manager).execute_read_only(
        connection_id, "SELECT value FROM numbers ORDER BY value"
    )

    assert len(result.rows) == 1000
    assert result.rows[0] == (0,)
    assert result.rows[-1] == (999,)
    assert result.was_capped is True


def test_sqlite_query_errors_become_domain_errors(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open_read_only(sqlite_db_path)

    with pytest.raises(DatabaseQueryError):
        QueryService(manager).execute_read_only(connection_id, "SELECT missing FROM students")
