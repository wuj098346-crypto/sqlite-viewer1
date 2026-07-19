import sys

from PySide6.QtWidgets import QApplication

from sqlite_viewer.presentation.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setOrganizationName("SQLite Viewer")
    application.setApplicationName("SQLite Viewer")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
