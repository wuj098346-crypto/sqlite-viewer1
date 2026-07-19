import pytest

from sqlite_viewer.models.errors import DatabaseQueryError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.schema import SchemaService


@pytest.fixture
def schema_service(sqlite_db_path):
    manager = ConnectionManager()
    connection_id = manager.open(sqlite_db_path)
    yield SchemaService(manager), connection_id
    manager.close_all()


def test_list_objects_returns_user_tables_views_and_indexes(schema_service):
    service, connection_id = schema_service

    objects = service.list_objects(connection_id)

    assert {(item.object_type, item.name, item.table_name) for item in objects} == {
        ("table", "courses", "courses"),
        ("table", "students", "students"),
        ("view", "student_course_view", "student_course_view"),
        ("index", "idx_students_course_id", "students"),
    }
    assert all(not item.name.startswith("sqlite_") for item in objects)


def test_table_columns_returns_declared_metadata(schema_service):
    service, connection_id = schema_service

    columns = service.table_columns(connection_id, "students")

    assert columns[0].name == "id"
    assert columns[0].declared_type == "INTEGER"
    assert columns[0].is_primary_key is True
    assert columns[1].name == "name"
    assert columns[1].is_not_null is True
    assert columns[3].name == "enrolled_at"
    assert columns[3].default_value == "'2026-07-19'"


def test_create_sql_returns_selected_table_definition(schema_service):
    service, connection_id = schema_service

    statement = service.create_sql(connection_id, "students")

    assert "CREATE TABLE students" in statement
    assert "course_id INTEGER NOT NULL" in statement


@pytest.mark.parametrize("method_name", ["table_columns", "create_sql"])
def test_missing_table_raises_domain_error(schema_service, method_name):
    service, connection_id = schema_service

    with pytest.raises(DatabaseQueryError):
        getattr(service, method_name)(connection_id, "missing_table")
