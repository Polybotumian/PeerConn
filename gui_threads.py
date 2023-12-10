from PyQt5.QtCore import (QThread, pyqtSignal)
from peerconn import PeerConn
from asyncio import run as async_run

class PeerConnThread(QThread):
    peerconn_ref: PeerConn | None
    terminate_thread = pyqtSignal()

    def __init__(self, peerconn_ref: PeerConn) -> None:
        super().__init__()
        self.peerconn_ref = peerconn_ref

    def run(self) -> None:
        async_run(self.peerconn_ref.thread_main())
        self.terminate_thread.emit()