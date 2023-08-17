from gui import Ui_MainWindow
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QListView, QVBoxLayout, QWidget,
                             QStyledItemDelegate, QStyle, QMenu, QAction, QDialog, QLabel, QFormLayout, 
                             QLineEdit, QMessageBox)
from PyQt5.QtCore import QStringListModel, QAbstractListModel, Qt, QSize, QPoint, QThread, pyqtSignal, QTimer, QModelIndex
from PyQt5.QtGui import QPainter, QColor, QIcon, QFontDatabase, QStandardItemModel, QStandardItem
from sys import argv as sys_argv, exit as sys_exit
from peerconn import PeerConn, PeerData
from asyncio import run as async_run
from time import sleep

class PeerConnThread(QThread):
    peerconn_ref: PeerConn | None
    terminate_thread = pyqtSignal()

    def __init__(self, peerconn_ref: PeerConn):
        super().__init__()
        self.peerconn_ref = peerconn_ref

    def run(self):
        async_run(self.peerconn_ref.thread_main())
        self.terminate_thread.emit()

class DialogListen(QDialog):
    def __init__(self, local_address: str) -> None:
        super().__init__()
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle('Create Listener')
        self.setFixedSize(240, 240)
        layout = QFormLayout()
        self.QLineEdit_display_name = QLineEdit()
        layout.addRow(QLabel('Display Name'), self.QLineEdit_display_name)
        self.QLineEdit_local_address = QLineEdit(local_address)
        self.QLineEdit_local_address.setReadOnly(True)
        layout.addRow(QLabel('Address'), self.QLineEdit_local_address)
        self.QLineEdit_msg_port = QLineEdit()
        layout.addRow(QLabel('Message Port'), self.QLineEdit_msg_port)
        self.QLineEdit_file_port = QLineEdit()
        layout.addRow(QLabel('File Port'), self.QLineEdit_file_port)
        self.QPushButton_create_listener = QPushButton('Create')
        self.QPushButton_create_listener.clicked.connect(self.accept)
        layout.addRow(self.QPushButton_create_listener)
        self.QPushButton_cancel = QPushButton('Cancel')
        self.QPushButton_cancel.clicked.connect(self.reject)
        layout.addRow(self.QPushButton_cancel)
        self.setLayout(layout)

class EditConnectionItem(QDialog):
    def __init__(self, peerdata: PeerData) -> None:
        super().__init__()
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle(f'Edit {peerdata.name}')
        self.setFixedSize(240, 240)
        layout = QFormLayout()
        self.QLineEdit_display_name = QLineEdit(peerdata.name)
        layout.addRow(QLabel('Display Name'), self.QLineEdit_display_name)
        self.QLineEdit_local_address = QLineEdit(peerdata.local_address)
        self.QLineEdit_local_address.setReadOnly(True)
        layout.addRow(QLabel('Address'), self.QLineEdit_local_address)
        self.QLineEdit_msg_port = QLineEdit(str(peerdata.msg_port))
        self.QLineEdit_msg_port.setReadOnly(True)
        layout.addRow(QLabel('Message Port'), self.QLineEdit_msg_port)
        self.QLineEdit_file_port = QLineEdit(str(peerdata.file_port))
        self.QLineEdit_file_port.setReadOnly(True)
        layout.addRow(QLabel('File Port'), self.QLineEdit_file_port)
        self.QPushButton_save_changes = QPushButton('Save')
        self.QPushButton_save_changes.clicked.connect(self.accept)
        layout.addRow(self.QPushButton_save_changes)
        self.QPushButton_cancel = QPushButton('Cancel')
        self.QPushButton_cancel.clicked.connect(self.reject)
        layout.addRow(self.QPushButton_cancel)
        self.setLayout(layout)

