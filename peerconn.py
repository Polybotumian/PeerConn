from models import StreamReader, StreamWriter, datetime, ServerResponses, PeerData, Message, History, Servers, Streams, PeerSocket
from uuid import uuid4
from asyncio import start_server, sleep as asyncio_sleep, open_connection, create_task, CancelledError, gather
from socket import gethostname, gethostbyname
from typing import List
#from pickle import dumps, loads
from logging import basicConfig, DEBUG as LOGGING_DEBUG, getLogger, Logger

class PeerConn:
    _peersockets: List[PeerSocket] | None
    _peerdata: PeerData | None
    _SLEEP_TIME: float = 0.1
    _logger: Logger | None
    _running: bool = False

    def __init__(self):
        self._configure_logging()
        self._logger.info(f'Initializing {PeerConn.__name__}...')
        self._peersockets = []
        self._peerdata = PeerData()

        self._running = True

    async def hm_create_peer_socket(self) -> str:
        self._logger.info('Creating a new peer socket..')
        peersocket_ref = PeerSocket(
            id= str(uuid4())
        )
        self._peersockets.append(peersocket_ref)

        self._logger.info(f'New peer socket has created: id = {peersocket_ref.id}')

        return peersocket_ref.id
    
    async def hm_set_peersocket(self, id: str, peerdata: PeerData):
        peersocket_ref = await self.hm_get_socket(id)
        if peersocket_ref != None:
            self._logger.info(f'Setting peersocket peerdata variables: id = {peersocket_ref.id}')
            peersocket_ref.peerdata = peerdata
            self._logger.info('Peersocket peerdata variables are set.')
    
    async def hm_create_client_name(self) -> str:
        print('NAME CREATED')
        return f'Client_{len(self._peersockets)}'

    async def hm_get_client_sockets(self) -> List[PeerSocket]:
        self._logger.info('Queering the acting as client peer sockets.')
        matches = [conn for conn in self._peersockets if conn.servers == None]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None

    async def hm_get_server_sockets(self) -> List[PeerSocket]:
        self._logger.info('Queering the acting as server peer sockets.')
        matches = [conn for conn in self._peersockets if conn.servers != None]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None
        
    async def hm_get_active_connections(self) -> List[PeerSocket]:
        self._logger.info('Queering the connected peer sockets.')
        matches = [conn for conn in self._peersockets if conn.msg_comm_connected and conn.file_comm_connected]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None
    
    async def hm_get_socket(self, id: str) -> PeerSocket:
        self._logger.info(f'Queering the peer sockets for: id = {id}')
        matches = [conn for conn in self._peersockets if conn.id == id]
        if matches:
            self._logger.info('Peer socket found, returning the reference.')
            return matches[0]
        else:
            self._logger.error('Peer socket has not been found! Returning None.')
            return None

    async def hm_get_local_address(self) -> str:
        self._logger.info('Returning IPv4.')
        return gethostbyname(gethostname())
    
    async def hm_disconnect(self, id: str):
        self._logger.info(f'Disconnecting peer socket: id = {id}')
        peersocket_ref = await self.hm_get_socket(id)
        
        if peersocket_ref != None:
            peersocket_ref.msg_comm_connected = False
            peersocket_ref.file_comm_connected = False
            if peersocket_ref.servers.msg_server != None:
                peersocket_ref.servers.msg_server.close()
                await peersocket_ref.servers.msg_server.wait_closed()

            if peersocket_ref.servers.file_server != None:
                peersocket_ref.servers.file_server.close()
                await peersocket_ref.servers.file_server.wait_closed()

            if peersocket_ref.streams.msg_writer != None:
                peersocket_ref.streams.msg_writer.close()
                await peersocket_ref.streams.msg_writer.wait_closed()

            if peersocket_ref.streams.file_writer != None:
                peersocket_ref.streams.file_writer.close()
                await peersocket_ref.streams.file_writer.wait_closed()
            del peersocket_ref
            self._logger.info('Peer socket is disconnected and removed.')

    async def hm_set_listener(self, id: str):
        self._logger.info(f'Listening for peer socket as server: id = {id}')
        peersocket_ref = await self.hm_get_socket(id)

        if peersocket_ref != None:
            try:
                peersocket_ref.servers = Servers()
                peersocket_ref.servers.msg_server = await start_server(
                    lambda r, w: PeerConn._server_incomming_messages(r, w, peersocket_ref),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info(f'Peer socket message server started: id = {id}')

                peersocket_ref.servers.file_server = await start_server(
                    lambda r, w: PeerConn._server_incomming_files(r, w, peersocket_ref),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )

                self._logger.info(f'Peer socket file server started: id = {id}')

            except Exception as ex:
                self._logger.error(f'Exception for peer socket {id}: {ex}')

    async def _server_incomming_messages(reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket):
                peersocket.history.messages = []
                peersocket.msg_comm_connected = True
                try:
                    while peersocket.msg_comm_connected:
                            data = await reader.read(2048)
                            if data and data != b'\n':
                                peersocket.history.messages.append(
                                    Message(
                                        sender=peersocket.peerdata.name,
                                        content=data.decode("utf-8"),
                                        date_time=datetime.now(),
                                        recieved= None
                                    )
                                )
                                peersocket.history.new_messages += 1
                                writer.write(ServerResponses.MSG.encode("utf-8"))
                                await writer.drain()
                            await asyncio_sleep(PeerConn._SLEEP_TIME)
                except CancelledError:
                    if peersocket.file_comm_connected:
                        raise

    async def _server_incomming_files(reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket):
        peersocket.file_comm_connected = True
        try:
            while peersocket.file_comm_connected:
                    data = await reader.read(2048)
                    if data:
                        peersocket.history.messages.append(
                            Message(
                                sender=peersocket.peerdata.name,
                                content=data.decode("utf-8"),
                                date_time=datetime.now(),
                                recieved= None
                            )
                        )
                    while True:
                        file_data = await reader.read(4096)
                        if not file_data:
                            break
                        print(file_data.decode())
                        writer.write(ServerResponses.MSG.encode("utf-8"))
                        await writer.drain()
                    await asyncio_sleep(PeerConn._SLEEP_TIME)
        except CancelledError:
            if peersocket.file_comm_connected:
                raise

    async def hm_connect_to(self, id: str, peerdata: PeerData) -> None:
        self._logger.info(f'Trying to connect {peerdata.local_address} via peer socket: id = {id}')
        peersocket_ref = await self.hm_get_socket(id)
        if peersocket_ref is not None:
            try:
                peersocket_ref.peerdata = peerdata
                peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info('Connected to message server.')

                peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )

                self._logger.info('Connected to file server.')

                create_task(
                    gather(
                        PeerConn._server_incomming_messages(peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer, peersocket_ref),
                        PeerConn._server_incomming_files(peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer, peersocket_ref)
                    )
                )

                self._logger.info('Tasks are created.')
            except Exception as ex:
                self._logger.error(f'Exception for peer socket {id}: {ex}')

    async def hm_exit(self):
        for peersocket in self._peersockets:
            await self.hm_disconnect(peersocket.id)
        self._logger.info(f'Active peer sockets: {len(self._peersockets)}')
        self._logger.info(f'Exiting from {PeerConn.__name__}..')

    def _configure_logging(self):
        basicConfig(
            filename='peerconn.log',
            level= LOGGING_DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self._logger = getLogger(__name__)
        self._logger.info('Logging configured.')