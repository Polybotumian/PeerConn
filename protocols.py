from twisted.internet import protocol
from twisted.internet.interfaces import ITransport
from twisted.internet.error import ConnectionDone, ConnectionLost
from customSignals import Communication, PeerInfo
from dmodels import BPI, CHD
from uuid import uuid4
from logging import Logger


class P2PProtocol(protocol.Protocol):

    def __init__(
        self, communication: Communication, peerInfo: PeerInfo, logger: Logger
    ):
        self.identifier = str(uuid4())
        self.transport: ITransport
        self.communication = communication
        self.communication.sendMsg.connect(self.sendMessage)
        self.communication.sendFile.connect(self.sendFile)
        self.communication.close.connect(self.closeConnection)
        self.peerInfo = peerInfo
        self.logger = logger

    def connectionMade(self) -> None:
        print(self.transport.getHost(), self.transport.getPeer())
        self.logger.info(f"Connection established: {self.identifier}")
        self.authenticatePeer()

    def connectionLost(self, reason) -> None:
        if reason.check(ConnectionDone):
            reason_msg = "Connection closed cleanly."
        elif reason.check(ConnectionLost):
            reason_msg = "Connection lost unexpectedly."
        else:
            reason_msg = reason.getErrorMessage()  # Default message
        self.basicPeerInfo.flags = 0
        self.communication.lost.emit(self.identifier, reason_msg)
        self.logger.info(f"Connection lost: {self.identifier}, {reason_msg}")

    def abortConnection(self) -> None:
        self.logger.info(f"Connection Aborted: {self.identifier}")

    def closeConnection(self, identifier) -> None:
        if self.identifier == identifier:
            self.transport.loseConnection()
            self.logger.info(f"Disconnected: {self.identifier}")

    def dataReceived(self, data) -> None:
        if data.startswith(b"msg:"):
            self.handleMessage(data[4:])
        elif data.startswith(b"file:"):
            self.handleFile(data[5:])
        else:
            self.logger.error(f"Unidentified data type")

    def sendMessage(self, identifier, message: str) -> None:
        if message and self.identifier == identifier:
            message = "msg:" + message
            self.transport.write(message.encode("utf-8"))

    def sendFile(self, identifier, file_path) -> None:
        if file_path and self.identifier == identifier:
            self.transport.write(b"file:")
            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    self.transport.write(chunk)

    def handleMessage(self, message) -> None:
        self.communication.received.emit(self.identifier, message.decode("utf-8"))

    def handleFile(self, file_data) -> None:
        print(f"Dosya alındı: {len(file_data)} bytes")

    def authenticatePeer(self) -> None:
        self.basicPeerInfo = BPI(identifier=self.identifier, history=CHD(), flags=1)
        self.peerInfo.descriptive.emit(self.basicPeerInfo)
        self.logger.info(f"Authenticating: {self.identifier}")

    def handleError(self, error) -> None:
        self.logger.error(f"An error occured: {self.identifier}, {error}")
