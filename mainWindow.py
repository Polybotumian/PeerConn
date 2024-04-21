from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QMenu, QFileDialog
from desktopUI import Ui_MainWindow
from customSignals import Communication, PeerInfo
from dmodels import BPI, CHD
from PyQt5.QtCore import Qt
from logging import Logger
from os import path
from customDiags import ConnectionDialog

class MainWindow(QMainWindow):
    def __init__(self, langUi):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.langUi = langUi
        self.setWindowTitle('PeerConn')
        self.setUilanguage()
        self.setUiElemsActiveness(False)

        self.communication = Communication()
        self.peerInfo = PeerInfo()
        self.logger: Logger = None
        self.ui.connectionList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.connectionList.customContextMenuRequested.connect(self.showConnListContextMenu)

        self.setSignals()

    def setUilanguage(self):
        self.ui.tabWidget.setTabText(0, self.langUi['message'].title())
        self.ui.tabWidget.setTabText(1, self.langUi['file'].title())

        self.ui.sendButton_0.setText(self.langUi['send'].title())
        self.ui.pickButton.setText(self.langUi['pick'].title())
        self.ui.sendButton_1.setText(self.langUi['send'].title())

        self.ui.menuOptions.setTitle(self.langUi['options'].title())
        self.ui.actionConnect_To.setText(self.langUi['connect_to'].title())

    def setSignals(self):
        self.ui.sendButton_0.clicked.connect(self.emitSendMsgSignal)
        self.ui.sendButton_1.clicked.connect(self.emitSendFileSignal)
        self.ui.pickButton.clicked.connect(self.openFileDiag)

        self.communication.received.connect(self.updateMsgHistory)
        self.communication.lost.connect(self.updateMsgHistory)
        self.peerInfo.descriptive.connect(self.updateConnList)

        self.ui.connectionList.currentItemChanged.connect(self.peerTransition)
        self.ui.connectionList.setDragEnabled(True)

        self.ui.actionConnect_To.triggered.connect(self.showConnDiag)

    def showConnDiag(self):
        dialog = ConnectionDialog()
        if dialog.exec_():
            ip, port = dialog.get_data()
            self.connectTo(ip, int(port))

    def showConnListContextMenu(self, position):
        context_menu = QMenu(self)
        disconnect_action = context_menu.addAction(self.langUi['disconnect'].title())
        remove_action = context_menu.addAction(self.langUi['remove'].title())
        row = self.ui.connectionList.currentRow()
        basicPeerInfo: BPI = self.ui.connectionList.item(row).data(Qt.ItemDataRole.UserRole + 1)
        if basicPeerInfo.flags & 1 == 0:
            disconnect_action.setEnabled(False)
            remove_action.setEnabled(True)
        else:
            disconnect_action.setEnabled(True)
            remove_action.setEnabled(False)
        peer_item:BPI = self.ui.connectionList.currentItem()
        
        if peer_item:
            peer: BPI = peer_item.data(Qt.ItemDataRole.UserRole + 1)
            action = context_menu.exec_(self.ui.connectionList.mapToGlobal(position))

            if action == disconnect_action:
                self.communication.close.emit(peer.identifier)
            elif action == remove_action:
                self.ui.chatWindow.clear()
                self.ui.connectionList.takeItem(row)               

    def connectTo(self, ip, port):
        self.reactor.connectTCP(ip, port, self.twistedFactory)

    def emitSendMsgSignal(self):
        message = self.ui.messageEdit.text()
        if message:
            peer: BPI = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
            self.communication.sendMsg.emit(peer.identifier, message)
            self.updateMsgHistory(self.ui.connectionList.currentItem(), message)
            self.ui.messageEdit.clear()
    
    def emitSendFileSignal(self):
        dirStr = self.ui.pathEdit.text()
        if path.exists(dirStr):
            peer: BPI = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
            self.communication.sendFile.emit(peer.identifier, dirStr)
            self.updateMsgHistory(self.ui.connectionList.currentItem(), "File uploading")
            self.ui.pathEdit.clear()

    def updateMsgHistory(self, peer_item: QListWidgetItem, message):
        if type(peer_item) != QListWidgetItem:
            peer_item = self.ui.connectionList.findItems(peer_item, Qt.MatchFlag.MatchExactly).pop()
        peer_item.data(Qt.ItemDataRole.UserRole + 1).history.messages.append(message)
        self.updateChatWindow(peer_item)

    def peerTransition(self, currentPeer_item: QListWidgetItem, previousPeer_item: QListWidgetItem):
        self.updateChatWindow(currentPeer_item)

    def setUiElemsActiveness(self, activeness):
        self.ui.chatWindow.setEnabled(activeness)
        self.ui.tabWidget.setEnabled(activeness)

    def updateChatWindow(self, peer_item: QListWidgetItem):
        if not peer_item:
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(False)
        elif peer_item and peer_item == self.ui.connectionList.currentItem():
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(True)
            self.ui.chatWindow.addItems(peer_item.data(Qt.ItemDataRole.UserRole + 1).history.messages)
    
    def updateConnList(self, basicPeerInfo):
        connection = QListWidgetItem()
        connection.setText(basicPeerInfo.identifier)
        connection.setData(Qt.ItemDataRole.UserRole + 1, basicPeerInfo)
        self.ui.connectionList.addItem(connection)

    def openFileDiag(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "Tüm Dosyalar (*);;Python Dosyaları (*.py)")
        if filePath:
            self.ui.pathEdit.setText(filePath)