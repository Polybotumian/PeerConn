from twisted.internet import protocol
from protocols import P2PProtocol

class P2PFactory(protocol.ClientFactory):
    def __init__(self, communication, peerInfo, logger):
        self.communication = communication
        self.peerInfo = peerInfo
        self.logger = logger

    def buildProtocol(self, addr):
        return P2PProtocol(self.communication, self.peerInfo, self.logger)