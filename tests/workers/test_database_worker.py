from PySide6.QtCore import QThreadPool

from sqlite_viewer.models.errors import DatabaseQueryError
from sqlite_viewer.workers.database_worker import DatabaseWorker


def test_worker_emits_successful_result(qtbot):
    worker = DatabaseWorker(lambda: ("loaded", 3))

    with qtbot.waitSignal(worker.signals.succeeded, timeout=1_000) as signal:
        QThreadPool.globalInstance().start(worker)

    assert signal.args == [("loaded", 3)]


def test_worker_emits_domain_error_message(qtbot):
    worker = DatabaseWorker(lambda: (_ for _ in ()).throw(DatabaseQueryError("invalid SQL")))

    with qtbot.waitSignal(worker.signals.failed, timeout=1_000) as signal:
        QThreadPool.globalInstance().start(worker)

    assert signal.args == ["invalid SQL"]


def test_worker_does_not_block_qt_event_loop(qtbot):
    worker = DatabaseWorker(lambda: "completed")
    received = []
    worker.signals.succeeded.connect(received.append)

    QThreadPool.globalInstance().start(worker)

    qtbot.waitUntil(lambda: received == ["completed"], timeout=1_000)
