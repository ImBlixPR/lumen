"""Single-instance command channel.

A second launch forwards its request to the running instance and exits:

    lumen --cmd play-pause        (also back-sentence, toggle-overlay, lock-overlay, show, quit)
    lumen "D:/Books/novela.m4b"   (opens the book in the running instance)

That keeps one overlay and one worker. It also lets any launcher or shortcut tool drive
Lumen when a global hotkey is taken.
"""

from __future__ import annotations

import getpass
import hashlib

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

COMMANDS = ("play-pause", "back-sentence", "toggle-overlay", "lock-overlay", "show", "quit")


def server_name() -> str:
    user = hashlib.sha1(getpass.getuser().encode()).hexdigest()[:10]
    return f"lumen-{user}"


def send_to_running(message: str, timeout_ms: int = 800) -> bool:
    """Deliver `message` to a running instance. False if none is listening."""
    socket = QLocalSocket()
    socket.connectToServer(server_name())
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write((message + "\n").encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class CommandServer(QObject):
    received = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._accept)

    def listen(self) -> bool:
        QLocalServer.removeServer(server_name())  # clear a stale endpoint after a crash
        return self._server.listen(server_name())

    def _accept(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _read(self, socket: QLocalSocket) -> None:
        while socket.canReadLine():
            line = bytes(socket.readLine()).decode("utf-8", "replace").strip()
            if line:
                self.received.emit(line)
