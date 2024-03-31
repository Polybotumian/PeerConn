from twisted.internet import protocol
from protocols import P2PProtocol

class P2PFactory(protocol.Factory):
    def __init__(self, communication, peerInfo, primary = False):
        self.communication = communication
        self.peerInfo = peerInfo

    def buildProtocol(self, addr):
        return P2PProtocol(self.communication, self.peerInfo)