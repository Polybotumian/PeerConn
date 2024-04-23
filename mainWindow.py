from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QMenu, QFileDialog, QAction
from desktopUI import Ui_MainWindow
from customSignals import Communication, PeerInfo
from dmodels import BPI, CHD
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon
from logging import Logger
from os import path, listdir
from customDiags import ConnectionDialog
from json import load
from PyQt5.QtMultimedia import QSoundEffect
from factories import P2PFactory
from typing import Any

class MainWindow(QMainWindow):
    twistedFactory: P2PFactory
    reactor: Any

    def __init__(self, config) -> None:
        """
        config: Configuration file content from JSON.
        """
        super().__init__()
        self.config = config
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.setWindowTitle('PeerConn')
        self.setUilanguage()
        self.loadIcons()
        self.setIcons()
        self.loadSounds()
        self.setUiElemsActiveness(False)
        
        self.communication = Communication()
        self.peerInfo = PeerInfo()
        self.logger: Logger = None
        self.ui.connectionList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.connectionList.customContextMenuRequested.connect(self.showConnListContextMenu)

        self.setSignals()

    def setUilanguage(self) -> None:
        """
        Loads defined language from JSON file & sets UI component texts.
        """
        with open(path.join(self.config['locale']['foldername'], self.config['locale']['lang']['filename']), "r", encoding= 'utf-8') as file:
            self.langUi = load(file)[self.config['locale']['lang']['cur']]

        self.ui.tabWidget.setTabText(0, self.langUi['message'].title())
        self.ui.tabWidget.setTabText(1, self.langUi['file'].title())

        self.ui.sendButton_0.setText(self.langUi['send'].title())
        self.ui.pickButton.setText(self.langUi['pick'].title())
        self.ui.sendButton_1.setText(self.langUi['send'].title())

        self.ui.menuOptions.setTitle(self.langUi['options'].title())
        self.ui.actionConnect_To.setText(self.langUi['connect_to'].title())

    def setSignals(self) -> None:
        self.ui.sendButton_0.clicked.connect(self.emitSendMsgSignal)
        self.ui.sendButton_1.clicked.connect(self.emitSendFileSignal)
        self.ui.pickButton.clicked.connect(self.openFileDiag)

        self.communication.received.connect(self.messageReceived)
        self.communication.lost.connect(self.connectionLost)
        self.peerInfo.descriptive.connect(self.insItemToConnList)

        self.ui.connectionList.currentItemChanged.connect(self.peerTransition)
        self.ui.connectionList.setDragEnabled(True)

        self.ui.actionConnect_To.triggered.connect(self.showConnDiag)

    def loadIcons(self):
        iconsPath = path.join(self.config['assets']['foldername'], self.config['assets']['icons']['foldername'])
        iconDirs = listdir(iconsPath)
        self.icons = {}
        for iconDir in iconDirs:
            self.icons[path.splitext(path.basename(iconDir))[0]] = QIcon(path.abspath(iconsPath) + '/' + iconDir)

    def loadSounds(self):
        soundsPath = path.join(self.config['assets']['foldername'], self.config['assets']['sounds']['foldername'])
        soundDirs = listdir(soundsPath)
        self.sounds: dict[str, QSoundEffect] = {}
        for soundDir in soundDirs:
            key = path.splitext(path.basename(soundDir))[0]
            self.sounds[key] = QSoundEffect(self)
            self.sounds[key].setSource(QUrl.fromLocalFile(path.join(soundsPath, soundDir)))
            self.sounds[key].setVolume(1.0)

    def setIcons(self):
        self.ui.tabWidget.setTabIcon(0, self.icons['messages'])
        self.ui.tabWidget.setTabIcon(1, self.icons['document'])

        self.ui.sendButton_0.setIcon(self.icons['paper-plane'])
        self.ui.pickButton.setIcon(self.icons['search-alt'])
        self.ui.sendButton_1.setIcon(self.icons['upload'])

        self.ui.menuOptions.setIcon(self.icons['settings'])
        self.ui.actionConnect_To.setIcon(self.icons['plus'])

    def showConnDiag(self) -> None:
        dialog = ConnectionDialog()
        if dialog.exec_():
            ip, port = dialog.get_data()
            self.connectTo(ip, int(port))

    def showConnListContextMenu(self, position) -> None:
        context_menu = QMenu(self)
        disconnect_action: QAction = context_menu.addAction(self.langUi['disconnect'].title())
        remove_action: QAction = context_menu.addAction(self.langUi['remove'].title())
        row = self.ui.connectionList.currentRow()
        basicPeerInfo: BPI = self.ui.connectionList.item(row).data(Qt.ItemDataRole.UserRole + 1)
        if basicPeerInfo.flags & 1 == 0:
            disconnect_action.setEnabled(False)
            remove_action.setEnabled(True)
        else:
            disconnect_action.setEnabled(True)
            remove_action.setEnabled(False)
        peer_item = self.ui.connectionList.currentItem()
        
        if peer_item:
            peer: BPI = peer_item.data(Qt.ItemDataRole.UserRole + 1)
            action = context_menu.exec_(self.ui.connectionList.mapToGlobal(position))

            if action == disconnect_action:
                self.communication.close.emit(peer.identifier)
            elif action == remove_action:
                self.ui.chatWindow.clear()
                self.ui.connectionList.takeItem(row)               

    def connectTo(self, ip: str, port: int) -> None:
        self.reactor.connectTCP(ip, port, self.twistedFactory)

    def emitSendMsgSignal(self) -> None:
        message = self.ui.messageEdit.text()
        if message:
            peer: BPI = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
            self.communication.sendMsg.emit(peer.identifier, message)
            self.updateMsgHistory(self.ui.connectionList.currentItem(), message)
            self.ui.messageEdit.clear()
    
    def emitSendFileSignal(self) -> None:
        dirStr = self.ui.pathEdit.text()
        if path.exists(dirStr):
            peer: BPI = self.ui.connectionList.currentItem().data(Qt.ItemDataRole.UserRole + 1)
            self.communication.sendFile.emit(peer.identifier, dirStr)
            self.updateMsgHistory(self.ui.connectionList.currentItem(), "File uploading")
            self.ui.pathEdit.clear()

    def messageReceived(self, identifier: str, message: str):
        peer_item = self.ui.connectionList.findItems(identifier, Qt.MatchFlag.MatchExactly).pop()
        self.updateMsgHistory(peer_item, message)

    def updateMsgHistory(self, peer_item: QListWidgetItem, message: str) -> None:
        history: CHD = peer_item.data(Qt.ItemDataRole.UserRole + 1).history
        history.messages.append(message)
        self.updateChatWindow(peer_item)

    def connectionLost(self, identifier: str, reason: str) -> None:
        self.sounds['bubble-pop-up'].play()
        peer_item = self.ui.connectionList.findItems(identifier, Qt.MatchFlag.MatchExactly).pop()
        peer_item.setIcon(self.icons['link-slash'])
        self.updateMsgHistory(peer_item, reason)

    def peerTransition(self, currentPeer_item: QListWidgetItem, previousPeer_item: QListWidgetItem) -> None:
        self.updateChatWindow(currentPeer_item)

    def setUiElemsActiveness(self, activeness: bool) -> None:
        self.ui.chatWindow.setEnabled(activeness)
        self.ui.tabWidget.setEnabled(activeness)

    def updateChatWindow(self, peer_item: QListWidgetItem) -> None:
        if not peer_item:
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(False)
        elif peer_item and peer_item == self.ui.connectionList.currentItem():
            self.ui.chatWindow.clear()
            self.setUiElemsActiveness(True)
            self.ui.chatWindow.addItems(peer_item.data(Qt.ItemDataRole.UserRole + 1).history.messages)
    
    def insItemToConnList(self, basicPeerInfo: BPI) -> None:
        self.sounds['long-pop'].play()
        connection = QListWidgetItem()
        connection.setText(basicPeerInfo.identifier)
        connection.setData(Qt.ItemDataRole.UserRole + 1, basicPeerInfo)
        connection.setIcon(self.icons['link'])
        self.ui.connectionList.addItem(connection)
        basicPeerInfo.history.messages.append('Connection established!')

    def openFileDiag(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "Tüm Dosyalar (*);;Python Dosyaları (*.py)")
        if filePath:
            self.ui.pathEdit.setText(filePath)