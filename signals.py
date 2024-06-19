from PyQt5.QtCore import pyqtSignal, QObject
from data_models import BPI


class Communication(QObject):
    received_msg = pyqtSignal(str, str)
    msg_send = pyqtSignal(str, str)
    file_send = pyqtSignal(str, str)
    conn_close = pyqtSignal(str)
    conn_lost = pyqtSignal(str, str)
    peer_info = pyqtSignal(BPI)
    file_percentage = pyqtSignal(str, int)
    notification = pyqtSignal(str, str)