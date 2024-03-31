from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QMenu
from desktopUI import Ui_MainWindow
from signals import Communication, PeerInfo
from dmodels import BPI, CHD
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('PeerConn')

        self.peers = []
        self.communication = Communication()
        self.peerInfo = PeerInfo()
        self.twistedFactory = None
        self.reactor = None
        self.ui.connectionList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.connectionList.customContextMenuRequested.connect(self.show_peer_context_menu)

        self.ui.sendButton.clicked.connect(self.emit_send_signal)
        self.communication.received.connect(self.updateMessageHistory)
        self.peerInfo.descriptive.connect(self.updateConnectionList)
        self.ui.connectionList.currentItemChanged.connect(self.peerTransition)
        self.ui.connectionList.setDragEnabled(True)

    def show_peer_context_menu(self, position):
        # Bağlam menüsünü oluştur
        context_menu = QMenu(self)
        disconnect_action = context_menu.addAction('Disconnect')
        identifier = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
        row = self.ui.connectionList.currentRow()
        action = context_menu.exec_(self.ui.connectionList.mapToGlobal(position))

        # Menüden seçilen eyleme göre işlem yap
        if action == disconnect_action:
            for peer in self.peers:
                if peer.identifier == identifier:
                    self.peers.remove(peer)
                    self.ui.chatWindow.clear()
                    break
            self.communication.close.emit(identifier)
            self.ui.connectionList.takeItem(row)

    def emit_send_signal(self):
        message = self.ui.messageEdit.text()
        peerId = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
        if message and peerId:
            self.communication.send.emit(peerId, message)
            self.ui.messageEdit.clear()
            self.updateMessageHistory(peerId, message)

    def updateMessageHistory(self, identifier, message):
        for peer in self.peers:
            if peer.identifier == identifier:
                peer.history.messages.append(message)
                self.updateChatWindow(peer)
                break

    def peerTransition(self, currentPeer, previousPeer):
        for peer in self.peers:
            if peer.identifier == currentPeer.data(Qt.ItemDataRole.UserRole + 1):
                self.updateChatWindow(peer)
                break

    def updateChatWindow(self, peer):
        currentPeer = self.ui.connectionList.currentItem()
        if currentPeer and peer.identifier == currentPeer.data(Qt.ItemDataRole.UserRole + 1):
            self.ui.chatWindow.clear()
            self.ui.chatWindow.addItems(peer.history.messages)
    
    def updateConnectionList(self, peerInfo):
        newPeer = BPI(
            identifier= peerInfo.identifier,
            history= CHD(),
            flags= peerInfo.flags
        )
        self.peers.append(newPeer)

        connection = QListWidgetItem()
        connection.setText(newPeer.identifier)
        connection.setData(Qt.ItemDataRole.UserRole + 1, newPeer.identifier)
        self.ui.connectionList.addItem(connection)
