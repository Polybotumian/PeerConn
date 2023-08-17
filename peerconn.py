from models import StreamReader, StreamWriter, datetime, ServerResponses, PeerData, Message, History, Servers, Streams, PeerSocket, dataclass
from uuid import uuid4
from asyncio import start_server, sleep as asyncio_sleep, open_connection, create_task, CancelledError, gather, AbstractEventLoop, get_running_loop, Event, Queue
from socket import gethostname, AF_INET
from typing import List
#from pickle import dumps, loads
from logging import basicConfig, DEBUG as LOGGING_DEBUG, getLogger, Logger
from psutil import net_if_addrs

class PeerConn:
    _peersockets: List[PeerSocket] | None
    _peerdata: PeerData | None
    _SLEEP_TIME: float = 0.1
    _logger: Logger | None
    _loop: AbstractEventLoop | None
    _command_event: Event | None
    _command_queue: Queue | None
    log_filename: str = 'peerconn.log'

    def __init__(self) -> None:
        self._configure_logging()
        self._peersockets = []
        self._peerdata = PeerData(
            name= gethostname(),
            local_address= self.get_ipv4_address(adapter_name= 'Wi-Fi')
        )
        self._command_event = Event()
        self._command_queue = Queue()
        self._logger.info(f'{PeerConn.__name__}: Initialized.')

    def create_peer_socket(self, custom_id: str = None) -> str:
        peersocket_ref = PeerSocket(
            id= custom_id if custom_id != None else str(uuid4()),
            history= History()
        )
        self._peersockets.append(peersocket_ref)

        self._logger.info(f'{self.create_peer_socket.__name__}: {peersocket_ref.id}')

        return peersocket_ref.id
    
    def set_peersocket(self, id: str, peerdata: PeerData):
        peersocket_ref = self.get_socket(id)
        if peersocket_ref != None:
            peersocket_ref.peerdata = peerdata
            self._logger.info(f'{self.set_peersocket.__name__}: {peersocket_ref.id}')
    
    def create_client_name(self) -> str:
        return f'Client_{len(self._peersockets)}'

    def get_client_sockets(self) -> List[PeerSocket]:
        matches = [conn for conn in self._peersockets if conn.servers == None]
        if matches:
            return matches
        else:
            return None

    def get_server_sockets(self) -> List[PeerSocket]:
        matches = [conn for conn in self._peersockets if conn.servers != None]
        if matches:
            return matches
        else:
            return None
        
    def get_active_connections(self) -> List[PeerSocket]:
        matches = [conn for conn in self._peersockets if conn.msg_comm_connected and conn.file_comm_connected]
        if matches:
            return matches
        else:
            return None
        
    def get_inactive_connections(self) -> List[PeerSocket]:
        matches = [conn for conn in self._peersockets if not conn.msg_comm_connected and not conn.file_comm_connected]
        if matches:
            return matches
        else:
            return None
    
    def get_socket(self, id: str) -> PeerSocket:
        matches = [conn for conn in self._peersockets if conn.id == id]
        if matches:
            return matches[0]
        else:
            return None
    
    async def hm_disconnect(self, id: str) -> None:
        self._logger.info(f'{self.hm_disconnect.__name__}: {id}')
        peersocket_ref = self.get_socket(id)
        
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
            self._peersockets.remove(peersocket_ref)
            self._logger.info(f'{self.hm_disconnect.__name__}: OK.')

    async def hm_set_listener(self, id: str) -> None:
        self._logger.info(f'{self.hm_set_listener.__name__}: {id}')
        peersocket_ref = self.get_socket(id)

        if peersocket_ref != None and peersocket_ref.peerdata != None:
            try:
                peersocket_ref.servers = Servers()
                peersocket_ref.servers.msg_server = await start_server(
                    lambda reader, writer: PeerConn._server_incomming_messages(reader, writer, peersocket_ref),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info(f'{self.hm_set_listener.__name__}: Message server = OK.')

                peersocket_ref.servers.file_server = await start_server(
                    lambda reader, writer: PeerConn._server_incomming_files(reader, writer, peersocket_ref),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )

                self._logger.info(f'{self.hm_set_listener.__name__}: File server = OK.')

            except Exception as ex:
                self._logger.error(f'{self.hm_set_listener.__name__}: {id}: {ex}')

    async def _server_incomming_messages(reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket):
                try:
                    peersocket.history.messages = []
                    peersocket.streams = Streams()
                    peersocket.streams.msg_reader = reader
                    peersocket.streams.msg_writer = writer
                    peersocket.msg_comm_connected = True
                    while peersocket.msg_comm_connected:
                            data = await reader.read(2048)
                            if data and data != b'\n':
                                peersocket.history.messages.append(
                                    Message(
                                        sender=peersocket.peerdata.name,
                                        content=data.decode("utf-8"),
                                        date_time=datetime.now()
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
        try:
            peersocket.history.messages = []
            peersocket.streams.file_reader = reader
            peersocket.streams.file_writer = writer
            peersocket.file_comm_connected = True
            while peersocket.file_comm_connected:
                    data = await reader.read(2048)
                    if data:
                        peersocket.history.messages.append(
                            Message(
                                sender=peersocket.peerdata.name,
                                content=data.decode("utf-8"),
                                date_time=datetime.now(),
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
        self._logger.info(f'{self.hm_connect_to.__name__}: {peerdata.local_address}, {id}')
        peersocket_ref = self.get_socket(id)
        if peersocket_ref is not None:
            try:
                peersocket_ref.peerdata = peerdata
                peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info(f'{self.hm_connect_to.__name__}: Message server = OK.')

                peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )

                self._logger.info(f'{self.hm_connect_to.__name__}: File server = OK.')

                create_task(
                    gather(
                        PeerConn._server_incomming_messages(peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer, peersocket_ref),
                        PeerConn._server_incomming_files(peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer, peersocket_ref)
                    )
                )
            except Exception as ex:
                self._logger.error(f'{self.hm_exit.__name__}: {id}, {ex}')

    async def hm_exit(self) -> None:
        for peersocket in self._peersockets:
            await self.hm_disconnect(peersocket.id)
        self._logger.info(f'{self.hm_exit.__name__}: Active peersockets = {len(self._peersockets)}')
        self._logger.info(f'{self.hm_exit.__name__}: Exiting {PeerConn.__name__}..')

    async def hm_send_message(self, id: str, data: str) -> None:
        try:
            peersocket_ref = self.get_socket(id)
            peersocket_ref.streams.msg_writer.write(data.encode("utf-8"))
            peersocket_ref.history.messages.append(Message(self._peerdata.name, data, datetime.now()))
            await peersocket_ref.streams.msg_writer.drain()
        except Exception as ex:
            self._logger.error(f'{self.hm_send_message.__name__}: {peersocket_ref.id}, {ex}')

    def _configure_logging(self) -> None:
        with open(self.log_filename, "w") as file:
            file.close()
        basicConfig(
            filename = self.log_filename,
            level= LOGGING_DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self._logger = getLogger(__name__)
        self._logger.info(f'{self._configure_logging.__name__}: OK.')

    def get_ipv4_address(self, adapter_name: str) -> str:
        for interface, addrs in net_if_addrs().items():
            if interface == adapter_name:
                for addr in addrs:
                    if addr.family == AF_INET:
                        self._logger.info(f'{self.get_ipv4_address.__name__}: {interface} {addr.address}.')
                        return addr.address
        self._logger.error(f'{self.get_ipv4_address.__name__}: Cannot found!')
        return None
    
    @dataclass
    class CommandTypes:
        exit: int = 0
        set_listener: int = 1
        send_message: int = 2
        disconnect: int = 3
    
    @dataclass
    class Command:
        type: int = None
        socket_id: str = None
        peerdata: PeerData = None
        message: str = None
        file_path: str = None

    def set_listener(self, peersocket_id: str):
        self._queue_command(
            PeerConn.Command(
                    type= PeerConn.CommandTypes.set_listener,
                    socket_id= peersocket_id
                )
        )

    def send_message(self, peersocket_id: str, message: str):
        self._queue_command(
            PeerConn.Command(
                    type= PeerConn.CommandTypes.send_message,
                    socket_id= peersocket_id,
                    message= message
                )
        )

    def disconnect(self, peersocket_id: str):
        self._queue_command(
            PeerConn.Command(
                    type= PeerConn.CommandTypes.disconnect,
                    socket_id= peersocket_id,
                )
        )

    def exit(self):
        self._queue_command(
            PeerConn.Command(
                    type= PeerConn.CommandTypes.exit
                )
        )
        
    def _queue_command(self, command: Command):
        self._loop.call_soon_threadsafe(
                self._command_queue.put_nowait,
                command
            )
    
    async def thread_main(self):
        self._logger.info(f'{self.thread_main.__name__}: Running.')
        self._loop = get_running_loop()
        while self._loop.is_running():
            try:
                command: PeerConn.Command = await self._command_queue.get()
                self._logger.info(f'{self.thread_main.__name__}: {command.type}')
                if command.type == PeerConn.CommandTypes.set_listener:
                    await self.hm_set_listener(command.socket_id)
                elif command.type == PeerConn.CommandTypes.send_message:
                    await self.hm_send_message(command.socket_id, command.message)
                elif command.type == PeerConn.CommandTypes.disconnect:
                    await self.hm_disconnect(command.socket_id)
                elif command.type == PeerConn.CommandTypes.exit:
                    await self.hm_exit()
                    break
            except CancelledError:
                pass