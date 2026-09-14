"""Model downloads for the onboarding and settings screens, reported to QML."""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import Property, QObject, Signal, Slot

from .. import models
from ..downloads import download


class DownloadService(QObject):
    itemsChanged = Signal()
    busyChanged = Signal()
    finished = Signal(bool, str)  # success, error message
    _progress = Signal(str, float, float)  # model id, bytes done, bytes total (from the thread)
    _state = Signal(str, str)  # model id, state

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._busy = False
        self._progress.connect(self._on_progress)
        self._state.connect(self._on_state)

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list:
        return self._items

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Slot("QStringList")
    def start(self, model_ids: list[str]) -> None:
        if self._busy:
            return
        specs = [models.get_model(m) for m in model_ids]
        self._items = [
            {"id": s.id, "label": s.label, "done": 0.0, "total": s.size_mb * 1e6, "rate": 0.0,
             "state": "done" if models.is_installed(s) else "waiting"}
            for s in specs
        ]
        self._busy = True
        self.itemsChanged.emit()
        self.busyChanged.emit()
        threading.Thread(target=self._run, args=(specs,), name="model-downloads", daemon=True).start()

    def _run(self, specs: list[models.ModelSpec]) -> None:
        error = ""
        for spec in specs:
            if models.is_installed(spec):
                continue
            self._state.emit(spec.id, "downloading")
            try:
                download(spec, lambda done, total, sid=spec.id: self._progress.emit(sid, float(done), float(total)))
                self._state.emit(spec.id, "done")
            except Exception as exc:
                error = f"Couldn't download {spec.label}: {exc}"
                self._state.emit(spec.id, "failed")
                break
        self._state.emit("", "finished:" + error)

    def _on_progress(self, model_id: str, done: float, total: float) -> None:
        now = time.monotonic()
        for item in self._items:
            if item["id"] == model_id:
                started = item.setdefault("_t0", now)
                item["done"], item["total"] = done, total
                item["rate"] = done / max(now - started, 1e-6)
        self._items = [dict(i) for i in self._items]
        self.itemsChanged.emit()

    def _on_state(self, model_id: str, state: str) -> None:
        if state.startswith("finished:"):
            error = state.split(":", 1)[1]
            self._busy = False
            self.busyChanged.emit()
            self.finished.emit(not error, error)
            return
        for item in self._items:
            if item["id"] == model_id:
                item["state"] = state
                if state == "done":
                    item["done"] = item["total"]
        self._items = [dict(i) for i in self._items]
        self.itemsChanged.emit()
