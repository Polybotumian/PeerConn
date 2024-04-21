from sys import argv, exit
from os import path, mkdir
from PyQt5.QtWidgets import QApplication
import qt5reactor
from mainWindow import MainWindow
from factories import P2PFactory
from json import load
import logging

def main():
    if path.exists('./local/defConfig.json'):
        
        with open('./local/defConfig.json', "r") as file:
            config = load(file)
        
        if not path.exists('./' + config['downloads']['dir']):
            mkdir('/'.join((path.curdir, config['downloads']['dir'])))
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(config['logger']['format'])

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(config['logger']['filename'], config['logger']['mode'])
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        app = QApplication(argv)
        qt5reactor.install()

        with open('./local/langUi.json', "r", encoding= 'utf-8') as file:
            window = MainWindow(load(file)[config['defLang']])
        window.logger = logger
        window.logger.info('Initialized')
        window.show()
        
        from twisted.internet import reactor
        window.reactor = reactor
        window.twistedFactory = P2PFactory(window.communication, window.peerInfo, logger)
        window.logger.info('Factory initialized')
        reactor.listenTCP(config['factory']['port'], window.twistedFactory)
        window.logger.info(f'Reactor listens: {config["factory"]["port"]}')
        reactor.runReturn(installSignalHandlers= False)

        exit(app.exec_())

if __name__ == '__main__':
    main()