from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class DatabaseWorkerSignals(QObject):
    started = Signal()
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class DatabaseWorker(QRunnable):
    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation
        self.signals = DatabaseWorkerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            self.signals.succeeded.emit(self._operation())
        except Exception as error:
            self.signals.failed.emit(str(error))
        finally:
            self.signals.finished.emit()
