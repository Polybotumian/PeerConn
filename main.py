import sys
from PyQt5.QtWidgets import QApplication
import qt5reactor
from mWindow import MainWindow
from factories import P2PFactory

def main():
    app = QApplication(sys.argv)
    qt5reactor.install()

    window = MainWindow()
    window.show()

    from twisted.internet import reactor
    window.reactor = reactor
    window.twistedFactory = P2PFactory(window.communication, window.peerInfo)
    reactor.listenTCP(12345, window.twistedFactory)
    reactor.runReturn(installSignalHandlers= False)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()