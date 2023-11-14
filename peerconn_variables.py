from peerconn_models import ( PeerData, PeerSocket)
from asyncio import (AbstractEventLoop, Event, Queue)
from typing import List
from logging import Logger
from os import path
from sys import argv as sys_argv

class Variables:
    """Basis variables defined for PeerConn."""
    _peersockets:       List[PeerSocket] | None     # PeerSocket list to store and manage multiple connections
    _peerdata:                  PeerData | None     # User's PeerData
    _SLEEP_TIME:                    float = 0.1     # Sleep time constant for async functions 
    _logger:                      Logger | None     # Logger object for logging transactions
    _loop:             AbstractEventLoop | None     # Async loop object
    _command_event:                Event | None     # Event object for thread_main function
    _command_queue:                Queue | None     # Queue to store and run commands
    log_filename:                     str = 'last.log'
    _file_delimiter:               bytes | None = b'PEERCONN_DELIMETER'             # Delimiter for uploading file with its info, in binary > [file_info, delimiter, file]
    _BASE_PATH:                       str = path.abspath(path.dirname(sys_argv[0])) # Path of the PeerConn
    _DOWNLOADS_DIR:                str = path.join(_BASE_PATH, 'downloads')         # Download directory path
    _config_path:                     str = path.join(_BASE_PATH, 'config.json')    # Path of the configuration json file for user preferences like custom host name and custom downloads directory