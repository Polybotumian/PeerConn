from models import StreamReader, StreamWriter, datetime, ServerResponses, PeerData, Message, History, Servers, Streams, PeerSocket
from uuid import uuid4
from asyncio import start_server, gather, sleep as async_sleep, open_connection, create_task, CancelledError, Task, run
from socket import gethostname, gethostbyname
from typing import List
#from pickle import dumps, loads
from logging import basicConfig, DEBUG as LOGGING_DEBUG, getLogger, Logger

class PeerConn:
    _peersockets: List[PeerSocket] | None
    _my_name: str | None
    _async_sleep_time: float = 0.1
    _tasks: list[Task] | None
    _logger: Logger | None

    def __init__(self, my_name:str = 'ME'):
        self._configure_logging()
        self._logger.info(f'Initializing {PeerConn.__name__}...')
        self._peersockets = []
        self._my_name = my_name

    async def create_peer_socket(self) -> str:
        self._logger.info('Creating a new peer socket..')
        peersocket_ref = PeerSocket(
            id= str(uuid4()),
            servers= Servers(
            msg_server= None,
            file_server= None
            ),
            streams= Streams(
            msg_reader= None,
            msg_writer= None,
            file_reader= None,
            file_writer= None
            ),
            history= History(
                messages= None,
                new_messages= False
            ),
            peerdata_server= PeerData(
                name= None,
                local_address= None,
                msg_port= None,
                file_port= None
            ),
            peerdata_client= PeerData(
                name= None,
                local_address= None,
                msg_port= None,
                file_port= None
            ),
            msg_comm_connected= False,
            file_comm_connected= False
        )
        self._peersockets.append(peersocket_ref)

        self._logger.info(f'New peer socket has created: id = {peersocket_ref.id}')

        return peersocket_ref.id
    
    async def set_peersocket(self, id: str, peerdata_server: PeerData = None, peerdata_client: PeerData = None):
        peersocket_ref = await self.get_socket(id)
        if peersocket_ref != None:
            self._logger.info(f'Setting peersocket peerdata variables: id = {peersocket_ref.id}')
            peersocket_ref.peerdata_server = peerdata_server
            peersocket_ref.peerdata_client = peerdata_client
            self._logger.info('Peersocket peerdata variables are set.')
    
    async def create_client_name(self) -> str:
        return f'Client_{len(self._peersockets)}'

    async def get_client_sockets(self) -> List[PeerSocket]:
        self._logger.info('Queering the acting as client peer sockets.')
        matches = [conn for conn in self._peersockets if conn.servers.msg_server == None and conn.servers.file_server == None]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None

    async def get_server_sockets(self) -> List[PeerSocket]:
        self._logger.info('Queering the acting as server peer sockets.')
        matches = [conn for conn in self._peersockets if conn.servers.msg_server != None and conn.servers.file_server != None]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None
        
    async def get_active_connections(self) -> List[PeerSocket]:
        self._logger.info('Queering the connected peer sockets.')
        matches = [conn for conn in self._peersockets if conn.msg_comm_connected and conn.file_comm_connected]
        if matches:
            self._logger.info('Peer sockets found, returning the list reference.')
            return matches
        else:
            self._logger.error('Peer sockets has not been found! Returning None.')
            return None
    
    async def get_socket(self, id: str) -> PeerSocket:
        self._logger.info(f'Queering the peer sockets for: id = {id}')
        matches = [conn for conn in self._peersockets if conn.id == id]
        if matches[0]:
            self._logger.info('Peer socket found, returning the reference.')
            return matches[0]
        else:
            self._logger.error('Peer socket has not been found! Returning None.')
            return None

    async def get_local_address(self) -> str:
        self._logger.info('Returning IPv4.')
        return gethostbyname(gethostname())
    
    async def disconnect(self, id: str):
        self._logger.info(f'Disconnecting peer socket: id = {id}')
        peersocket_ref = await self.get_socket(id)
        
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

    async def listen(self, id: str):
        self._logger.info(f'Listening for peer socket as server: id = {id}')
        peersocket_ref = await self.get_socket(id)

        if peersocket_ref != None:
            try:
                peersocket_ref.servers.msg_server = await start_server(
                    lambda r, w: PeerConn._handle_messages_as_server(r, w, peersocket_ref),
                    peersocket_ref.peerdata_server.local_address,
                    peersocket_ref.peerdata_server.msg_port
                )

                self._logger.info(f'Peer socket message server started: id = {id}')

                peersocket_ref.servers.file_server = await start_server(
                    lambda r, w: PeerConn._handle_files_as_server(r, w, peersocket_ref),
                    peersocket_ref.peerdata_server.local_address,
                    peersocket_ref.peerdata_server.file_port
                )

                self._logger.info(f'Peer socket file server started: id = {id}')

                await peersocket_ref.servers.msg_server.serve_forever()
                await peersocket_ref.servers.file_server.serve_forever()
            except Exception as ex:
                self._logger.error(f'EXCEPTION for peer socket {id}: {ex}')

    async def _handle_messages_as_server(reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket):
                peersocket.history.messages = []
                peersocket.msg_comm_connected = True
                try:
                    while peersocket.msg_comm_connected:
                            data = await reader.read(2048)
                            if data and data != b'\n':
                                peersocket.history.messages.append(
                                    Message(
                                        sender=peersocket.peerdata_client.name,
                                        content=data.decode("utf-8"),
                                        date_time=datetime.now(),
                                        recieved= None
                                    )
                                )
                                peersocket.history.new_messages += 1
                                writer.write(ServerResponses.MSG.encode("utf-8"))
                                await writer.drain()
                            await async_sleep(PeerConn._async_sleep_time)
                except CancelledError:
                    if peersocket.file_comm_connected:
                        raise

    async def _handle_files_as_server(reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket):
        peersocket.file_comm_connected = True
        try:
            while peersocket.file_comm_connected:
                    data = await reader.read(2048)
                    if data:
                        peersocket.history.messages.append(
                            Message(
                                sender=peersocket.peerdata_client.name,
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
                    await async_sleep(PeerConn._async_sleep_time)
        except CancelledError:
            if peersocket.file_comm_connected:
                raise

    async def connect_to(self, id: str, peerdata: PeerData) -> None:
        self._logger.info(f'Trying to connect {peerdata.local_address} via peer socket: id = {id}')
        peersocket_ref = await self.get_socket(id)
        if peersocket_ref is not None:
            try:
                peersocket_ref.peerdata_client = peerdata
                peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer = await open_connection(
                    peersocket_ref.peerdata_client.local_address,
                    peersocket_ref.peerdata_client.msg_port
                )

                self._logger.info('Connected to message server.')

                peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer = await open_connection(
                    peersocket_ref.peerdata_client.local_address,
                    peersocket_ref.peerdata_client.file_port
                )

                self._logger.info('Connected to file server.')

                create_task(PeerConn._handle_messages_as_server(peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer, peersocket_ref))
                create_task(PeerConn._handle_files_as_server(peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer, peersocket_ref))

                self._logger.info('Tasks are created.')
            except Exception as ex:
                self._logger.error(f'EXCEPTION for peer socket {id}: {ex}')

    async def exit_async(self):
        for peersocket in self._peersockets:
            await self.disconnect(peersocket.id)
        self._logger.info(f'Active peer sockets: {len(self._peersockets)}')
        # for task in self._tasks:
        #     task.cancel()
        #self._tasks.clear()
        #self._logger.info(f'Active Tasks: {len(self._tasks)}')
        self._logger.info(f'Exiting from {PeerConn.__name__}..')

    def exit(self):
        run(self.exit_async())

    def _configure_logging(self):
        basicConfig(
            filename='peerconn.log',
            level= LOGGING_DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self._logger = getLogger(__name__)
        self._logger.info('Logging configured.')
    
    # async def main(self):
    #     self._logger.info('Running main()..')

    #     self._tasks = [
            
    #     ]
    #     try:
    #         await gather(*self._tasks)
    #     except CancelledError:
    #         pass