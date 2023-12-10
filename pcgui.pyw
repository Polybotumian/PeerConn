from gui import (Ui_MainWindow)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenu, QAction, QDialog, QLineEdit, QMessageBox, QFileDialog)
from PyQt5.QtCore import (Qt, QPoint, QTimer)
from PyQt5.QtGui import (QColor, QIcon, QStandardItemModel, QStandardItem)
from sys import (argv as sys_argv, exit as sys_exit)
from peerconn import (PeerConn, PeerData, MessageTypes)
from time import (sleep)
from os import (path)
from functools import (partial)
from gui_dialogs import (DialogChangeConfigs, DialogEditConnectionItem, DialogConnect, DialogListen)
from gui_threads import (PeerConnThread)

class PeerConnGUI:
    # Main Window Constants
    MAIN_WINDOW_TITLE: str = 'PeerConn - GUI (v231217)'
    # Properties
    _peerconn:                        PeerConn | None = None
    _peerconn_thread:           PeerConnThread | None = None
    _app:                         QApplication | None = None
    _ui:                         Ui_MainWindow | None = None
    _main_window:                  QMainWindow | None = None
    _dialog:                           QDialog | None = None
    _qtimer_update_ui:                  QTimer | None = None
    ICON_FOLDER:                           str | None = None
    # QListView Models
    _model_socket_list: QStandardItemModel | None = None
    _model_chat: QStandardItemModel | None = None
    # Flags
    _update_chat: bool = False
    # Icons Names
    icon_client_active:     QIcon | None = None
    icon_client_inactive:   QIcon | None = None
    icon_client_waiting:    QIcon | None = None
    icon_server_active:     QIcon | None = None
    icon_server_inactive:   QIcon | None = None
    icon_server_waiting:    QIcon | None = None

    def __init__(self) -> None:
        self._peerconn = PeerConn()
        self._app = QApplication(sys_argv)
        self._peerconn_thread = PeerConnThread(self._peerconn)
        self._peerconn_thread.start()
        self._qtimer_update_ui = QTimer()
        self._qtimer_update_ui.timeout.connect(self.update_ui)
        self._qtimer_update_ui.start(250)
        self.set_ui()
        self._peerconn._logger.info(f'UI-{PeerConnGUI.__name__}: Initialized.')

    def set_ui(self) -> None:
        self._main_window = QMainWindow()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self._main_window)
        self.ICON_FOLDER = path.join(self._peerconn._BASE_PATH, 'icons')
        self.icon_client_active = QIcon(path.join(self.ICON_FOLDER, 'sockets/client_active.png'))
        self.icon_client_inactive = QIcon(path.join(self.ICON_FOLDER,'sockets/client_inactive.png'))
        self.icon_client_waiting = QIcon(path.join(self.ICON_FOLDER,'sockets/client_waiting.png'))
        self.icon_server_active = QIcon(path.join(self.ICON_FOLDER,'sockets/server_active.png'))
        self.icon_server_inactive = QIcon(path.join(self.ICON_FOLDER,'sockets/server_inactive.png'))
        self.icon_server_waiting = QIcon(path.join(self.ICON_FOLDER,'sockets/server_waiting.png'))
        self._main_window.setWindowTitle(self.MAIN_WINDOW_TITLE)
        self._main_window.setWindowIcon(QIcon(path.join(self.ICON_FOLDER,'window/peerconn.png')))
        self.set_user_data_ui()
        self._ui.listView_chat.setEnabled(False)
        self._ui.lineEdit_message.setMaxLength(512)
        self._ui.lineEdit_message.returnPressed.connect(self.send_message)
        self._ui.lineEdit_message.setEnabled(False)
        self._ui.progressBar_file.setHidden(True)
        self.set_buttons()
        self.set_QListViews()
        self.set_toolbar_actions()

    def set_toolbar_actions(self) -> None:
        self._ui.actionPreferences.setEnabled(False)
        self._ui.actionHelp.triggered.connect(lambda:self._ui.stackedWidget.setCurrentIndex(1))
        self._ui.actionAbout.triggered.connect(lambda:self._ui.stackedWidget.setCurrentIndex(2))
        self._ui.actionChange_My_Data.triggered.connect(self.show_change_configs_dialog)

    def set_user_data_ui(self) -> None:
        self._ui.lineEdit_user_hostname.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ui.lineEdit_user_hostname.setText(self._peerconn._peerdata.name)
        self._ui.lineEdit_user_hostname.setReadOnly(True)
        
        self._ui.lineEdit_user_local_address.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ui.lineEdit_user_local_address.setText(self._peerconn._peerdata.local_address)
        self._ui.lineEdit_user_local_address.setReadOnly(True)

        self._peerconn._logger.info(f'UI-{self.set_user_data_ui.__name__}: Set.')

    def set_buttons(self) -> None:
        self._ui.pushButton_listen.clicked.connect(self.show_listen_dialog)
        self._ui.pushButton_connect.clicked.connect(self.show_connect_dialog)
        self._ui.pushButton_send_message.clicked.connect(self.send_message)
        self._ui.pushButton_send_message.setEnabled(False)
        self._ui.pushButton_about_back.clicked.connect(lambda:self._ui.stackedWidget.setCurrentIndex(0))
        self._ui.pushButton_guide_back.clicked.connect(lambda:self._ui.stackedWidget.setCurrentIndex(0))
        self._ui.pushButton_file.clicked.connect(partial(self.pick_file, self._ui.lineEdit_file_path))
        self._ui.pushButton_file.setEnabled(False)
        self._peerconn._logger.info(f'UI-{self.set_buttons.__name__}: Set.')

    def send_message(self) -> None:
        index = self._ui.listView_sockets.currentIndex()
        if index.isValid() and self._ui.lineEdit_message.text():
            selected_item = self._model_socket_list.itemFromIndex(index)
            if selected_item:
                peersocket_id = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                my_message = self._ui.lineEdit_message.text()
                self._peerconn.send_message(peersocket_id, my_message)
                self._update_chat = True
                self._ui.lineEdit_message.clear()

    def send_file(self) -> None:
        index = self._ui.listView_sockets.currentIndex()
        if index.isValid() and self._ui.lineEdit_file_path.text():
            selected_item = self._model_socket_list.itemFromIndex(index)
            if selected_item:
                peersocket_id = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                file_path = self._ui.lineEdit_file_path.text()
                self._peerconn.send_file(peersocket_id, file_path)
                self._update_chat = True
                self._ui.lineEdit_file_path.clear()
        else:
            message_box = QMessageBox()
            message_box.setWindowTitle('No File Path')
            message_box.setText('You have\'nt select a file, you cannot use "Send File" button!')
            message_box.setIcon(QMessageBox.Icon.Warning)
            message_box.addButton(QMessageBox.StandardButton.Ok)
            message_box.exec_()

    def cancel_file(self, peersocket_id: str) -> None:
        self._peerconn.cancel_file(peersocket_id)
    
    def pick_file(self, line_edit: QLineEdit):
        options = QFileDialog.Options()
        options |= QFileDialog.Option.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(self._main_window, "Select File", "", "All Files (*)", options= options)
        if file_path:
            line_edit.setText(file_path)

    def show_listen_dialog(self) -> None:
        try:
            self._dialog = DialogListen(self._peerconn._peerdata.local_address)
            self._peerconn._logger.info(f'UI-{self.show_listen_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                display_name = self._dialog.QLineEdit_display_name.text()
                local_address = self._dialog.QLineEdit_local_address.text()
                msg_port = self._dialog.QSpinBox_msg_port.value()
                file_port = self._dialog.QSpinBox_file_port.value()
                if len(display_name) > 0 and self._peerconn.is_valid_ipv4(local_address) and msg_port != file_port:
                    peerdata = PeerData(display_name, local_address, msg_port, file_port)
                    id = self._peerconn.create_peer_socket()
                    self._peerconn.set_peersocket(id, peerdata)
                    self._peerconn.set_server(id)
                    item = QStandardItem(peerdata.name)
                    item.setToolTip(f'Address: {peerdata.local_address}\nMessage Port: {peerdata.msg_port}\nFile Port: {peerdata.file_port}')
                    item.setIcon(self.icon_server_waiting)
                    item.setData(id, Qt.ItemDataRole.UserRole + 1)
                    self._model_socket_list.appendRow(item)
                else:
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Wrong Inputs')
                    message_box.setText('Check if display name is not empty and IP address is correct and ports are different.')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.show_listen_dialog.__name__}: {ex}')

    def show_connect_dialog(self) -> None:
        try:
            self._dialog = DialogConnect()
            self._peerconn._logger.info(f'UI-{self.show_connect_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                display_name = self._dialog.QLineEdit_display_name.text()
                local_address = self._dialog.QLineEdit_local_address.text()
                msg_port = self._dialog.QSpinBox_msg_port.value()
                file_port = self._dialog.QSpinBox_file_port.value()
                if len(display_name) > 0 and self._peerconn.is_valid_ipv4(local_address) and msg_port != file_port:
                    peerdata = PeerData(display_name, local_address, msg_port, file_port)
                    id = self._peerconn.create_peer_socket()
                    self._peerconn.set_peersocket(id, peerdata)
                    self._peerconn.connect(id)
                    item = QStandardItem(peerdata.name)
                    item.setIcon(self.icon_client_waiting)
                    item.setData(id, Qt.ItemDataRole.UserRole + 1)
                    self._model_socket_list.appendRow(item)
                else:
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Wrong Inputs')
                    message_box.setText('Check if display name is not empty and IP address is correct and ports are different.')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.show_connect_dialog.__name__}: {ex}')

    def show_edit_connection_item_dialog(self) -> None:
        try:
            index = self._ui.listView_sockets.currentIndex()
            item = self._model_socket_list.itemFromIndex(index)
            peersocket_id = item.data(Qt.ItemDataRole.UserRole + 1)
            self._dialog = DialogEditConnectionItem(self._peerconn.get_socket(peersocket_id).peerdata)
            self._peerconn._logger.info(f'UI-{self.show_edit_connection_item_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                display_name = self._dialog.QLineEdit_display_name.text()
                local_address = self._dialog.QLineEdit_local_address.text()
                msg_port = int(self._dialog.QLineEdit_msg_port.text())
                file_port = int(self._dialog.QLineEdit_file_port.text())

                peerdata = PeerData(display_name, local_address, msg_port, file_port)
                self._peerconn.set_peersocket(peersocket_id, peerdata)
                self._model_socket_list.itemFromIndex(index).setText(peerdata.name)
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.show_edit_connection_item_dialog.__name__}: {ex}')

    def show_change_configs_dialog(self) -> None:
        try:
            self._dialog = DialogChangeConfigs(self._peerconn._peerdata, self._peerconn._DOWNLOADS_DIR)
            message_box = QMessageBox()
            self._peerconn._logger.info(f'UI-{self.show_change_configs_dialog.__name__}: Executed.')
            if self._dialog.exec_() == QDialog.DialogCode.Accepted:
                if len(self._dialog.QLineEdit_display_name.text()) > 0:
                    self._peerconn._peerdata.name = self._dialog.QLineEdit_display_name.text()
                else:
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Empty Host Name')
                    message_box.setText('You can\'t assign an empty host name!')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
                if self._peerconn.is_valid_ipv4(ip= self._dialog.QLineEdit_local_address.text()) and self._peerconn._peerdata.local_address != self._dialog.QLineEdit_local_address.text():
                    message_box.setWindowTitle('Changing Address')
                    message_box.setText('If you change your local address all active sockets are going to be removed!')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.addButton(QMessageBox.StandardButton.Cancel)
                    if message_box.exec_() == QMessageBox.StandardButton.Ok:
                        self._qtimer_update_ui.stop()
                        self._peerconn.close_all()
                        self._peerconn._peerdata.name = self._dialog.QLineEdit_display_name.text()
                        self._peerconn._peerdata.local_address = self._dialog.QLineEdit_local_address.text()
                        self._model_socket_list.clear()
                        self._model_chat.clear()
                        self._qtimer_update_ui.start(50)
                elif not self._peerconn.is_valid_ipv4(ip= self._dialog.QLineEdit_local_address.text()):
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Wrong IPv4')
                    message_box.setText('Check if IP address format is correct.')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
                if path.isdir(self._dialog.QLineEdit_download_dir_path.text()):
                    self._peerconn._DOWNLOADS_DIR = self._dialog.QLineEdit_download_dir_path.text()
                else:
                    message_box = QMessageBox()
                    message_box.setWindowTitle('Non Existing Directory')
                    message_box.setText('Check if directory path is exists.')
                    message_box.setIcon(QMessageBox.Icon.Warning)
                    message_box.addButton(QMessageBox.StandardButton.Ok)
                    message_box.exec_()
                self._ui.lineEdit_user_hostname.setText(self._peerconn._peerdata.name)
                self._ui.lineEdit_user_local_address.setText(self._peerconn._peerdata.local_address)
                self._peerconn.config_file(True)
        except Exception as ex:
            self._peerconn._logger.error(f'UI-{self.show_change_configs_dialog.__name__}: {ex}')

    def set_QListViews(self) -> None:
        self._model_socket_list = QStandardItemModel()
        self._ui.listView_sockets.setModel(self._model_socket_list)
        self._ui.listView_sockets.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ui.listView_sockets.customContextMenuRequested.connect(self.context_menu_active_connections)
        self._ui.listView_sockets.selectionModel().currentChanged.connect(self.on_connection_selection)

        self._model_chat = QStandardItemModel()
        self._ui.listView_chat.setModel(self._model_chat)
        self._ui.listView_chat.setAutoScroll(True)
        self._peerconn._logger.info(f'UI-{self.set_QListViews.__name__}: Initialized')

    def context_menu_active_connections(self, position: QPoint) -> None:
        index = self._ui.listView_sockets.indexAt(position)
        if index.isValid():
            menu = QMenu(self._ui.listView_sockets)
            edit_action = QAction('Edit', menu)
            disconnect_action = QAction('Disconnect', menu)
            remove_action = QAction('Remove', menu)
            menu.addAction(edit_action)
            menu.addAction(disconnect_action)
            menu.addAction(remove_action)
            action = menu.exec_(self._ui.listView_sockets.viewport().mapToGlobal(position))
            item = self._model_socket_list.itemFromIndex(index)
            item_id = item.data(Qt.ItemDataRole.UserRole + 1)
            if action == edit_action:
                self.show_edit_connection_item_dialog()
            elif action == disconnect_action:
                self._peerconn.close(item_id)
            elif action == remove_action:
                i = item.row()
                self._peerconn.close(item_id)
                sleep(0.1) # Wait for disconnecting from peersocket
                self._peerconn._peersockets.remove(self._peerconn._peersockets[i])
                self._model_socket_list.removeRow(i)

    def update_ui(self) -> None:
        try:
            self.update_chat()
            item_list = self._model_socket_list.findItems('*', Qt.MatchFlag.MatchWildcard)
            if self._peerconn._peersockets != None:
                if not self._ui.listView_sockets.selectionModel().hasSelection() and self._ui.listView_sockets.model().rowCount() > 0:
                    self._ui.listView_sockets.setCurrentIndex(self._ui.listView_sockets.model().index(0, 0))
                    self._ui.listView_chat.setEnabled(True)
                    self._ui.lineEdit_message.setEnabled(True)
                    self._ui.lineEdit_file_path.setEnabled(True)
                    self._ui.pushButton_send_message.setEnabled(True)
                    self._ui.pushButton_file.setEnabled(True)
                elif self._ui.listView_sockets.selectionModel().hasSelection() == False:
                    self._ui.listView_chat.setEnabled(False)
                    self._ui.lineEdit_message.setEnabled(False)
                    self._ui.lineEdit_file_path.setEnabled(False)
                    self._ui.pushButton_send_message.setEnabled(False)
                    self._ui.pushButton_file.setEnabled(False)

                for i in range(0, len(self._peerconn._peersockets)):
                    peersocket_ref = self._peerconn._peersockets[i]

                    if peersocket_ref.servers: # Check if socket is server
                        if (peersocket_ref.msg_comm_connected and
                            peersocket_ref.file_comm_connected):
                            item_list[i].setIcon(self.icon_server_active)
                            
                        elif (not peersocket_ref.servers.msg_server and
                            not peersocket_ref.servers.file_server and
                            not peersocket_ref.msg_comm_connected and
                            not peersocket_ref.file_comm_connected):
                            item_list[i].setIcon(self.icon_server_inactive)

                    elif not peersocket_ref.servers and peersocket_ref.streams:
                        
                        if (peersocket_ref.msg_comm_connected
                            and peersocket_ref.file_comm_connected):
                            item_list[i].setIcon(self.icon_client_active)
                        elif (not peersocket_ref.streams.msg_reader and
                            not peersocket_ref.streams.msg_writer and
                            not peersocket_ref.streams.file_reader and
                            not peersocket_ref.streams.file_writer and
                            not peersocket_ref.msg_comm_connected and
                            not peersocket_ref.file_comm_connected):
                            item_list[i].setIcon(self.icon_client_inactive)
        except Exception as ex:
            self._peerconn._logger.error(f'{self.update_ui.__name__}: {ex}')

    def on_connection_selection(self) -> None:
        self._model_chat.clear()
        self._update_chat = True

    def update_chat(self) -> None:
        index = self._ui.listView_sockets.currentIndex()
        if index.isValid():
            selected_item = self._model_socket_list.itemFromIndex(index)
            if selected_item:
                peersocket_id = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                peersocket_ref = self._peerconn.get_socket(peersocket_id)
                if peersocket_ref != None:
                    if len(self._ui.lineEdit_file_path.text()) > 0 and peersocket_ref.in_file_transaction == False:
                        self._ui.pushButton_file.disconnect()
                        self._ui.pushButton_file.clicked.connect(self.send_file)
                        self._ui.pushButton_file.setText('Send File')
                    elif peersocket_ref.in_file_transaction == True:
                        if peersocket_ref.file_percentage == 0:
                            self._ui.pushButton_file.disconnect()
                            self._ui.pushButton_file.clicked.connect(partial(self.cancel_file, peersocket_ref.id))
                            self._ui.pushButton_file.setText('Abort File')
                        self._ui.progressBar_file.setHidden(False)
                        self._ui.progressBar_file.setValue(peersocket_ref.file_percentage)
                    elif peersocket_ref.in_file_transaction == False and len(self._ui.lineEdit_file_path.text()) == 0:
                            self._ui.progressBar_file.setHidden(True)
                            self._ui.progressBar_file.setValue(0)
                            self._ui.pushButton_file.disconnect()
                            self._ui.pushButton_file.clicked.connect(partial(self.pick_file, self._ui.lineEdit_file_path))
                            self._ui.pushButton_file.setText('Pick File')
                    if peersocket_ref.history.new_messages > 0 or self._update_chat:
                        for i in range(self._model_chat.rowCount(), len(peersocket_ref.history.messages)):
                                msg = peersocket_ref.history.messages[i]
                                msg_item = QStandardItem(f'{msg.content}')
                                msg_item.setToolTip(f'{msg.date_time.day}/{msg.date_time.month}/{msg.date_time.year}, {msg.date_time.hour}:{msg.date_time.minute}, {msg.sender}')
                                if msg.type != None:
                                    if msg.type == MessageTypes.CONNECTION_ESTABLISHED:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                        msg_item.setBackground(QColor(40, 160, 40))
                                        msg_item.setForeground(QColor(255, 255, 255))
                                    elif msg.type == MessageTypes.CONNECTION_LOST:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                        msg_item.setBackground(QColor(160, 40, 40))
                                        msg_item.setForeground(QColor(255, 255, 255))
                                    elif msg.type == MessageTypes.ME:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignJustify | Qt.AlignmentFlag.AlignRight)
                                        msg_item.setBackground(QColor(130, 150, 220))
                                        msg_item.setForeground(QColor(0, 0, 0))
                                    elif msg.type == MessageTypes.PEER:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignJustify)
                                        msg_item.setBackground(QColor(80, 100, 170))
                                        msg_item.setForeground(QColor(255, 255, 255))
                                    elif msg.type == MessageTypes.FILE_NOTIFY_0:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                        msg_item.setBackground(QColor(255, 145, 0))
                                        msg_item.setForeground(QColor(0, 0, 0))
                                    elif msg.type == MessageTypes.FILE_NOTIFY_1:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                        msg_item.setBackground(QColor(180, 100, 0))
                                        msg_item.setForeground(QColor(255, 255, 255))
                                    elif msg.type == MessageTypes.SYSTEM_WARN:
                                        msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                        msg_item.setBackground(QColor(100, 0, 250))
                                        msg_item.setForeground(QColor(255, 255, 255))
                                self._model_chat.appendRow(msg_item)
                        last_item_index = self._model_chat.index(self._model_chat.rowCount() - 1, 0)
                        self._ui.listView_chat.scrollTo(last_item_index)
                        peersocket_ref.history.new_messages = 0
                        self._update_chat = False

    def on_exit(self) -> None:
        self._qtimer_update_ui.stop()
        self._peerconn.exit()
        sleep(0.5)
        self._peerconn_thread.terminate()
        sleep(0.5)
        self._peerconn._logger.info(f'UI-{self.on_exit.__name__}: Executed.')
    
    def main(self) -> None:
        self._main_window.show()
        self._app.aboutToQuit.connect(self.on_exit) 
        sys_exit(self._app.exec_())

if __name__ == '__main__':
    peerconn_gui = PeerConnGUI()
    peerconn_gui.main()