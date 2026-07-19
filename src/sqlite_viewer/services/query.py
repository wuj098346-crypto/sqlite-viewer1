import re
import sqlite3
from time import perf_counter

from sqlite_viewer.models.domain import PageResult, QueryResult
from sqlite_viewer.models.errors import DatabaseQueryError, ReadOnlyViolationError
from sqlite_viewer.services.connection import ConnectionManager
from sqlite_viewer.services.schema import hidden_row_identifier, quote_identifier


MAX_QUERY_ROWS = 1_000
TABLE_PAGE_SIZE = 100
READ_ONLY_PRAGMAS = frozenset(
    {
        "table_info",
        "table_xinfo",
        "index_list",
        "index_info",
        "index_xinfo",
        "foreign_key_list",
        "database_list",
        "compile_options",
        "page_count",
        "page_size",
        "schema_version",
        "user_version",
    }
)


def normalize_sql(statement: str) -> str:
    output: list[str] = []
    index = 0
    state = "normal"

    while index < len(statement):
        character = statement[index]
        following = statement[index + 1] if index + 1 < len(statement) else ""

        if state == "normal":
            if character == "'":
                state = "single_quote"
                output.append(character)
            elif character == '"':
                state = "double_quote"
                output.append(character)
            elif character == "[":
                state = "bracket_identifier"
                output.append(character)
            elif character == "-" and following == "-":
                state = "line_comment"
                output.append(" ")
                index += 1
            elif character == "/" and following == "*":
                state = "block_comment"
                output.append(" ")
                index += 1
            else:
                output.append(character)
        elif state == "single_quote":
            output.append(character)
            if character == "'" and following == "'":
                output.append(following)
                index += 1
            elif character == "'":
                state = "normal"
        elif state == "double_quote":
            output.append(character)
            if character == '"' and following == '"':
                output.append(following)
                index += 1
            elif character == '"':
                state = "normal"
        elif state == "bracket_identifier":
            output.append(character)
            if character == "]":
                state = "normal"
        elif state == "line_comment":
            if character in "\r\n":
                output.append(character)
                state = "normal"
        elif state == "block_comment" and character == "*" and following == "/":
            state = "normal"
            index += 1

        index += 1

    if state == "block_comment":
        raise ReadOnlyViolationError("Unterminated SQL comment")
    if state in {"single_quote", "double_quote", "bracket_identifier"}:
        raise ReadOnlyViolationError("Unterminated SQL quote")
    return "".join(output).strip()


def _statement_segments(statement: str) -> tuple[str, ...]:
    segments: list[str] = []
    current: list[str] = []
    state = "normal"
    index = 0

    while index < len(statement):
        character = statement[index]
        following = statement[index + 1] if index + 1 < len(statement) else ""
        current.append(character)

        if state == "normal":
            if character == "'":
                state = "single_quote"
            elif character == '"':
                state = "double_quote"
            elif character == "[":
                state = "bracket_identifier"
            elif character == ";":
                current.pop()
                segment = "".join(current).strip()
                if segment:
                    segments.append(segment)
                current = []
        elif state == "single_quote":
            if character == "'" and following == "'":
                current.append(following)
                index += 1
            elif character == "'":
                state = "normal"
        elif state == "double_quote":
            if character == '"' and following == '"':
                current.append(following)
                index += 1
            elif character == '"':
                state = "normal"
        elif state == "bracket_identifier" and character == "]":
            state = "normal"

        index += 1

    segment = "".join(current).strip()
    if segment:
        segments.append(segment)
    return tuple(segments)


def _has_unquoted_equals(statement: str) -> bool:
    state = "normal"
    index = 0
    while index < len(statement):
        character = statement[index]
        following = statement[index + 1] if index + 1 < len(statement) else ""
        if state == "normal":
            if character == "=":
                return True
            if character == "'":
                state = "single_quote"
            elif character == '"':
                state = "double_quote"
            elif character == "[":
                state = "bracket_identifier"
        elif state == "single_quote":
            if character == "'" and following == "'":
                index += 1
            elif character == "'":
                state = "normal"
        elif state == "double_quote":
            if character == '"' and following == '"':
                index += 1
            elif character == '"':
                state = "normal"
        elif state == "bracket_identifier" and character == "]":
            state = "normal"
        index += 1
    return False


