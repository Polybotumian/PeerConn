from dataclasses import dataclass
from asyncio import AbstractServer
from asyncio.streams import StreamReader, StreamWriter
from datetime import datetime

class ServerResponses:
    MSG: str = 'M3554G3_R3513V3D'
    FILE_CHUNK: str = 'CHUNK_R3513V3D'
    FILE: str = 'F1L3_R3513V3D'

# Data class to store peer connection details
@dataclass
class PeerData:
    name: str | None
    local_address: str | None
    msg_port: int | None
    file_port: int | None

# Data class to represent individual messages
@dataclass
class Message:
    sender: str | None          # Name of the sender
    content: str | None         # Content of the message
    date_time: datetime | None  # Indicates when the message was sent/received
    recieved: bool | None

# Data class to manage message history
@dataclass
class History:
    messages: list[Message] | None  # List of messages
    new_messages: int               # Number of undisplayed messages

# Data class to store references to servers
@dataclass
class Servers:
    msg_server: AbstractServer | None  # Reference to the server for handling messages
    file_server: AbstractServer | None # Reference to the server for handling files

# Data class to manage data streams
@dataclass
class Streams:
    msg_reader: StreamReader | None    # Reader to read data from the socket (messages)
    msg_writer: StreamWriter | None    # Writer to write data to the socket (messages)
    file_reader: StreamReader | None    # Reader to read data from the socket (files)
    file_writer: StreamWriter | None    # Writer to write data to the socket (files)

# Main class representing an asynchronous socket
@dataclass
class PeerSocket:
    id: str | None                 # An identifier for the socket (could be None if not assigned)
    servers: Servers | None        # References to servers for handling messages and files
    streams: Streams | None        # Data streams for messages and files
    history: History | None        # Message history
    peerdata_server: PeerData | None  # Peer data of this computer
    peerdata_client: PeerData | None  # Peer data of peer computer
    msg_comm_connected: bool          # Indicates whether the message communication established
    file_comm_connected: bool         # Indicates whether the file communication established
