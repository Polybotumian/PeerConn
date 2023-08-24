from dataclasses import dataclass, field
from asyncio import AbstractServer
from asyncio.streams import StreamReader, StreamWriter
from datetime import datetime
from typing import List

class ServerResponses:
    MSG: str = 'M3554G3_R3513V3D'
    FILE_CHUNK: str = 'CHUNK_R3513V3D'
    FILE: str = 'F1L3_R3513V3D'

class MessageTypes:
    ME: int = 0
    PEER: int = 1
    CONNECTION_ESTABLISHED: int = 2
    CONNECTION_LOST: int = 3
    SYSTEM_NOTIFY: int = 4
    SYSTEM_WARN: int = 5

# Data class to store peer connection details
@dataclass
class PeerData:
    name: str | None = None
    local_address: str | None = None
    msg_port: int | None = None
    file_port: int | None = None

@dataclass
class FileData:
    name: str | None = None
    extension: str | None = None
    size : int | None = None

# Data class to represent individual messages
@dataclass
class Message:
    sender: str | None = 'Sender'      # Name of the sender
    content: str | None = 'None'       # Content of the message
    date_time: datetime | None = None  # Indicates when the message was sent/received
    type: int | None = None

# Data class to manage message history
@dataclass
class History:
    messages: List[Message] | None = field(default_factory=list)  # List of messages
    new_messages: int = 0                                         # Number of undisplayed messages

# Data class to store references to servers
@dataclass
class Servers:
    msg_server: AbstractServer | None = None  # Reference to the server for handling messages
    file_server: AbstractServer | None = None # Reference to the server for handling files

# Data class to manage data streams
@dataclass
class Streams:
    msg_reader: StreamReader | None = None    # Reader to read data from the socket (messages)
    msg_writer: StreamWriter | None = None    # Writer to write data to the socket (messages)
    file_reader: StreamReader | None = None   # Reader to read data from the socket (files)
    file_writer: StreamWriter | None = None   # Writer to write data to the socket (files)

# Main class representing an asynchronous socket
@dataclass
class PeerSocket:
    id: str | None = None                 # An identifier for the socket (could be None if not assigned)
    servers: Servers | None = None        # References to servers for handling messages and files
    streams: Streams | None = None        # Data streams for messages and files
    history: History | None = None        # Message history
    peerdata: PeerData | None = None      # Peer data of this computer
    msg_comm_connected: bool = False      # Indicates whether the message communication established
    file_comm_connected: bool = False     # Indicates whether the file communication established
    in_file_transaction: bool = False
    file_percentage: int | None = None