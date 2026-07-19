import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sqlite_viewer.models.errors import (
    DatabaseOpenError,
    DatabaseQueryError,
    ExportError,
    ReadOnlyViolationError,
    SQLiteViewerError,
)
from sqlite_viewer.models.domain import ColumnInfo, DatabaseIdentity, DatabaseObject, PageResult, QueryResult


def test_sqlite_fixture_contains_expected_schema(sqlite_db_path):
    with sqlite3.connect(sqlite_db_path) as connection:
        objects = set(
            connection.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )

    assert ("table", "students") in objects
    assert ("table", "courses") in objects
    assert ("view", "student_course_view") in objects
    assert ("index", "idx_students_course_id") in objects


def test_student_row_helpers_return_original_rows(
    sqlite_db_path, read_students, original_student_rows,
):
    assert len(original_student_rows) >= 3
    assert read_students(sqlite_db_path) == original_student_rows


def test_database_identity_is_immutable_and_keeps_path_and_name():
    identity = DatabaseIdentity(path=Path("sample.db"), display_name="sample.db")

    assert identity.path == Path("sample.db")
    assert identity.display_name == "sample.db"

    with pytest.raises(FrozenInstanceError):
        identity.display_name = "other.db"


def test_database_object_and_page_result_keep_view_data():
    database_object = DatabaseObject("table", "students", None)
    page = PageResult(
        columns=("id", "name"), rows=((1, "Alice"),), page_number=1,
        page_size=100, has_next_page=False, total_rows=1,
    )

    assert database_object.object_type == "table"
    assert database_object.name == "students"
    assert page.rows == ((1, "Alice"),)


def test_column_and_query_results_keep_read_only_metadata():
    column = ColumnInfo("id", "INTEGER", True, True, None)
    result = QueryResult(("id",), ((1,),), 2.5, False)

    assert column.is_primary_key is True
    assert result.elapsed_ms == 2.5


@pytest.mark.parametrize(
    "value, field_name, replacement",
    [
        (DatabaseObject("table", "students", None), "name", "courses"),
        (ColumnInfo("id", "INTEGER", True, True, None), "declared_type", "TEXT"),
        (PageResult(("id",), ((1,),), 1, 100, False, 1), "page_number", 2),
        (QueryResult(("id",), ((1,),), 2.5, False), "was_capped", True),
    ],
)
def test_all_result_models_are_immutable(value, field_name, replacement):
    with pytest.raises(FrozenInstanceError):
        setattr(value, field_name, replacement)


@pytest.mark.parametrize(
    "error_type",
    [DatabaseOpenError, ReadOnlyViolationError, DatabaseQueryError, ExportError],
)
def test_domain_errors_are_user_presentable(error_type):
    assert isinstance(error_type("details"), SQLiteViewerError)
