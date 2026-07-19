import sqlite3

from sqlite_viewer.models.domain import ColumnInfo
from sqlite_viewer.models.errors import DatabaseWriteError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.schema import hidden_row_identifier, quote_identifier


def _is_generated_integer_key(column: ColumnInfo, columns: tuple[ColumnInfo, ...]) -> bool:
    return (
        column.is_primary_key
        and len(tuple(item for item in columns if item.is_primary_key)) == 1
        and column.declared_type.strip().upper() == "INTEGER"
    )


def _validate(columns: tuple[ColumnInfo, ...], values: dict[str, object], *, require_keys: bool) -> None:
    for column in columns:
        value = values.get(column.name)
        required = column.is_not_null or (require_keys and column.is_primary_key)
        if required and (value is None or value == ""):
            raise DatabaseWriteError(f"{column.name} is required")
        if value is None and column.is_not_null:
            raise DatabaseWriteError(f"{column.name} is required")


class RowWriteService:
    def __init__(self, connections: ConnectionManager) -> None:
        self._connections = connections

    def insert(self, connection_id: str, table_name: str, columns: tuple[ColumnInfo, ...], values: dict[str, object]) -> None:
        included = tuple(column for column in columns if not _is_generated_integer_key(column, columns))
        _validate(included, values, require_keys=True)
        names = ", ".join(quote_identifier(column.name) for column in included)
        placeholders = ", ".join("?" for _ in included)
        self._execute(connection_id, f"INSERT INTO {quote_identifier(table_name)} ({names}) VALUES ({placeholders})", tuple(values.get(column.name) for column in included))

    def update(self, connection_id: str, table_name: str, columns: tuple[ColumnInfo, ...], primary_key_values: tuple[object, ...], row_id: int | None, values: dict[str, object]) -> None:
        editable = tuple(column for column in columns if not column.is_primary_key)
        _validate(editable, values, require_keys=False)
        assignments = ", ".join(f"{quote_identifier(column.name)} = ?" for column in editable)
        keys = tuple(column for column in columns if column.is_primary_key)
        if keys:
            if len(primary_key_values) != len(keys):
                raise DatabaseWriteError("Primary key values are required")
            where = " AND ".join(f"{quote_identifier(column.name)} IS ?" for column in keys)
            locator_values = primary_key_values
        elif row_id is not None and (row_identifier := hidden_row_identifier(
            column.name for column in columns
        )) is not None:
            where = f"{quote_identifier(row_identifier)} = ?"
            locator_values = (row_id,)
        else:
            raise DatabaseWriteError("Row identity is required")
        self._execute(connection_id, f"UPDATE {quote_identifier(table_name)} SET {assignments} WHERE {where}", tuple(values.get(column.name) for column in editable) + locator_values)

    def delete(self, connection_id: str, table_name: str, columns: tuple[ColumnInfo, ...], primary_key_values: tuple[object, ...], row_id: int | None) -> None:
        keys = tuple(column for column in columns if column.is_primary_key)
        if keys:
            if len(primary_key_values) != len(keys):
                raise DatabaseWriteError("Primary key values are required")
            where = " AND ".join(f"{quote_identifier(column.name)} IS ?" for column in keys)
            locator_values = primary_key_values
        elif row_id is not None and (row_identifier := hidden_row_identifier(
            column.name for column in columns
        )) is not None:
            where = f"{quote_identifier(row_identifier)} = ?"
            locator_values = (row_id,)
        else:
            raise DatabaseWriteError("Row identity is required")
        self._execute(connection_id, f"DELETE FROM {quote_identifier(table_name)} WHERE {where}", locator_values)

    def _execute(self, connection_id: str, statement: str, parameters: tuple[object, ...]) -> None:
        try:
            connection = self._connections.get(connection_id)
            connection.execute(statement, parameters)
            connection.commit()
        except sqlite3.Error as error:
            raise DatabaseWriteError(str(error)) from error
