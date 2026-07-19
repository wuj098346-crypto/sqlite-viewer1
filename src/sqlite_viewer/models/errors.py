class SQLiteViewerError(Exception):
    """Base class for user-presentable application errors."""


class DatabaseOpenError(SQLiteViewerError):
    """Raised when a database cannot be opened read-only."""


class ReadOnlyViolationError(SQLiteViewerError):
    """Raised when a SQL statement is not permitted in read-only mode."""


class DatabaseQueryError(SQLiteViewerError):
    """Raised when a permitted database read fails."""


class DatabaseWriteError(SQLiteViewerError):
    """Raised when a table row cannot be written."""


class ExportError(SQLiteViewerError):
    """Raised when a CSV result cannot be written."""
