from twisted.internet import protocol
import protocols


class P2P(protocol.ClientFactory):
    def __init__(self, communication, logger):
        self.communication = communication
        self.logger = logger

    def buildProtocol(self, addr):
        return protocols.P2P(self.communication, self.logger)
