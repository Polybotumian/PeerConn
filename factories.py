from twisted.internet import protocol
from p2p import Protocol


class P2PFactory(protocol.ClientFactory):
    def __init__(self, communication, peerInfo, logger):
        self.communication = communication
        self.peerInfo = peerInfo
        self.logger = logger

    def buildProtocol(self, addr):
        return Protocol(self.communication, self.peerInfo, self.logger)
