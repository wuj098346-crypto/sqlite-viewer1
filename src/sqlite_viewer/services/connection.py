import sqlite3
from pathlib import Path
from threading import RLock
from uuid import uuid4

from sqlite_viewer.models.domain import DatabaseIdentity
from sqlite_viewer.models.errors import DatabaseOpenError


SQLITE_HEADER = b"SQLite format 3\x00"


def _database_path(database: DatabaseIdentity | Path) -> Path:
    if isinstance(database, DatabaseIdentity):
        return database.path
    return database


def build_read_only_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, sqlite3.Connection] = {}
        self._lock = RLock()

    def open_read_only(self, database: DatabaseIdentity | Path) -> str:
        path = _database_path(database)
        self._validate_database_file(path)

        try:
            connection = sqlite3.connect(
                build_read_only_uri(path), uri=True, check_same_thread=False
            )
        except (OSError, sqlite3.Error) as error:
            raise DatabaseOpenError(f"Could not open database: {path}") from error

        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA schema_version").fetchone()
        except sqlite3.Error as error:
            connection.close()
            raise DatabaseOpenError(f"Could not open database: {path}") from error

        connection_id = str(uuid4())
        with self._lock:
            self._connections[connection_id] = connection
        return connection_id

    def get(self, connection_id: str) -> sqlite3.Connection:
        with self._lock:
            try:
                return self._connections[connection_id]
            except KeyError as error:
                raise DatabaseOpenError("Database connection is not open") from error

    def close(self, connection_id: str) -> None:
        with self._lock:
            connection = self._connections.pop(connection_id, None)
        if connection is not None:
            connection.close()

    def close_all(self) -> None:
        with self._lock:
            connections = tuple(self._connections.values())
            self._connections.clear()
        for connection in connections:
            connection.close()

    @staticmethod
    def _validate_database_file(path: Path) -> None:
        try:
            with path.open("rb") as database_file:
                header = database_file.read(len(SQLITE_HEADER))
        except OSError as error:
            raise DatabaseOpenError(f"Could not read database: {path}") from error

        if header != SQLITE_HEADER:
            raise DatabaseOpenError(f"Not a SQLite database: {path}")
