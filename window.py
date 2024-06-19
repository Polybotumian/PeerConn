from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QMenu, QFileDialog, QAction, QMessageBox
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import Qt, QUrl, QPoint
from PyQt5.QtGui import QIcon, QColor
from logging import Logger
from os import path, listdir
from puic import Ui_MainWindow
from typing import Any, Dict
from OpenSSL.crypto import X509, PKey
from twisted.internet.ssl import CertificateOptions
from ipaddress import ip_address
from json import load
from datetime import datetime

import factories
from signals import Communication
from data_models import BPI, CHD, Message
from dialoags import ConnectionDialog
from key_events import Mekef


class Window(QMainWindow):
    twistedFactory: factories.P2P
    reactor: Any

    def __init__(self, config: Dict) -> None:
        """
        config: Configuration file content from JSON.
        """
        super().__init__()
        self.config = config
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("PeerConn")
        self.setLocale()
        self.loadIcons()
        self.setIcons()
        self.loadSounds()
        self.setUiElemsActiveness(False)

        self.communication = Communication()
        self.logger: Logger = None
        self.ca_key: PKey = None
        self.ca_cert: X509 = None
        self.ui.connectionList.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.connectionList.customContextMenuRequested.connect(
            self.showConnListContextMenu
        )

        self.setSignals()

    def setLocale(self) -> None:
        """
        Loads languages from JSON file & sets the selected language that is defined in config.json.
        """
        with open(
            path.join(self.config["locale"]["path"]),
            "r",
            encoding="utf-8",
        ) as file:
            self.langUi = load(file)[self.config["locale"]["selected"]]

        self.ui.tabWidget.setTabText(0, self.langUi["message"].title())
        self.ui.tabWidget.setTabText(1, self.langUi["file"].title())
        self.ui.tabWidget.setTabText(2, self.langUi["info"].title())

        self.ui.sendButton_0.setText(self.langUi["send"].title())
        self.ui.pickButton.setText(self.langUi["pick"].title())
        self.ui.sendButton_1.setText(self.langUi["send"].title())

        self.ui.menuOptions.setTitle(self.langUi["options"].title())
        self.ui.actionConnect_To.setText(self.langUi["connect_to"].title())

        self.ui.label_ip.setText("IP")
        self.ui.label_ip_val.setText("0.0.0.0")
        self.ui.label_port.setText("Port")
        self.ui.label_port_val.setText(str(self.config["port"]))
        self.ui.label_security.setText(self.langUi["security"].title())
        self.ui.label_security_val.setText(self.config["security"].upper())

    def setSignals(self) -> None:
        self.ui.sendButton_0.clicked.connect(self.emitSendMsgSignal)
        self.ui.sendButton_1.clicked.connect(self.emitSendFileSignal)
        self.ui.pickButton.clicked.connect(self.openFileDiag)

        self.communication.received_msg.connect(self.messageReceived)
        self.communication.conn_lost.connect(self.connectionLost)
        self.communication.peer_info.connect(self.insertItemToConnList)
        self.communication.file_percentage.connect(self.progressBar)
        self.communication.notification.connect(self.nofication)

        self.ui.connectionList.currentItemChanged.connect(self.peerTransition)
        self.ui.connectionList.setDragEnabled(True)

        self.ui.actionConnect_To.triggered.connect(self.showConnDiag)

        mekef = Mekef(self.ui.messageEdit)
        mekef.send_message_callback = self.emitSendMsgSignal
        self.ui.messageEdit.installEventFilter(mekef)

    def loadIcons(self):
        iconsPath = self.config["paths"]["icons"]
        iconDirs = listdir(iconsPath)
        self.icons = {}
        for iconDir in iconDirs:
            self.icons[path.splitext(path.basename(iconDir))[0]] = QIcon(
                path.abspath(iconsPath) + "/" + iconDir
            )

    def loadSounds(self):
        soundsPath = path.join(self.config["paths"]["sounds"])
        soundDirs = listdir(soundsPath)
        self.sounds: dict[str, QSoundEffect] = {}
        for soundDir in soundDirs:
            key = path.splitext(path.basename(soundDir))[0]
            self.sounds[key] = QSoundEffect(self)
            self.sounds[key].setSource(
                QUrl.fromLocalFile(path.join(soundsPath, soundDir))
            )
            self.sounds[key].setVolume(1.0)

    def setIcons(self):
        self.ui.tabWidget.setTabIcon(0, self.icons["messages"])
        self.ui.tabWidget.setTabIcon(1, self.icons["document"])
        self.ui.tabWidget.setTabIcon(2, self.icons["info"])

        self.ui.sendButton_0.setIcon(self.icons["paper-plane"])
        self.ui.pickButton.setIcon(self.icons["search-alt"])
        self.ui.sendButton_1.setIcon(self.icons["upload"])

        self.ui.menuOptions.setIcon(self.icons["settings"])
        self.ui.actionConnect_To.setIcon(self.icons["plus"])

    def show_warning(self, icon: QMessageBox.Icon, title: str, message: str) -> None:
        msg_box = QMessageBox()
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec_()

    def showConnDiag(self) -> None:
        while True:
            dialog = ConnectionDialog()
            if dialog.exec_():
                ip, port = dialog.get_data()
                try:
                    ip_address(ip)
                    port_int = int(port)
                    if not (0 <= port_int <= 65535):
                        raise ValueError("Port must be between 0 and 65535")
                    self.connectTo(ip, port_int)
                    break
                except ValueError as ve:
                    self.show_warning(QMessageBox.Icon.Warning,
                                      "Invalid Input", str(ve))
                    self.logger.error(ve)
            else:
                break

    def showConnListContextMenu(self, position: QPoint) -> None:
        context_menu = QMenu(self)
        disconnect_action: QAction = context_menu.addAction(
            self.langUi["disconnect"].title()
        )
        remove_action: QAction = context_menu.addAction(
            self.langUi["remove"].title())
        row = self.ui.connectionList.currentRow()
        if self.ui.connectionList.item(row) != None:
            basicPeerInfo: BPI = self.ui.connectionList.item(row).data(
                Qt.ItemDataRole.UserRole + 1
            )
            if basicPeerInfo.flags & 1 == 0:
                disconnect_action.setEnabled(False)
                remove_action.setEnabled(True)
            else:
                disconnect_action.setEnabled(True)
                remove_action.setEnabled(False)
            peer_item = self.ui.connectionList.currentItem()

            if peer_item:
                peer: BPI = peer_item.data(Qt.ItemDataRole.UserRole + 1)
                action = context_menu.exec_(
                    self.ui.connectionList.mapToGlobal(position))

                if action == disconnect_action:
                    self.communication.conn_close.emit(peer.identifier)
                elif action == remove_action:
                    self.ui.chatWindow.clear()
                    self.ui.connectionList.takeItem(row)

    def connectTo(self, ip: str, port: int) -> None:
        self.reactor.connectSSL(
            ip,
            port,
            self.twistedFactory,
            CertificateOptions(
                verify=False
                # trustRoot=trustRootFromCertificates([Certificate(self.ca_cert)]),
            ),
        )

    def emitSendMsgSignal(self) -> None:
        message = self.ui.messageEdit.toPlainText()
        if message:
            peer: BPI = self.ui.connectionList.currentItem().data(
                Qt.ItemDataRole.UserRole + 1
            )
            self.communication.msg_send.emit(peer.identifier, message)
            self.updateMsgHistory(
                self.ui.connectionList.currentItem(), Message(message, datetime.now(), 1))
            self.ui.messageEdit.clear()

    def emitSendFileSignal(self) -> None:
        dirStr = self.ui.pathEdit.text()
        if path.exists(dirStr):
            peer: BPI = self.ui.connectionList.currentItem().data(
                Qt.ItemDataRole.UserRole + 1
            )
            self.communication.file_send.emit(peer.identifier, dirStr)
            self.ui.pathEdit.clear()

    def messageReceived(self, identifier: str, message: str):
        peer_item = self.ui.connectionList.findItems(
            identifier, Qt.MatchFlag.MatchExactly
        ).pop()
        self.updateMsgHistory(peer_item, Message(message, datetime.now(), 2))

    def nofication(self, identifier: str, message: str):
        peer_item = self.ui.connectionList.findItems(
            identifier, Qt.MatchFlag.MatchExactly
        ).pop()
        self.updateMsgHistory(peer_item, Message(message, datetime.now(), 0))

    def updateMsgHistory(self, peer_item: QListWidgetItem, message: Message) -> None:
        history: CHD = peer_item.data(Qt.ItemDataRole.UserRole + 1).history
        history.messages.append(message)
        self.updateChatWindow(peer_item)

    def connectionLost(self, identifier: str, reason: str) -> None:
        self.sounds["bubble-pop-up"].play()
        peer_item = self.ui.connectionList.findItems(
            identifier, Qt.MatchFlag.MatchExactly
        ).pop()
        peer_item.setIcon(self.icons["link-slash"])
        self.updateMsgHistory(peer_item, Message(reason, datetime.now(), 0))

    def peerTransition(
        self, current_peer_item: QListWidgetItem, previous_peer_item: QListWidgetItem
    ) -> None:
        self.updateChatWindow(current_peer_item)

    def setUiElemsActiveness(self, activeness: bool) -> None:
        self.ui.tabWidget.setTabEnabled(0, activeness)
        self.ui.tabWidget.setTabEnabled(1, activeness)
        self.ui.tabWidget.setTabEnabled(3, True)
        if self.ui.tabWidget.currentIndex() != 0 and not self.ui.tabWidget.isTabEnabled(0):
            self.ui.tabWidget.setCurrentIndex(0)

        self.ui.progressBar.setVisible(False)

    def updateChatWindow(self, peer_item: QListWidgetItem) -> None:
        if not peer_item:
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(False)
        # elif peer_item and peer_item.data(Qt.ItemDataRole.UserRole + 1).flags & 1 == 0:
        #     self.setUiElemsActiveness(False)
        elif peer_item and peer_item == self.ui.connectionList.currentItem():
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(True)
            for message in peer_item.data(Qt.ItemDataRole.UserRole + 1).history.messages:
                message: Message
                list_item = QListWidgetItem(None, self.ui.chatWindow)
                message_text = f"{message.dtime.strftime('%d/%m/%Y, %H:%M:%S')}\n{message.text}"
                if message.who == 0:
                    # list_item.setBackground(QColor(200, 200, 200, 255))
                    list_item.setForeground(QColor(50, 168, 82, 255))
                    list_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    list_item.setText(message_text)
                elif message.who == 1:
                    list_item.setForeground(QColor(50, 56, 168, 255))
                    list_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                    list_item.setText(message_text)
                elif message.who == 2:
                    list_item.setForeground(QColor(107, 50, 168, 255))
                    list_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
                    list_item.setText(message_text)
                self.ui.chatWindow.addItem(list_item)

    def insertItemToConnList(self, basic_peer_info: BPI) -> None:
        self.sounds["long-pop"].play()
        connection = QListWidgetItem()
        connection.setText(basic_peer_info.identifier)
        connection.setData(Qt.ItemDataRole.UserRole + 1, basic_peer_info)
        connection.setIcon(self.icons["link"])
        self.ui.connectionList.addItem(connection)
        basic_peer_info.history.messages.append(
            Message(text="Connection established!", dtime=datetime.now(), who=0))

    def progressBar(self, peer_id, percentage: int) -> None:
        if self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1).identifier == peer_id:
            self.ui.progressBar.setVisible(True)
            self.ui.progressBar.setValue(percentage)
            if self.ui.progressBar.value() >= 100:
                self.ui.progressBar.setVisible(False)

    def openFileDiag(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self,
            f"{self.langUi['open_file'].title()}",
            "",
            f"{self.langUi['all'].title()} {self.langUi['files'].title()} (*);",
        )
        if filePath:
            self.ui.pathEdit.setText(filePath)
