from asyncio import run, create_task
from peerconn import PeerConn, PeerData
from custom_curses_items import CustomCursesMenu, CustomMenuItem, CustomFunctionItem, CustomSubmenuItem
from socket import gethostname, gethostbyname

class PeerConnMenu(PeerConn):
    menu_main: CustomCursesMenu | None
    menu_profile: CustomCursesMenu | None

    def __init__(self):
        super().__init__()
        self.menu_main = CustomCursesMenu("PeerConn Interactive Interface", "Main Menu:")

        self.menu_profile = CustomCursesMenu("FunctionItem", "Data:")
        self.menu_profile.items.append(CustomFunctionItem(self._my_name, self.change_name, override_index= "Name", seperator= " : "))
        self.menu_profile.items.append(CustomFunctionItem(gethostname(), self.refresh_host_name, override_index= "Host Name", seperator=" : "))
        self.menu_profile.items.append(CustomFunctionItem(gethostbyname(gethostname()), self.refresh_local_address, override_index= "Local Address", seperator= " : "))

        self.menu_main.items.append(CustomSubmenuItem("Profile", self.menu_profile, override_index= ""))
        self.menu_main.items.append(CustomFunctionItem(len(self._peersockets), self.refresh_active_connections, override_index= "Active Sockets", seperator= " = "))
        self.menu_main.items.append(CustomFunctionItem("", self.listen_manual, override_index= "Create Socket"))

    def change_name(self):
        self._my_name = input("New name is -> ")
        self.menu_profile.items[0].text = self._my_name

    def refresh_host_name(self):
        self.menu_profile.items[1].text = gethostname()

    def refresh_local_address(self):
        self.menu_profile.items[2].text = gethostbyname(gethostname())

    def refresh_active_connections(self):
        self.menu_main.items[1].text = len(self._peersockets)

    async def listen_manual(self):
        id = run(self.create_peer_socket())
        self.refresh_active_connections()
        await self.set_peersocket(
            id= id,
            peerdata_server= PeerData(
            name= self._my_name,
            local_address= gethostbyname(gethostname()),
            msg_port= input("Message Port = "),
            file_port= input("File Port = ")
            )
            )
        await create_task(self.listen(id))

    def run(self):
        self.menu_main.show()
        self.exit()

if __name__ == '__main__':
    app = PeerConnMenu()
    app.run()