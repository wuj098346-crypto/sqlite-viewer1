import sqlite3

from sqlite_viewer.models.domain import ColumnInfo, DatabaseObject
from sqlite_viewer.models.errors import DatabaseQueryError
from sqlite_viewer.services.connection import ConnectionManager


def quote_identifier(name: str) -> str:
    return f'"{name.replace("\"", "\"\"")}"'


class SchemaService:
    def __init__(self, connections: ConnectionManager) -> None:
        self._connections = connections

    def list_objects(self, connection_id: str) -> tuple[DatabaseObject, ...]:
        try:
            rows = self._connections.get(connection_id).execute(
                """
                SELECT type, name, tbl_name
                FROM sqlite_master
                WHERE type IN ('table', 'view', 'index')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name
                """
            )
        except sqlite3.Error as error:
            raise DatabaseQueryError("Could not read database objects") from error

        return tuple(
            DatabaseObject(row["type"], row["name"], row["tbl_name"])
            for row in rows
        )

    def table_columns(self, connection_id: str, table_name: str) -> tuple[ColumnInfo, ...]:
        try:
            rows = tuple(
                self._connections.get(connection_id).execute(
                    f"PRAGMA table_info({quote_identifier(table_name)})"
                )
            )
        except sqlite3.Error as error:
            raise DatabaseQueryError(f"Could not read columns for {table_name}") from error

        if not rows:
            raise DatabaseQueryError(f"Table does not exist: {table_name}")

        return tuple(
            ColumnInfo(
                name=row["name"],
                declared_type=row["type"],
                is_primary_key=bool(row["pk"]),
                is_not_null=bool(row["notnull"]),
                default_value=row["dflt_value"],
            )
            for row in rows
        )

    def create_sql(self, connection_id: str, table_name: str) -> str:
        try:
            row = self._connections.get(connection_id).execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseQueryError(f"Could not read SQL for {table_name}") from error

        if row is None or row["sql"] is None:
            raise DatabaseQueryError(f"Table does not exist: {table_name}")
        return row["sql"]
