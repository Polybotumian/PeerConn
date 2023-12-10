from peerconn_models import (StreamReader, StreamWriter, datetime, PeerData,
                    Message, History, Servers, Streams, PeerSocket,
                    FileData, MessageTypes, Events, PeerPacket)
from uuid import (uuid4)
from asyncio import (start_server, open_connection, create_task, get_running_loop, sleep, wait_for, TimeoutError,
                     CancelledError, IncompleteReadError, Event, Queue)
from socket import (gethostname, AF_INET)
from typing import (List, AnyStr)
from pickle import (dumps as pickle_dumps, loads as picke_loads)
from logging import (basicConfig, DEBUG as LOGGING_DEBUG, getLogger, Logger)
from psutil import (net_if_addrs)
from os import (path, makedirs)
from ipaddress import (ip_address)
from json import (dumps as json_dumps, dump as json_dump, loads as json_loads)
from cryptography.fernet import (Fernet)

from peerconn_commands import Commands

class PeerConn(Commands):
    """Main class for gathering seperate PeerConn classes and accessibility."""
    def __init__(self) -> None:
        self._configure_logging()
        self._peersockets = []
        self._peerdata = PeerData(
            name= gethostname(),
            local_address= self.get_ipv4_address(adapter_names= ['Wi-Fi', 'WiFi'])
        )
        self._command_event = Event()
        self._command_queue = Queue()
        if not path.exists(self._DOWNLOADS_DIR):
            makedirs(self._DOWNLOADS_DIR)
        self.configuration_file(False)
        self._logger.info(f'{PeerConn.__name__}: Initialized.')
    
    def configuration_file(self, new_configs:bool) -> None:
        if not path.exists(self._config_path) and new_configs == False:
            with open(self._config_path, 'w', encoding= 'utf-8') as config_file:
                json_dump({'name':self._peerdata.name, 'download_dir': self._DOWNLOADS_DIR}, config_file)
            self._logger.info(f'{self.configuration_file.__name__}: Configuration file initialized.')
        elif path.exists(self._config_path) and new_configs == True:
            with open(self._config_path, 'w', encoding= 'utf-8') as config_file:
                json_dump({'name':self._peerdata.name, 'download_dir': self._DOWNLOADS_DIR}, config_file)
            self._logger.info(f'{self.configuration_file.__name__}: New configuration file has saved.')
        else:
            with open(self._config_path, 'r', encoding= 'utf-8') as config_file:
                config = json_loads(config_file.read())
                self._DOWNLOADS_DIR = config['download_dir']
                self._peerdata.name = config['name']
            self._logger.info(f'{self.configuration_file.__name__}: Configurations are set.')

    def is_valid_ipv4(self, ip: str) -> bool:
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False

    def create_peer_socket(self, custom_id: str = None) -> str:
        peersocket_ref = PeerSocket(
            id= custom_id if custom_id != None else str(uuid4()),
            history= History()
        )
        self._peersockets.append(peersocket_ref)

        self._logger.info(f'{self.create_peer_socket.__name__}: {peersocket_ref.id}')

        return peersocket_ref.id

    def set_peersocket(self, id: str, peerdata: PeerData) -> None:
        peersocket_ref = self.get_socket(id)
        if peersocket_ref != None:
            peersocket_ref.peerdata = peerdata
            self._logger.info(f'{self.set_peersocket.__name__}: {peersocket_ref.id}')
        else:
            self._logger.warning(f'{self.set_peersocket.__name__}: {id} not found!')

    def create_client_name(self) -> str:
        return f'Client_{len(self._peersockets)}'

    def get_client_sockets(self) -> List[PeerSocket]:
        matches = [peersocket for peersocket in self._peersockets if peersocket.servers == None]
        if matches:
            return matches
        else:
            return None

    def get_server_sockets(self) -> List[PeerSocket]:
        matches = [peersocket for peersocket in self._peersockets if peersocket.servers != None]
        if matches:
            return matches
        else:
            return None

    def get_active_connections(self) -> List[PeerSocket]:
        matches = [peersocket for peersocket in self._peersockets if peersocket.msg_comm_connected and peersocket.file_comm_connected]
        if matches:
            return matches
        else:
            return None

    def get_inactive_connections(self) -> List[PeerSocket]:
        matches = [peersocket for peersocket in self._peersockets if not peersocket.msg_comm_connected and not peersocket.file_comm_connected]
        if matches:
            return matches
        else:
            return None

    def get_socket(self, id: str) -> PeerSocket:
        matches = [peersocket for peersocket in self._peersockets if peersocket.id == id]
        if matches:
            return matches[0]
        else:
            return None

    async def hm_close(self, id: str) -> None:
        self._logger.info(f'{self.hm_close.__name__}: {id}')
        peersocket_ref = self.get_socket(id)

        if peersocket_ref != None and peersocket_ref.servers or peersocket_ref.streams:
            peersocket_ref.msg_comm_connected = False
            peersocket_ref.file_comm_connected = False
            if peersocket_ref.servers != None:
                if peersocket_ref.servers.msg_server != None:
                    peersocket_ref.servers.msg_server.close()
                    await peersocket_ref.servers.msg_server.wait_closed()
                    peersocket_ref.servers.msg_server = None
                    self._logger.info(f'{self.hm_close.__name__}: Message server is closed.')

                if peersocket_ref.servers.file_server != None:
                    peersocket_ref.servers.file_server.close()
                    await peersocket_ref.servers.file_server.wait_closed()
                    peersocket_ref.servers.file_server = None
                    self._logger.info(f'{self.hm_close.__name__}: File server of is closed.')

            if peersocket_ref.streams != None:
                if peersocket_ref.streams.msg_writer != None:
                    peersocket_ref.streams.msg_writer.close()
                    await peersocket_ref.streams.msg_writer.wait_closed()
                    peersocket_ref.streams.msg_writer = None
                    self._logger.info(f'{self.hm_close.__name__}: Message writer of is closed.')

                if peersocket_ref.streams.file_writer != None:
                    peersocket_ref.streams.file_writer.close()
                    await peersocket_ref.streams.file_writer.wait_closed()
                    peersocket_ref.streams.file_writer = None
                    self._logger.info(f'{self.hm_close.__name__}: File writer of is closed.')
        else:
            self._logger.warning(f'{self.hm_close.__name__}: {id} not found!')

    async def create_key(self) -> bytes:
        self._logger.info(f'{self.create_key.__name__}: OK.')
        return Fernet.generate_key()
    
    async def exchange_key(self, peersocket_ref:PeerSocket) -> bool:
        try:
            dumped_packet = pickle_dumps(PeerPacket(self._peerdata, peersocket_ref.key, peersocket_ref.streams.msg_writer.get_extra_info('peername')))
            received_packet = None
            if peersocket_ref.servers != None:
                received_packet = await wait_for(peersocket_ref.streams.msg_reader.read(2048), 5)
                received_packet: PeerPacket = picke_loads(received_packet)
                peersocket_ref.key += received_packet.key
                peersocket_ref.streams.msg_writer.write(dumped_packet)
            else:
                peersocket_ref.streams.msg_writer.write(dumped_packet)
                received_packet = await wait_for(peersocket_ref.streams.msg_reader.read(2048), 5)
                received_packet: PeerPacket = picke_loads(received_packet)
                peersocket_ref.key = received_packet.key + peersocket_ref.key
            peersocket_ref.chiper_suite = Fernet(peersocket_ref.key)
            self._logger.info(f'{self.exchange_key.__name__}: OK.')
            return True
        except TimeoutError:
            self._logger.info(f'{self.exchange_key.__name__}: Timeout!')
        except Exception as e:
            self._logger.info(f'{self.exchange_key.__name__}: {e}')
        finally:
            await peersocket_ref.streams.msg_writer.drain()
        return False

    async def hm_set_server(self, id: str) -> None:
        self._logger.info(f'{self.hm_set_server.__name__}: {id}')
        peersocket_ref = self.get_socket(id)

        if peersocket_ref != None and peersocket_ref.peerdata != None:
            try:
                peersocket_ref.key = await self.create_key()
                peersocket_ref.servers = Servers()
                peersocket_ref.events = Events(msg_event_server= Event(), msg_event_stream= Event(), file_event_server= Event(), file_event_stream= Event())
                peersocket_ref.servers.msg_server = await start_server(
                    lambda reader, writer: self._server_incomming_messages(reader, writer, peersocket_ref, self._logger),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info(f'{self.hm_set_server.__name__}: Message server = OK.')

                # peersocket_ref.events.file_event_server = Event()
                peersocket_ref.servers.file_server = await start_server(
                    lambda reader, writer: self._server_incomming_files(reader, writer, peersocket_ref, self._logger),
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )
                
                self._logger.info(f'{self.hm_set_server.__name__}: File server = OK.')

            except Exception as ex:
                self._logger.error(f'{self.hm_set_server.__name__}: {id}: {ex}')

    async def _server_incomming_messages(self, reader: StreamReader, writer: StreamWriter, peersocket:PeerSocket, logger: Logger) -> None:
        try:
            if peersocket.streams == None:
                peersocket.streams = Streams()
            # peersocket.events.msg_event_server = Event()
            if peersocket.history.messages == None:
                peersocket.history.messages = []
            peersocket.streams.msg_reader = reader
            peersocket.streams.msg_writer = writer
            if await self.exchange_key(peersocket):
                peersocket.msg_comm_connected = True

                peersocket.history.messages.append(
                            Message(
                                sender= PeerConn.__name__,
                                content= 'Connected to message socket!',
                                date_time= datetime.now(),
                                type= MessageTypes.CONNECTION_ESTABLISHED
                            )
                        )
                peersocket.history.new_messages += 1

                while not peersocket.events.msg_event_server.is_set():
                    try:
                        data = await peersocket.streams.msg_reader.read(2048)
                        if data:
                            decrypted_data = peersocket.chiper_suite.decrypt(data)
                            data : PeerPacket = picke_loads(decrypted_data)
                            peersocket.history.messages.append(
                                Message(
                                    sender= data.sender.name,
                                    content= data.message.content,
                                    date_time= datetime.now(),
                                    type= MessageTypes.PEER
                                )
                            )
                            peersocket.history.new_messages += 1
                        else:
                            break
                    except IncompleteReadError as ex:
                        if peersocket.msg_comm_connected:
                            logger.warning(f'{peersocket.id} - {PeerConn._server_incomming_messages.__name__}: Connection with message socket closed abruptly! {ex}')
                        else:
                            logger.info(f'{peersocket.id} - {PeerConn._server_incomming_messages.__name__}: Disconnected from message socket.')
                        break
                    except OSError as ex:
                        logger.error(f'{peersocket.id} - {PeerConn._server_incomming_messages.__name__}: {ex}')
                        if ex.errno == 64:
                            peersocket.history.messages.append(
                                Message(
                                    sender= PeerConn.__name__,
                                    content= 'Connection lost with message port! The specified network name is no longer available.',
                                    date_time= datetime.now(),
                                    type= MessageTypes.CONNECTION_LOST
                                )
                            )
                        break
                    except Exception as ex:
                        logger.error(f'{peersocket.id} - {PeerConn._server_incomming_messages.__name__}: {ex}')
                        break
        finally:
            notify: str = None
            if peersocket.msg_comm_connected:
                notify = 'Connection with message socket closed abruptly!'
            else:
                notify = 'Disconnected from message socket.'
            peersocket.history.messages.append(
                        Message(
                            sender= PeerConn.__name__,
                            content= notify,
                            date_time= datetime.now(),
                            type= MessageTypes.CONNECTION_LOST
                        )
                    )
            peersocket.history.new_messages += 1
            if peersocket != None:
                peersocket.msg_comm_connected = False
                if peersocket.servers != None:
                    if peersocket.servers.msg_server != None:
                        peersocket.servers.msg_server.close()
                        await peersocket.servers.msg_server.wait_closed()
                        peersocket.servers.msg_server = None

                if peersocket.streams != None:
                    if peersocket.streams.msg_writer != None:
                        peersocket.streams.msg_writer.close()
                        await peersocket.streams.msg_writer.wait_closed()
                        peersocket.streams.msg_writer = None
                        peersocket.streams.msg_reader = None

    async def _server_incomming_files(self, reader: StreamReader, writer: StreamWriter, peersocket: PeerSocket, logger: Logger) -> None:
        try:
            if peersocket.streams == None:
                peersocket.streams = Streams()
            # peersocket.events.file_event_stream = Event()
            if peersocket.history.messages == None:
                peersocket.history.messages = []
            peersocket.streams.file_reader = reader
            peersocket.streams.file_writer = writer
            peersocket.file_comm_connected = True
            peersocket.file_percentage = 0

            peersocket.history.messages.append(
                        Message(
                            sender= PeerConn.__name__,
                            content= 'Connected to file socket!',
                            date_time= datetime.now(),
                            type= MessageTypes.CONNECTION_ESTABLISHED
                        )
                    )
            peersocket.history.new_messages += 1

            while not peersocket.events.file_event_server.is_set():
                try:
                    serialized_data = await peersocket.streams.file_reader.readuntil(PeerConn._file_delimiter)
                    peersocket.in_file_transaction = True
                    file_data:FileData = picke_loads(serialized_data.removesuffix(PeerConn._file_delimiter))
                    logger.info(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: Receiving a file: {file_data}')
                    todays_download_path = path.join(PeerConn._DOWNLOADS_DIR, str(datetime.now().date()))
                    if not path.exists(todays_download_path):
                        makedirs(todays_download_path)
                    received_file_path = path.join(todays_download_path, f'{file_data.name}{file_data.extension}')
                    with open(received_file_path, 'wb') as received_file:
                        peersocket.history.messages.append(
                            Message(
                                sender= PeerConn.__name__,
                                content= f'{peersocket.peerdata.name} is sending you [{file_data.name}{file_data.extension}, {file_data.size}].',
                                date_time= datetime.now(),
                                type= MessageTypes.FILE_NOTIFY_0
                            )
                        )
                        peersocket.history.new_messages += 1
                        readed_data_size = 0
                        while True:
                            try:
                                data = await wait_for(peersocket.streams.file_reader.read(4096), timeout= 3.0)
                                received_file.write(data)
                                readed_data_size += len(data)
                                peersocket.file_percentage = round((readed_data_size * 100) / file_data.size)
                                if readed_data_size >= file_data.size:
                                    logger.info(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: Completed! Received data size = {readed_data_size}.')
                                    peersocket.history.messages.append(
                                        Message(
                                            sender= PeerConn.__name__,
                                            content= f'[{file_data.name}{file_data.extension}, {readed_data_size}] is completely received!.',
                                            date_time= datetime.now(),
                                            type= MessageTypes.FILE_NOTIFY_1
                                        )
                                    )
                                    peersocket.history.new_messages += 1
                                    break
                                elif not data:
                                    logger.warning(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: Failed to receive!')
                                    peersocket.history.messages.append(
                                        Message(
                                            sender= PeerConn.__name__,
                                            content= f'[{file_data.name}{file_data.extension}, {readed_data_size}] is failed to receive!.',
                                            date_time= datetime.now(),
                                            type= MessageTypes.FILE_NOTIFY_1
                                        )
                                    )
                                    peersocket.history.new_messages += 1
                                    break
                            except TimeoutError:
                                peersocket.history.messages.append(
                                        Message(
                                            sender= PeerConn.__name__,
                                            content= f'[{file_data.name}{file_data.extension}, {readed_data_size}] is failed to receive!.',
                                            date_time= datetime.now(),
                                            type= MessageTypes.FILE_NOTIFY_1
                                        )
                                    )
                                peersocket.history.new_messages += 1
                                break
                except IncompleteReadError as ex:
                    if peersocket.file_comm_connected:
                        logger.warning(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: Connection with file socket closed abruptly! {ex}')
                    else:
                        logger.info(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: Disconnected from file socket.')
                    break
                except OSError as ex:
                    logger.error(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: {ex}')
                    if ex.errno == 64:
                        peersocket.history.messages.append(
                            Message(
                                sender= PeerConn.__name__,
                                content= 'Connection lost with file port! The specified network name is no longer available.',
                                date_time= datetime.now(),
                                type= MessageTypes.CONNECTION_LOST
                            )
                        )
                    break
                except Exception as ex:
                    logger.error(f'{peersocket.id} - {PeerConn._server_incomming_files.__name__}: {ex}')
                    break
                finally:
                    peersocket.in_file_transaction = False
        finally:
            notify: str = None
            if peersocket.file_comm_connected:
                notify = 'Connection with file socket closed abruptly!'
            else:
                notify = 'Disconnected from file socket.'
            peersocket.history.messages.append(
                        Message(
                            sender= PeerConn.__name__,
                            content= notify,
                            date_time= datetime.now(),
                            type= MessageTypes.CONNECTION_LOST
                        )
                    )
            peersocket.history.new_messages += 1
            if peersocket != None:
                peersocket.file_comm_connected = False
                if peersocket.servers != None:
                    if peersocket.servers.file_server != None:
                        peersocket.servers.file_server.close()
                        await peersocket.servers.file_server.wait_closed()
                        peersocket.servers.file_server = None

                if peersocket.streams != None:
                    if peersocket.streams.file_writer != None:
                        peersocket.streams.file_writer.close()
                        await peersocket.streams.file_writer.wait_closed()
                        peersocket.streams.file_writer = None
                        peersocket.streams.file_reader = None

    async def hm_connect(self, id: str) -> None:
        peersocket_ref = self.get_socket(id)
        if peersocket_ref is not None:
            self._logger.info(f'{peersocket_ref.id} - {self.hm_connect.__name__}: {peersocket_ref.peerdata.local_address}: {peersocket_ref.peerdata.msg_port}, {peersocket_ref.peerdata.file_port}')
            try:
                peersocket_ref.key = await self.create_key()
                peersocket_ref.streams = Streams()
                peersocket_ref.events = Events(msg_event_server= Event(), msg_event_stream= Event(), file_event_server= Event(), file_event_stream= Event())
                peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.msg_port
                )

                self._logger.info(f'{peersocket_ref.id} - {self.hm_connect.__name__}: Message server = OK.')

                peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer = await open_connection(
                    peersocket_ref.peerdata.local_address,
                    peersocket_ref.peerdata.file_port
                )

                self._logger.info(f'{peersocket_ref.id} - {self.hm_connect.__name__}: File server = OK.')

                create_task(self._server_incomming_messages(peersocket_ref.streams.msg_reader, peersocket_ref.streams.msg_writer, peersocket_ref, self._logger))
                create_task(self._server_incomming_files(peersocket_ref.streams.file_reader, peersocket_ref.streams.file_writer, peersocket_ref, self._logger))

            except Exception as ex:
                self._logger.error(f'{id} - {self.hm_connect.__name__}: {ex}')

    async def hm_close_all(self) -> None:
        for peersocket in self._peersockets:
            await self.hm_close(peersocket.id)

    async def hm_exit(self) -> None:
        await self.hm_close_all()
        self._peersockets.clear()
        self._logger.info(f'{self.hm_exit.__name__}: Active peersockets = {len(self._peersockets)}')
        self._logger.info(f'{self.hm_exit.__name__}: Exiting {PeerConn.__name__}..')

    async def hm_send_message(self, id: str, data: str) -> None:
        try:
            peersocket_ref = self.get_socket(id)
            if peersocket_ref != None:
                if peersocket_ref.streams != None:
                    if peersocket_ref.streams.msg_writer != None:
                        packet = PeerPacket(sender= self._peerdata, target= peersocket_ref.streams.msg_writer.get_extra_info('peername'), message= Message(self._peerdata.name, data, datetime.now(), MessageTypes.ME))
                        packet_dump = pickle_dumps(packet)
                        encrypted_dump = peersocket_ref.chiper_suite.encrypt(packet_dump)
                        peersocket_ref.streams.msg_writer.write(encrypted_dump)
                        peersocket_ref.history.messages.append(packet.message)
                        await peersocket_ref.streams.msg_writer.drain()
                        self._logger.info(f'{peersocket_ref.id} - {self.hm_send_message.__name__}: Sent!')
                    else:
                        self._logger.info(f'{peersocket_ref.id} - {self.hm_send_message.__name__}: Can\'t sent!')
                        self.no_repeat_notification_msg(
                            peersocket_ref, Message(
                                sender= PeerConn.__name__,
                                content= 'Message can\'t be send!',
                                date_time= datetime.now(),
                                type= MessageTypes.SYSTEM_WARN
                            )
                        )
                else:
                    self.no_repeat_notification_msg(
                            peersocket_ref, Message(
                                sender= PeerConn.__name__,
                                content= 'No connection!',
                                date_time= datetime.now(),
                                type= MessageTypes.SYSTEM_WARN
                            )
                        )
        except ConnectionError as ex:
            self._logger.error(f'{id} - {self.hm_send_message.__name__}: {ex}')
            await self.close(id)

    async def hm_send_file(self, id: str, file_path: str) -> None:
        try:
            path.isdir(file_path)
            peersocket_ref = self.get_socket(id)
            if peersocket_ref != None and not peersocket_ref.in_file_transaction:
                if peersocket_ref.streams.file_writer != None:
                    peersocket_ref.in_file_transaction = True
                    file_name_without_extension, file_extension = path.splitext(file_path)
                    file_name_without_extension = file_name_without_extension.split('/')[-1]
                    file_data = FileData(name= file_name_without_extension, extension= file_extension, size= path.getsize(file_path))
                    serialized_file_data = pickle_dumps(file_data)
                    self._logger.info(f'{peersocket_ref.id} - {PeerConn.hm_send_file.__name__}: Sending a file: {file_data}')
                    self.no_repeat_notification_msg(peersocket_ref,
                        Message(
                            sender= PeerConn.__name__,
                            content= f'Sending [{file_data.name}{file_data.extension}, {file_data.size}] to {peersocket_ref.peerdata.name}.',
                            date_time= datetime.now(),
                            type= MessageTypes.FILE_NOTIFY_0
                        )
                    )
                    peersocket_ref.streams.file_writer.write(serialized_file_data)
                    peersocket_ref.streams.file_writer.write(self._file_delimiter)
                    with open(file_path, 'rb') as file:
                        total_write = 0
                        while not peersocket_ref.events.file_event_stream.is_set():
                            chunk = file.read(4096)
                            if not chunk:
                                peersocket_ref.file_percentage = 0
                                peersocket_ref.in_file_transaction = False
                                break
                            peersocket_ref.streams.file_writer.write(chunk)
                            await peersocket_ref.streams.file_writer.drain()
                            total_write += len(chunk)
                            peersocket_ref.file_percentage = round((total_write * 100) / file_data.size)
                            await sleep(self._SLEEP_TIME)
                    if peersocket_ref.events.file_event_stream.is_set():
                        self._logger.info(f'{peersocket_ref.id} - {self.hm_send_file.__name__}: Cancelled!')
                        self.no_repeat_notification_msg(peersocket_ref,
                            Message(
                                sender= PeerConn.__name__,
                                content= f'[{file_data.name}{file_data.extension}] is cancelled!',
                                date_time= datetime.now(),
                                type= MessageTypes.FILE_NOTIFY_1
                            )
                        )
                    else:
                        self._logger.info(f'{peersocket_ref.id} - {self.hm_send_file.__name__}: Sent!')
                        self.no_repeat_notification_msg(peersocket_ref,
                            Message(
                                sender= PeerConn.__name__,
                                content= f'[{file_data.name}{file_data.extension}] is sent to {peersocket_ref.peerdata.name}!',
                                date_time= datetime.now(),
                                type= MessageTypes.FILE_NOTIFY_1
                            )
                        )
                    peersocket_ref.events.file_event_stream.clear()
                else:
                    self.no_repeat_notification_msg(peersocket_ref,
                        Message(
                            sender= PeerConn.__name__,
                            content= 'File can\'t be send!',
                            date_time= datetime.now(),
                            type= MessageTypes.SYSTEM_WARN
                        )
                    )
        except Exception as ex:
            self._logger.error(f'{id} - {self.hm_send_file.__name__}: {peersocket_ref.id}, {ex}')
        finally:
            peersocket_ref.in_file_transaction = False

    def no_repeat_notification_msg(self, peersocket_ref: PeerSocket, message: Message) -> None:
        if peersocket_ref.history.messages:
            if peersocket_ref.history.messages[-1].content != message.content:
                peersocket_ref.history.messages.append(message)
                peersocket_ref.history.new_messages += 1

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

    def get_ipv4_address(self, adapter_names: list[str]) -> str:
        for interface, addrs in net_if_addrs().items():
            for adapter_name in adapter_names:
                if interface.startswith(adapter_name):
                    for addr in addrs:
                        if addr.family == AF_INET:
                            self._logger.info(f'{self.get_ipv4_address.__name__}: {interface} {addr.address}.')
                            return addr.address
        self._logger.error(f'{self.get_ipv4_address.__name__}: Cannot found!')
        return None

    async def thread_main(self) -> None:
        try:
            self._logger.info(f'{self.thread_main.__name__}: Running.')
            self._loop = get_running_loop()
            while self._loop.is_running():
                try:
                    command: PeerConn.Command = await self._command_queue.get()
                    self._logger.info(f'{self.thread_main.__name__}: {command.type}')
                    if command.type == PeerConn.CommandTypes.set_server:
                        await self.hm_set_server(command.content[0])
                    elif command.type == PeerConn.CommandTypes.connect:
                        await self.hm_connect(command.content[0])
                    elif command.type == PeerConn.CommandTypes.send_message:
                        await self.hm_send_message(command.content[0], command.content[1])
                    elif command.type == PeerConn.CommandTypes.send_file:
                        create_task(self.hm_send_file(command.content[0], command.content[1]))
                    elif command.type == PeerConn.CommandTypes.cancel_file:
                        self.get_socket(command.content[0]).events.file_event_stream.set()
                    elif command.type == PeerConn.CommandTypes.change_download_dir:
                        PeerConn._DOWNLOADS_DIR = command.content[0]
                    elif command.type == PeerConn.CommandTypes.config_file:
                        self.configuration_file(command.content[0])
                    elif command.type == PeerConn.CommandTypes.close:
                        await self.hm_close(command.content[0])
                    elif command.type == PeerConn.CommandTypes.close_all:
                        await self.hm_close_all()
                    elif command.type == PeerConn.CommandTypes.exit:
                        await self.hm_exit()
                        break
                except CancelledError:
                    self._logger.error(f'{self.thread_main.__name__}: {ex}')
                except Exception as ex:
                    self._logger.error(f'{self.thread_main.__name__}: {ex}')
        except Exception as ex:
            self._logger.error(f'{self.thread_main.__name__}: {ex}')
        finally:
            if len(self._peersockets) > 0:
                await self.hm_exit()