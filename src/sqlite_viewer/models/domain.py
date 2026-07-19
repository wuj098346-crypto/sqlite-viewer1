from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class DatabaseIdentity:
    path: Path
    display_name: str


@dataclass(frozen=True)
class DatabaseObject:
    object_type: Literal["table", "view", "index"]
    name: str
    table_name: str | None


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    declared_type: str
    is_primary_key: bool
    is_not_null: bool
    default_value: str | None


@dataclass(frozen=True)
class PageResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    page_number: int
    page_size: int
    has_next_page: bool
    total_rows: int | None
    row_ids: tuple[int | None, ...] = ()


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    elapsed_ms: float
    was_capped: bool
