# :electric_plug:PeerConn
 Peer-to-peer socket desktop application for Windows OS.
# :question:About
PeerConn is a peer-to-peer socket chat desktop application. It allows you to create multiple sockets to communicate with other sockets. It aims to manage communication and data transfer between computers with a user-friendly graphical interface.

It is developed using Python and many libraries used in development such as PyQt5, asyncio, psutil, logging. 

Due to the handling of multiple sockets and data transfer processes, PeerConn has to work in an async loop. For this reason there are 2 threads that this program has to use. The main thread is for the PyQt5 interface and the other is for PeerConn itself. 

For the sake of integration of PeerConn with PyQt5 and the performance of the application and the nature of async programming, PeerConn has a main method that remains a loop that handles runtime transactions and waits for runtime commands via event. This way all tasks are created in the same loop and are able to execute certain methods in a sync code and it also keeps async sockets alive.

It has a basic logging system that logs actions and errors in the program to a file with the extension "log".

**Please report any bugs you have found when using PeerConn. I would also be grateful if you could let me know what you think is missing from PeerConn.**
# :closed_book:Guide
#### Host Name and Local Address:
PeerConn automatically assigns your computer name as "Host Name" and finds your IPv4 to assign it as "Local Address". The most important thing here is your Local Address, which you can use to set up listener peer sockets for incoming connections, or to connect to another computer using its IPv4.

#### Listen and Connect buttons:
These buttons allow you to create 2 different types of peersockets, these are server and client peersockets. When you create a peersocket it will appear in a list on the left hand side of the window.

#### Peersockets:
The left pane of the window is a list of peersockets. You can select a peersocket by clicking on it. When a socket is selected, you can only interact with that peersocket. You can also change the name of the peersocket from the context menu that opens when you right click on it.

#### Server Peersocket:
This type of peersocket is for incoming connections. A server peersocket has a down arrow icon to indicate that it is a server.

#### Client Peersocket:
This type of peersocket is for connecting to a server peersocket. A client peersocket has an up arrow icon to indicate that it is a client.

### :small_red_triangle_down:Peersocket icon colours:
- :yellow_circle:Yellow: Indicates that it is active and waiting for a connection.
- :green_circle:Green: Indicates that it is active and connected.
- :red_circle:Red: Indicates inactive and connection lost.

### To Send Multiple Files
You should zip your files and then send the zip file.
### To Connect Over Different Networks
You should use 3rd party tools. (e.g. Localtonet)
