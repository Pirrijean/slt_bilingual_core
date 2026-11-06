"""Asynchronous worker infrastructure ensuring GUI responsiveness for heavy tasks."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by background worker runnables."""

    started = Signal()
    finished = Signal()
    error = Signal(str, str)  # (error_type, error_traceback)
    result = Signal(object)
    progress = Signal(int)  # 0 to 100 percentage


class WorkerRunnable(QRunnable):
    """Executes a callable inside the QThreadPool without blocking the main event loop."""

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        """Run the wrapped function inside worker thread and emit appropriate signals."""
        self.signals.started.emit()
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(res)
        except Exception as exc:
            trace = traceback.format_exc()
            self.signals.error.emit(str(exc), trace)
        finally:
            self.signals.finished.emit()
