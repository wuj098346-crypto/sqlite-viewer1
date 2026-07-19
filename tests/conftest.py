import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest


STUDENT_ROWS = (
    (1, "Alice", 1),
    (2, "Bob", 1),
    (3, "Charlie", 2),
)


@pytest.fixture
def original_student_rows() -> tuple[tuple[int, str, int], ...]:
    return STUDENT_ROWS


@pytest.fixture
def sqlite_db_path(tmp_path: Path) -> Path:
    database_path = tmp_path / "sample.sqlite"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                enrolled_at TEXT DEFAULT '2026-07-19',
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
            CREATE INDEX idx_students_course_id ON students(course_id);
            CREATE VIEW student_course_view AS
                SELECT students.id AS student_id, students.name, courses.title AS course_title
                FROM students
                JOIN courses ON courses.id = students.course_id;
            """
        )
        connection.executemany(
            "INSERT INTO courses (id, title) VALUES (?, ?)",
            ((1, "Mathematics"), (2, "Literature")),
        )
        connection.executemany(
            "INSERT INTO students (id, name, course_id) VALUES (?, ?, ?)",
            STUDENT_ROWS,
        )

    return database_path


@pytest.fixture
def read_students() -> Callable[[Path], tuple[tuple[int, str, int], ...]]:
    def read(path: Path) -> tuple[tuple[int, str, int], ...]:
        with sqlite3.connect(path) as connection:
            return tuple(
                connection.execute(
                    "SELECT id, name, course_id FROM students ORDER BY id"
                )
            )

    return read
