from pathlib import Path

from sqlite_viewer.presentation.main_window import MainWindow


def test_opening_supported_database_creates_closable_tab(qtbot, sqlite_db_path):
    window = MainWindow()
    qtbot.addWidget(window)

    window.open_database(sqlite_db_path)

    assert window.database_tabs.count() == 1
    assert window.database_tabs.tabText(0) == "sample.sqlite"
    assert window.database_tabs.tabsClosable() is True


def test_unsupported_database_path_shows_error_without_tab(qtbot, tmp_path: Path):
    window = MainWindow()
    qtbot.addWidget(window)
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not sqlite", encoding="utf-8")

    window.open_database(unsupported)

    assert window.database_tabs.count() == 0
    assert "Unsupported" in window.statusBar().currentMessage()


def test_recent_files_are_deduplicated_and_limited(qtbot, tmp_path: Path):
    window = MainWindow()
    qtbot.addWidget(window)

    for number in range(12):
        window.remember_recent_file(tmp_path / f"database-{number}.sqlite")
    window.remember_recent_file(tmp_path / "database-11.sqlite")

    assert len(window.recent_files()) == 10
    assert window.recent_files()[0].name == "database-11.sqlite"
