from PyQt5.QtCore import pyqtSignal, QObject
from dmodels import BPI

class Communication(QObject):
    received = pyqtSignal(str, str)
    sendMsg = pyqtSignal(str, str)
    sendFile = pyqtSignal(str, str)
    close = pyqtSignal(str)
    lost = pyqtSignal(str, str)

class PeerInfo(QObject):
    descriptive = pyqtSignal(BPI)