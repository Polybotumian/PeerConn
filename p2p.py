from twisted.internet.protocol import Protocol as TwistedInternetProtocol
from twisted.internet.interfaces import ITransport
from twisted.internet.error import ConnectionDone, ConnectionLost
from signals import Communication, PeerInfo
from dmodels import BPI, CHD
from uuid import uuid4
from logging import Logger
from enum import Enum
from os import path
from json import dumps, loads


class Protocol(TwistedInternetProtocol):
    """
    Protocol for peer to peer connection.
    """

    def __init__(
        self, communication: Communication, peerInfo: PeerInfo, logger: Logger
    ):
        self.identifier = str(uuid4())
        self.transport: ITransport
        self.peerInfo = peerInfo
        self.logger = logger
        self.communication = communication

        self.communication.sendMsg.connect(self.sendMessage)
        self.communication.sendFile.connect(self.sendFile)
        self.communication.close.connect(self.closeConnection)

        # File transfer state
        self.isReceivingFile = False
        self.receivedFileInfo = None
        self.file = None  # File object for writing incoming data
        self.receivedFileSize = 0  # Track the size of received data

    # ENUMS
    class Delimiters(bytes, Enum):
        MESSAGE_BEGIN = b"---MESSAGE_BYTE---"
        FILE_BEGIN = b"---FILE_BYTE---"

    # DECORATORS
    def logAndHandleException(func):
        def wrapper(self, *args, **kwargs):
            try:
                self.logger.info(f"{self.identifier} -> {func.__name__})")
                result = func(self, *args, **kwargs)
                self.logger.info(f"{func.__name__} -> {result}")
                return result
            except Exception as e:
                self.logger.error(f"{self.identifier} -> {func.__name__} -> {e}")
                return None

        return wrapper

    # TWISTED IMPLEMENTER FUNCTION
    @logAndHandleException
    def connectionMade(self) -> None:
        self.authenticatePeer()

    # TWISTED IMPLEMENTER FUNCTION
    @logAndHandleException
    def connectionLost(self, reason) -> str:
        if reason.check(ConnectionDone):
            message = "Connection closed cleanly."
        elif reason.check(ConnectionLost):
            message = "Connection lost unexpectedly."
        else:
            message = reason.getErrorMessage()  # Default message
        self.basicPeerInfo.flags = 0
        self.communication.lost.emit(self.identifier, message)
        return message

    # TWISTED IMPLEMENTER FUNCTION
    @logAndHandleException
    def dataReceived(self, receivedBytes: bytes) -> None:
        if receivedBytes.startswith(self.Delimiters.MESSAGE_BEGIN):
            self.handleMessage(receivedBytes[len(self.Delimiters.MESSAGE_BEGIN) :])
        elif receivedBytes.startswith(self.Delimiters.FILE_BEGIN):
            self.isReceivingFile = True
            self.receivedFileInfo = None
            self.receivedFileSize = 0
            self.file = None
            self.handleFile(receivedBytes[len(self.Delimiters.FILE_BEGIN) :])
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
            messageBytes = self.Delimiters.MESSAGE_BEGIN + message.encode("utf-8")
            self.transport.write(messageBytes)

    @logAndHandleException
    def sendFile(self, identifier: str, filePath: str) -> None:
        if filePath and self.identifier == identifier:
            self.transport.write(self.Delimiters.FILE_BEGIN)
            fileInfoBytes = dumps(
                {
                    "filename": path.basename(filePath),
                    "filesize": path.getsize(filePath),
                    "filetype": "binary",
                }
            ).encode("utf-8")
            self.transport.write(fileInfoBytes)

            # Send a delimiter to separate file info and file data
            self.transport.write(self.Delimiters.FILE_BEGIN)

            with open(filePath, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    self.transport.write(chunk)

    @logAndHandleException
    def handleMessage(self, message: bytes) -> None:
        self.communication.received.emit(self.identifier, message.decode("utf-8"))

    @logAndHandleException
    def handleFile(self, fileData: bytes) -> None:
        if self.receivedFileInfo is None:
            delimiterIndex = fileData.find(self.Delimiters.FILE_BEGIN)
            if delimiterIndex == -1:
                self.receivedFileInfo = fileData
            else:
                self.receivedFileInfo = fileData[:delimiterIndex]
                self.startWritingFile(
                    fileData[delimiterIndex + len(self.Delimiters.FILE_BEGIN) :]
                )
        else:
            self.startWritingFile(fileData)

    def startWritingFile(self, fileData: bytes) -> None:
        if self.receivedFileInfo is not None and self.file is None:
            fileInfo = loads(self.receivedFileInfo)
            fileName = fileInfo["filename"]
            filePath = path.join("received_files", fileName)
            self.file = open(filePath, "wb")

        if self.file:
            self.file.write(fileData)
            self.receivedFileSize += len(fileData)
            self.checkAndCloseFile()

    def checkAndCloseFile(self):
        file_info = loads(self.receivedFileInfo)
        if self.receivedFileSize >= file_info["filesize"]:
            self.file.close()
            self.isReceivingFile = False
            self.receivedFileInfo = None
            self.file = None
            self.receivedFileSize = 0
            print(f"File {file_info['filename']} received successfully")

    @logAndHandleException
    def authenticatePeer(self) -> None:
        self.basicPeerInfo = BPI(identifier=self.identifier, history=CHD(), flags=1)
        self.peerInfo.descriptive.emit(self.basicPeerInfo)