def validate_read_only_statement(statement: str) -> str:
    normalized = normalize_sql(statement)
    segments = _statement_segments(normalized)
    if len(segments) != 1:
        raise ReadOnlyViolationError("Only one read-only SQL statement is allowed")

    candidate = segments[0]
    keyword_match = re.match(r"([A-Za-z]+)\b", candidate)
    if keyword_match is None:
        raise ReadOnlyViolationError("Only read-only SQL statements are allowed")

    keyword = keyword_match.group(1).upper()
    if keyword in {"SELECT", "EXPLAIN"}:
        return candidate
    if keyword != "PRAGMA":
        raise ReadOnlyViolationError("Only read-only SQL statements are allowed")

    pragma_match = re.match(r"PRAGMA\s+([A-Za-z_][A-Za-z0-9_]*)\b", candidate, re.IGNORECASE)
    if pragma_match is None or pragma_match.group(1).lower() not in READ_ONLY_PRAGMAS:
        raise ReadOnlyViolationError("This PRAGMA is not allowed")
    if _has_unquoted_equals(candidate[pragma_match.end() :]):
        raise ReadOnlyViolationError("PRAGMA assignments are not allowed")
    return candidate


class QueryService:
    def __init__(self, connections: ConnectionManager) -> None:
        self._connections = connections

    def execute_read_only(self, connection_id: str, statement: str) -> QueryResult:
        validated_statement = validate_read_only_statement(statement)
        started_at = perf_counter()
        try:
            cursor = self._connections.get(connection_id).execute(validated_statement)
            rows = tuple(tuple(row) for row in cursor.fetchmany(MAX_QUERY_ROWS + 1))
        except sqlite3.Error as error:
            raise DatabaseQueryError("Could not execute SQL query") from error

        columns = tuple(column[0] for column in cursor.description or ())
        was_capped = len(rows) > MAX_QUERY_ROWS
        if was_capped:
            rows = rows[:MAX_QUERY_ROWS]
        return QueryResult(
            columns=columns,
            rows=rows,
            elapsed_ms=(perf_counter() - started_at) * 1_000,
            was_capped=was_capped,
        )

    def fetch_table_page(
        self, connection_id: str, table_name: str, page_number: int
    ) -> PageResult:
        if page_number < 1:
            raise DatabaseQueryError("Page number must be positive")

        identifier = quote_identifier(table_name)
        offset = (page_number - 1) * TABLE_PAGE_SIZE
        try:
            connection = self._connections.get(connection_id)
            total_rows = connection.execute(
                f"SELECT COUNT(*) FROM {identifier}"
            ).fetchone()[0]
            column_info = tuple(connection.execute(f"PRAGMA table_info({identifier})"))
            columns = tuple(column["name"] for column in column_info)
            has_primary_key = any(row["pk"] for row in column_info)
            if has_primary_key:
                cursor = connection.execute(
                    f"SELECT * FROM {identifier} LIMIT ? OFFSET ?",
                    (TABLE_PAGE_SIZE, offset),
                )
                rows = tuple(tuple(row) for row in cursor)
                row_ids = (None,) * len(rows)
            elif (row_identifier := hidden_row_identifier(columns)) is None:
                cursor = connection.execute(
                    f"SELECT * FROM {identifier} LIMIT ? OFFSET ?",
                    (TABLE_PAGE_SIZE, offset),
                )
                rows = tuple(tuple(row) for row in cursor)
                row_ids = (None,) * len(rows)
            else:
                cursor = connection.execute(
                    f"SELECT {quote_identifier(row_identifier)}, * FROM {identifier} LIMIT ? OFFSET ?",
                    (TABLE_PAGE_SIZE, offset),
                )
                raw_rows = tuple(tuple(row) for row in cursor)
                row_ids = tuple(row[0] for row in raw_rows)
                rows = tuple(row[1:] for row in raw_rows)
        except sqlite3.Error as error:
            raise DatabaseQueryError(f"Could not load table data for {table_name}") from error

        return PageResult(
            columns=columns,
            rows=rows,
            page_number=page_number,
            page_size=TABLE_PAGE_SIZE,
            has_next_page=offset + len(rows) < total_rows,
            total_rows=total_rows,
            row_ids=row_ids,
        )
