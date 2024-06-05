from sys import argv, exit
from os import path, listdir
from PyQt5.QtWidgets import QApplication
from mainWindow import MainWindow
from factories import P2PFactory
import qt5reactor
from json import load
import logging
from tlsCert import genCrtAndKey, generateCa


def main():
    configFileName = "config.json"
    for dir in listdir(path.curdir):
        if dir.__contains__(configFileName):
            configDir = dir
            del configFileName
            break

    if path.exists(configDir):
        with open(configDir, "r") as file:
            config = load(file)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(config["logger"]["format"])

        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.DEBUG)
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)

        fileHandler = logging.FileHandler(
            config["logger"]["filename"], config["logger"]["mode"]
        )
        fileHandler.setLevel(logging.INFO)
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)

        app = QApplication(argv)
        qt5reactor.install()

        window = MainWindow(config)
        window.logger = logger
        window.logger.info("Initialized")
        window.show()

        from twisted.internet import reactor

        window.reactor = reactor
        window.twistedFactory = P2PFactory(
            window.communication, window.peerInfo, logger
        )
        window.logger.info("Factory initialized")
        window.ca_key, window.ca_cert = generateCa()
        window.cert_options = genCrtAndKey(window.ca_key, window.ca_cert)

        reactor.listenSSL(
            config["factory"]["port"],
            window.twistedFactory,
            window.cert_options,
        )
        window.logger.info(f'Reactor listens: {config["factory"]["port"]}')
        reactor.runReturn(installSignalHandlers=False)

        exit(app.exec_())


if __name__ == "__main__":
    main()