class PeerConnGUI:
    # Main Window Constants
    MWINDOW_TITLE: str = 'PeerConn - GUI'
    # Properties
    _peerconn: PeerConn | None
    _peerconn_thread: PeerConnThread | None
    _app: QApplication | None
    _ui: Ui_MainWindow | None
    _main_window: QMainWindow | None
    _dialog: QDialog | None = None
    _qtimer_update_ui: QTimer | None
    # QListView Models
    _model_active_connections: QStandardItemModel | None
    _model_chat: QStandardItemModel | None
    # Flags
    _i_sent: bool = False
    # Icon Names
    conn_active: str = 'conn_active.png'
    conn_inactive: str = 'conn_inactive.png'

    def __init__(self) -> None:
        self._peerconn = PeerConn()
        self._app = QApplication(sys_argv)
        self._peerconn_thread = PeerConnThread(self._peerconn)
        self._peerconn_thread.start()
        self._qtimer_update_ui = QTimer()
        self._qtimer_update_ui.timeout.connect(self.update_ui)
        self._qtimer_update_ui.start(50)
        self.set_ui()
        self._peerconn._logger.info(f'UI-{PeerConnGUI.__name__}: Initialized.')

    def set_ui(self) -> None:
        self._main_window = QMainWindow()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self._main_window)
        self._main_window.setWindowTitle(self.MWINDOW_TITLE)
        self.set_user_data_ui()
        self._ui.lineEdit_message.returnPressed.connect(self.send_message)
        self.set_buttons()
        self.set_QListViews()

    def set_user_data_ui(self):
        self._ui.lineEdit_user_hostname.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ui.lineEdit_user_hostname.setText(self._peerconn._peerdata.name)
        self._ui.lineEdit_user_hostname.setReadOnly(True)
        
        self._ui.lineEdit_user_local_address.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ui.lineEdit_user_local_address.setText(self._peerconn._peerdata.local_address)
        self._ui.lineEdit_user_local_address.setReadOnly(True)

        self._ui.lineEdit_user_auto_port.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ui.lineEdit_user_auto_port.setReadOnly(True)
        self._ui.lineEdit_user_auto_port.setEnabled(False)
        self._peerconn._logger.info(f'UI-{self.set_user_data_ui.__name__}: Set.')

    def set_buttons(self):
        self._ui.pushButton_listen.clicked.connect(self.listen_dialog)
        self._ui.pushButton_send.clicked.connect(self.send_message)
        self._peerconn._logger.info(f'UI-{self.set_buttons.__name__}: Set.')

    def send_message(self):
        index = self._ui.listView_active_connections.currentIndex()
        if index.isValid():
            selected_item = self._model_active_connections.itemFromIndex(index)
            if selected_item:
                peersocket_id = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                my_message = self._ui.lineEdit_message.text()
                self._peerconn.send_message(peersocket_id, my_message)
                self._i_sent = True
                self._ui.lineEdit_message.clear()

    def listen_dialog(self):
        try:
            self._dialog = DialogListen(self._peerconn._peerdata.local_address)
            self._peerconn._logger.info(f'UI-{self.listen_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                display_name = self._dialog.QLineEdit_display_name.text()
                local_address = self._dialog.QLineEdit_local_address.text()
                msg_port = int(self._dialog.QLineEdit_msg_port.text())
                file_port = int(self._dialog.QLineEdit_file_port.text())
                if msg_port != file_port:
                    peerdata = PeerData(display_name, local_address, msg_port, file_port)
                    id = self._peerconn.create_peer_socket()
                    self._peerconn.set_peersocket(id, peerdata)
                    self._peerconn.set_listener(id)
                    item = QStandardItem(peerdata.name)
                    item.setIcon(QIcon(self.conn_inactive))
                    item.setData(id, Qt.ItemDataRole.UserRole + 1)
                    self._model_active_connections.appendRow(item)
                else:
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Wrong Inputs')
                    message_box.setText('Check if IP address is correct and ports are different.')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.listen_dialog.__name__}: {ex}')

    def editConnectionItem_dialog(self):
        try:
            index = self._ui.listView_active_connections.currentIndex()
            item = self._model_active_connections.itemFromIndex(index)
            peersocket_id = item.data(Qt.ItemDataRole.UserRole + 1)
            self._dialog = EditConnectionItem(self._peerconn.get_socket(peersocket_id).peerdata)
            self._peerconn._logger.info(f'UI-{self.editConnectionItem_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                display_name = self._dialog.QLineEdit_display_name.text()
                local_address = self._dialog.QLineEdit_local_address.text()
                msg_port = int(self._dialog.QLineEdit_msg_port.text())
                file_port = int(self._dialog.QLineEdit_file_port.text())

                peerdata = PeerData(display_name, local_address, msg_port, file_port)
                self._peerconn.set_peersocket(peersocket_id, peerdata)
                self._model_active_connections.itemFromIndex(index).setText(peerdata.name)
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.editConnectionItem_dialog.__name__}: {ex}')

    def set_QListViews(self):
        self._model_active_connections = QStandardItemModel()
        self._ui.listView_active_connections.setModel(self._model_active_connections)
        self._ui.listView_active_connections.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ui.listView_active_connections.customContextMenuRequested.connect(self.context_menu_active_connections)
        self._ui.listView_active_connections.selectionModel().currentChanged.connect(self.on_connection_selection)

        self._model_chat = QStandardItemModel()
        self._ui.listView_chat.setModel(self._model_chat)
        self._peerconn._logger.info(f'UI-{self.set_QListViews.__name__}: Initialized')

    def context_menu_active_connections(self, position: QPoint):
        index = self._ui.listView_active_connections.indexAt(position)
        if index.isValid():
            menu = QMenu(self._ui.listView_active_connections)
            edit_action = QAction("Edit", menu)
            disconnect_action = QAction("Disconnect", menu)
            menu.addAction(edit_action)
            menu.addAction(disconnect_action)
            action = menu.exec_(self._ui.listView_active_connections.viewport().mapToGlobal(position))
            item = self._model_active_connections.itemFromIndex(index)
            item_id = item.data(Qt.ItemDataRole.UserRole + 1)
            if action == edit_action:
                self.editConnectionItem_dialog()
            elif action == disconnect_action:
                self._peerconn.disconnect(item_id)
                self._model_active_connections.removeRow(index.row())

    def update_ui(self):
        self.update_chat()
        active_connections = self._peerconn.get_active_connections()
        item_list = self._model_active_connections.findItems("*", Qt.MatchFlag.MatchWildcard)
        if active_connections != None:
            index = self._ui.listView_active_connections.currentIndex()
            for i in range(0, len(active_connections)):
                if active_connections[i].msg_comm_connected and active_connections[i].file_comm_connected:
                    item_list[i].setIcon(QIcon(self.conn_active))

    def on_connection_selection(self):
        self._model_chat.clear()

    def update_chat(self):
        index = self._ui.listView_active_connections.currentIndex()
        if index.isValid():
            selected_item = self._model_active_connections.itemFromIndex(index)
            if selected_item:
                peersocket_id = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                history = self._peerconn.get_socket(peersocket_id).history
                if history.new_messages > 0 or self._i_sent:
                    for i in range(self._model_chat.rowCount(), len(history.messages)):
                            msg = history.messages[i]
                            self._model_chat.appendRow(
                                QStandardItem(
                                    f'{msg.date_time.day}.{msg.date_time.month}.{msg.date_time.year} - {msg.date_time.hour}:{msg.date_time.minute} - {msg.sender}: {msg.content}'
                                )
                            )
                    history.new_messages = 0
                    self._i_sent = False

    def on_exit(self):
        self._peerconn.exit()
        sleep(2.0)
        self._peerconn_thread.terminate()
        self._peerconn._logger.info(f'UI-{self.on_exit.__name__}: Executed.')
    
    def main(self) -> None:
        self._main_window.show()
        self._app.aboutToQuit.connect(self.on_exit) 
        sys_exit(self._app.exec_())

if __name__ == '__main__':
    peerconn_gui = PeerConnGUI()
    peerconn_gui.main()