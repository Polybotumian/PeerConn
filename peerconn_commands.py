from peerconn_variables import Variables
from peerconn_models import (dataclass)

class Commands(Variables):
    """Has command definations for ability of use async functions within sync script."""
    @dataclass
    class CommandTypes:
        """Command Type Enum"""
        exit: int = 0               
        set_server: int = 1       # Sets PeerSocket as server
        connect: int = 2          # Connects to a PeerSocket
        send_message: int = 3
        send_file: int = 4
        cancel_file: int = 5
        change_download_dir: int = 6
        config_file: int = 7      # Transactions about configuration json file
        close: int = 8            # Closes a PeerSocket
        close_all: int = 9        # Closes all PeerSockets

    @dataclass
    class Command:
        type: int = None
        content: list = None

    def set_server(self, peersocket_id: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.set_server,
                    content= [peersocket_id]
                )
        )

    def connect(self, peersocket_id: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.connect,
                    content= [peersocket_id]
                )
        )

    def send_message(self, peersocket_id: str, message: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.send_message,
                    content= [peersocket_id, message]
                )
        )

    def send_file(self, peersocket_id: str, file_path: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.send_file,
                    content= [peersocket_id, file_path]
                )
        )

    def cancel_file(self, peersocket_id: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.cancel_file,
                    content= [peersocket_id]
                )
        )

    def change_download_dir(self, dir_path: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.change_download_dir,
                    content= [dir_path]
                )
        )

    def config_file(self, save) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.config_file,
                    content= [save]
                )
        )

    def close(self, peersocket_id: str) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.close,
                    content= [peersocket_id]
                )
        )

    def close_all(self) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.close_all
                )
        )

    def exit(self) -> None:
        self._queue_command(
            Commands.Command(
                    type= Commands.CommandTypes.exit
                )
        )

    def _queue_command(self, command: Command) -> None:
        self._loop.call_soon_threadsafe(
                self._command_queue.put_nowait,
                command
            )