"""
Main program entry.
"""
__version__ = "240615V4"
__author__ = "Yiğit Leblebicier"

from sys import argv, exit
from os import path, listdir, remove
from PyQt5.QtWidgets import QApplication
from window import Window
import qt5reactor
from json import load
import logging
from stun import get_ip_info

import factories
from cert_gen import genCrtAndKey, generateCa


def main():
    config_path = "config.json"
    init_err_log_path = "config_error.log"
    directoryList = listdir(path.curdir)

    if config_path in directoryList:
        with open(config_path, "r") as file:
            config = load(file)
    else:
        with open(path.join(init_err_log_path), "w") as file:
            file.write(f"{config_path} couldn't be found!")
            exit(-1)
    if init_err_log_path in directoryList:
        remove(init_err_log_path)

    del init_err_log_path
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging_formatter = logging.Formatter(config["logger"]["format"])
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging_formatter)
    logger.addHandler(console_handler)
    file_handler = logging.FileHandler(
        "last.log", config["logger"]["mode"]
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging_formatter)
    logger.addHandler(file_handler)

    app = QApplication(argv)
    qt5reactor.install()

    window = Window(config)
    window.logger = logger
    window.logger.info("Initialized")
    window.show()

    from twisted.internet import reactor
    window.reactor = reactor
    window.twistedFactory = factories.P2P(
        window.communication, logger
    )
    window.logger.info("Factory initialized")

    security_mode = config["security"]
    window.logger.info(f"Initializing with security mode: {security_mode}")

    port = config["port"]

    if config["usestun"]:
        try:
            nat_type, public_ip, public_port = get_ip_info()
            window.public_ip = public_ip
            window.logger.info(
                f"STUN Result - NAT Type: {nat_type}, Public IP: {public_ip}, Public Port: {public_port}")
            port = public_port
        except Exception as e:
            window.logger.error(f"STUN failed: {str(e)}")
            exit(-1)

    if security_mode is None:
        reactor.listenTCP(port, window.twistedFactory, interface='0.0.0.0')
    elif security_mode == "ssl/tls":
        window.ca_key, window.ca_cert = generateCa()
        window.cert_options = genCrtAndKey(window.ca_key, window.ca_cert)
        reactor.listenSSL(
            port,
            window.twistedFactory,
            window.cert_options,
            interface='0.0.0.0'
        )

    window.logger.info(f'Reactor listens on port: {port}')
    reactor.runReturn(installSignalHandlers=False)

    exit(app.exec_())


if __name__ == "__main__":
    main()
