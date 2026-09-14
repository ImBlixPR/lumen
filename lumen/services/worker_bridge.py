"""Runs the pipeline in a separate process and turns its events into Qt signals.

A reader thread blocks on the event queue and re-emits each event through a signal. Qt
queues it onto the main thread, so no model call can ever stall the UI or the audio.
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import threading
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..pipeline import worker


class WorkerBridge(QObject):
    event = Signal(object)  # dict from the worker, delivered on the main thread
    crashed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._ctx = mp.get_context("spawn")
        self._commands = None
        self._events = None
        self._process = None
        self._reader: threading.Thread | None = None
        self._stopping = False

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stopping = False
        self._commands = self._ctx.Queue()
        self._events = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=worker.run, args=(self._commands, self._events), name="lumen-worker", daemon=True
        )
        self._process.start()
        self._reader = threading.Thread(target=self._read_events, name="lumen-worker-events", daemon=True)
        self._reader.start()

    def send(self, command: dict[str, Any]) -> None:
        if not self.running:
            self.start()
        self._commands.put(command)

    def stop(self) -> None:
        self._stopping = True
        if self._process is None:
            return
        if self._process.is_alive():
            self._commands.put({"type": "shutdown"})
            self._process.join(timeout=3)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=2)
        self._process = None

    def _read_events(self) -> None:
        process, events = self._process, self._events
        while True:
            try:
                self.event.emit(events.get(timeout=0.5))
            except queue.Empty:
                if not process.is_alive():
                    if not self._stopping:
                        self.crashed.emit()
                    return
            except (EOFError, OSError):
                return
