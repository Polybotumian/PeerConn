from twisted.internet import protocol
from twisted.internet.interfaces import ITransport
from customSignals import Communication, PeerInfo
from dtos import PDTO
from uuid import uuid4
from logging import Logger
from os import urandom
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from twisted.internet.error import ConnectionDone, ConnectionLost

class P2PProtocol(protocol.Protocol):
    transport: ITransport

    def __init__(self, communication, peerInfo, logger):
        self.identifier = str(uuid4())
        self.communication: Communication = communication
        self.communication.sendMsg.connect(self.sendMessage)
        self.communication.sendFile.connect(self.sendFile)
        self.communication.close.connect(self.closeConnection)
        self.peerInfo: PeerInfo = peerInfo
        self.logger: Logger = logger
        self.key = urandom(32)  # AES için 256-bit anahtar
        self.iv = urandom(16)   # AES için 128-bit IV
        self.cipher = Cipher(algorithms.AES(self.key), modes.CFB(self.iv), backend=default_backend())

    def connectionMade(self):
        self.logger.info(f'Connection established: {self.identifier}')
        self.active = True
        self.authenticatePeer()

    def connectionLost(self, reason):
        if reason.check(ConnectionDone):
            reason_msg = "Connection closed cleanly."
        elif reason.check(ConnectionLost):
            reason_msg = "Connection lost unexpectedly."
        else:
            reason_msg = reason.getErrorMessage()  # Default message
        self.active = False
        self.communication.lost.emit(self.identifier, reason_msg)
        self.logger.info(f'Connection lost: {self.identifier}, {reason_msg}')

    def abortConnection(self):
        self.logger.info(f'Connection Aborted: {self.identifier}')
    
    def closeConnection(self, identifier):
        if self.identifier == identifier:
            self.transport.loseConnection()
            self.logger.info(f'Disconnected: {self.identifier}')

    def dataReceived(self, data):
        if data.startswith(b"msg:"):
            self.handleMessage(data[4:])
        elif data.startswith(b"file:"):
            self.handleFile(data[5:])
        else:
            self.logger.error(f'Unidentified data type')

    def sendMessage(self, identifier, message: str):
        if message and self.identifier == identifier:
            # encoded_message = message.encode('utf-8')
            # self.transport.write(self.encryptData(encoded_message))
            message = 'msg:' + message
            self.transport.write(message.encode('utf-8'))

    def sendFile(self, identifier, file_path):
        if file_path and self.identifier == identifier:
            self.transport.write(b'file:')
            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    encrypted_chunk = self.encryptData(chunk)
                    self.transport.write(encrypted_chunk)

    def handleMessage(self, message):
        # decrypted_message = self.decryptData(message)
        # self.communication.received.emit(self.identifier, decrypted_message.decode('utf-8'))
        self.communication.received.emit(self.identifier, message.decode('utf-8'))

    def handleFile(self, file_data):
        print(f"Dosya alındı: {len(file_data)} bytes")

    def authenticatePeer(self):
        basicPeerInfo = PDTO()
        basicPeerInfo.identifier = self.identifier
        basicPeerInfo.flags = 1
        self.peerInfo.descriptive.emit(basicPeerInfo)
        self.logger.info(f'Authenticating: {self.identifier}')

    def handleError(self, error):
        self.logger.error(f'An error occured: {self.identifier}, {error}')

    def encryptData(self, data):
        encryptor = self.cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        return encrypted_data

    def decryptData(self, data):
        decryptor = self.cipher.decryptor()
        decrypted_data = decryptor.update(data) + decryptor.finalize()
        return decrypted_data