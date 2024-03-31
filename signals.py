from PyQt5.QtCore import pyqtSignal, QObject
from dtos import PDTO

class Communication(QObject):
    received = pyqtSignal(str, str)
    send = pyqtSignal(str, str)
    close = pyqtSignal(str)

class PeerInfo(QObject):
    descriptive = pyqtSignal(PDTO)