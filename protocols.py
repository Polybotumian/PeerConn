from twisted.internet.protocol import Protocol as TwistedInternetProtocol
from twisted.internet.interfaces import ITransport
from twisted.internet.error import ConnectionDone, ConnectionLost
from uuid import uuid4
from logging import Logger
from enum import Enum
from os import path, makedirs
from json import dumps, loads
from hashlib import md5

from signals import Communication
from data_models import BPI, CHD


class P2P(TwistedInternetProtocol):
    """
    Protocol for peer to peer connection.
    """

    def __init__(self, communication: Communication, logger: Logger):
        self.identifier = str(uuid4())
        self.transport: ITransport
        self.logger = logger
        self.communication = communication

        self.communication.msg_send.connect(self.sendMessage)
        self.communication.file_send.connect(self.sendFile)
        self.communication.conn_close.connect(self.closeConnection)

        self.isReceivingFile = False
        self.receivedFileInfo = None
        self.receivedFileSize = 0
        self.file = None

    class Delimiters(bytes, Enum):
        MESSAGE_BEGIN = b"---MESSAGE_BYTE---"
        FILE_BEGIN = b"---FILE_BYTE---"

    def logAndHandleException(func):
        def wrapper(self, *args, **kwargs):
            try:
                self.logger.info(f"{self.identifier} -> {func.__name__})")
                result = func(self, *args, **kwargs)
                self.logger.info(f"{func.__name__} -> {result}")
                return result
            except Exception as e:
                self.logger.error(
                    f"{self.identifier} -> {func.__name__} -> {e}")
                return None
        return wrapper

    @logAndHandleException
    def connectionMade(self) -> None:
        self.authenticatePeer()

    @logAndHandleException
    def connectionLost(self, reason) -> str:
        if reason.check(ConnectionDone):
            message = "Connection closed cleanly."
        elif reason.check(ConnectionLost):
            message = "Connection lost unexpectedly."
        else:
            message = reason.getErrorMessage()
        self.basicPeerInfo.flags = 0
        self.communication.conn_lost.emit(self.identifier, message)
        return message

    @logAndHandleException
    def dataReceived(self, receivedBytes: bytes) -> None:
        if receivedBytes.startswith(self.Delimiters.MESSAGE_BEGIN):
            self.handleMessage(
                receivedBytes[len(self.Delimiters.MESSAGE_BEGIN):])
        elif receivedBytes.startswith(self.Delimiters.FILE_BEGIN):
            self.isReceivingFile = True
            self.receivedFileInfo = None
            self.receivedFileSize = 0
            self.file = None
            self.handleFile(receivedBytes[len(self.Delimiters.FILE_BEGIN):])
        elif self.isReceivingFile:
            self.handleFile(receivedBytes)
        else:
            raise Exception("Unidentified data bytes.")

    @logAndHandleException
    def closeConnection(self, identifier: str) -> None:
        if self.identifier == identifier:
            self.transport.loseConnection()
            self.logger.info(f"Disconnected: {self.identifier}")

    @logAndHandleException
    def sendMessage(self, identifier: str, message: str) -> None:
        if message and self.identifier == identifier:
            messageBytes = self.Delimiters.MESSAGE_BEGIN + \
                message.encode("utf-8")
            self.transport.write(messageBytes)

    @logAndHandleException
    def calculateChecksum(self, filePath):
        md5_hash = md5()
        with open(filePath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        return md5_hash.hexdigest()

    @logAndHandleException
    def sendFile(self, identifier: str, filePath: str) -> None:
        if filePath and self.identifier == identifier:
            self.transport.write(self.Delimiters.FILE_BEGIN)
            file_size = path.getsize(filePath)
            checksum = self.calculateChecksum(filePath)
            file_obj = {
                "filename": path.basename(filePath),
                "filesize": file_size,
                "checksum": checksum,
            }

            fileInfoBytes = dumps(file_obj).encode("utf-8")
            self.transport.write(fileInfoBytes)

            self.transport.write(self.Delimiters.FILE_BEGIN)
            total_sent = 0

            with open(filePath, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    self.transport.write(chunk)
                    total_sent += len(chunk)
                    self.communication.file_percentage.emit(
                        self.identifier, int((total_sent / file_size) * 100))

            self.communication.notification.emit(
                self.identifier, f'Uploaded: {file_obj["filename"]}, {file_obj["filesize"]}')

    @logAndHandleException
    def handleMessage(self, message: bytes) -> None:
        self.communication.received_msg.emit(
            self.identifier, message.decode("utf-8"))

    @logAndHandleException
    def handleFile(self, fileData: bytes) -> None:
        if self.receivedFileInfo is None:
            delimiterIndex = fileData.find(self.Delimiters.FILE_BEGIN)
            if delimiterIndex == -1:
                self.receivedFileInfo = fileData
            else:
                self.receivedFileInfo = fileData[:delimiterIndex]
                self.startWritingFile(
                    fileData[delimiterIndex + len(self.Delimiters.FILE_BEGIN):])
            self.communication.notification.emit(
                self.identifier, f'Receiving: {loads(self.receivedFileInfo)["filename"]}, {loads(self.receivedFileInfo)["filesize"]}')
        else:
            self.startWritingFile(fileData)

    @logAndHandleException
    def startWritingFile(self, fileData: bytes) -> None:
        if self.receivedFileInfo is not None and self.file is None:
            try:
                fileInfo = loads(self.receivedFileInfo)
                fileName = fileInfo["filename"]
                filePath = path.join("received_files", fileName)
                makedirs(path.dirname(filePath), exist_ok=True)
                self.file = open(filePath, "wb")
            except Exception as e:
                self.logger.error(f"Error starting to write file: {e}")
                self.receivedFileInfo = None
                self.isReceivingFile = False
                return

        if self.file:
            self.file.write(fileData)
            self.receivedFileSize += len(fileData)
            self.communication.file_percentage.emit(self.identifier, int(
                (self.receivedFileSize / loads(self.receivedFileInfo)["filesize"]) * 100))
            self.checkAndCloseFile()

    @logAndHandleException
    def checkAndCloseFile(self) -> None:
        try:
            file_info = loads(self.receivedFileInfo)
            if self.receivedFileSize >= file_info["filesize"]:
                self.file.close()
                self.communication.notification.emit(
                    self.identifier, "File has been received!")
                if loads(self.receivedFileInfo)["checksum"] == self.calculateChecksum(path.join('received_files', loads(self.receivedFileInfo)["filename"])):
                    self.communication.notification.emit(
                        self.identifier, "Checksum is ok.")
                else:
                    self.communication.notification.emit(
                        self.identifier, "Check sum is incorrect!")
                self.isReceivingFile = False
                self.receivedFileInfo = None
                self.file = None
                self.receivedFileSize = 0
                self.communication.file_percentage.emit(self.identifier, 100)
        except Exception as e:
            self.logger.error(f"Error in checkAndCloseFile: {e}")

    @logAndHandleException
    def authenticatePeer(self) -> None:
        self.basicPeerInfo = BPI(
            identifier=self.identifier, history=CHD(), flags=1)
        self.communication.peer_info.emit(self.basicPeerInfo)
