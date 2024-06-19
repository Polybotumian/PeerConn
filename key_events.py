from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtGui import QKeyEvent


class Mekef(QObject):
    """
    Message Edit Event Filter (Mekef)
    """

    def __init__(self, parent: QPlainTextEdit = None, send_message_callback=None):
        super().__init__(parent)
        self.send_message_callback = send_message_callback

    def eventFilter(self, obj, event):
        if event.type() == QKeyEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if self.send_message_callback:
                    self.send_message_callback()
                return True
        return super().eventFilter(obj, event)
