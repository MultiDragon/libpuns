# LibPUNS

## Introduction

**LibPUNS**, Panda3D Universal Networking System, is a simple networking library meant
to be used within Panda3D projects. It is written in Python and does not need any
external software, in contrast to the Distributed Object system that requires Astron.

## Example Usage
* This system is asymmetrical, which means the server nodes and the client nodes are not
interchangeable. Server nodes also have elevated privileges compared to the client nodes.
* The server side needs to initialize ServerMessageDirector:
```python
from libpuns.connection.message_registry import MsgRegistry
from libpuns.server.database_interface import DummyDatabaseInterface
from libpuns.server.server_director import ServerMessageDirector
from libpuns.server.server_node import SNetworkNode

@MsgRegistry.server_class(10)  # usage of enums strongly recommended
class ServerPlayer(SNetworkNode):
    pass

db = DummyDatabaseInterface()
server = ServerMessageDirector(db, ServerPlayer)
server.launch(7200)
```
This launches the server on port 7200 without database support.
* The client side needs to initialize ClientMessageDirector:
```python
from direct.showbase.ShowBase import ShowBase
from libpuns.connection.message_registry import MsgRegistry
from libpuns.client.client_director import ClientMessageDirector
from libpuns.client.client_node import CNetworkNode

def on_connect(node: CNetworkNode) -> None:
    print('Connected to the server, our avatar: ', node)

    
@MsgRegistry.client_class(10)  # usage of enums strongly recommended
class ClientPlayer(CNetworkNode):
    pass

client = ClientMessageDirector(ClientPlayer, on_connect)
base = ShowBase()
client.connect('127.0.0.1', 7200, 'login', 'password')
base.run()
```
* Both of the sides need to initialize the datagram signature:
```python
from libpuns.connection.message_registry import MsgRegistry, Flags
from libpuns.connection.packers import Int32, String

MsgRegistry.configure(
    10, [
        ('test', Flags.OwnerSend, (Int32(), String())),
    ]
)
```

After this is done, the ClientPlayer can send messages consisting of a 32-bit integer 
and a string to the server:
```python
def on_connect(node: CNetworkNode) -> None:
    print('Connected to the server, our avatar: ', node)
    node.send_update('test', (1, 'Hello World!'))

class ServerPlayer(SNetworkNode):
    def do_test(self, num: int, msg: str) -> None:
        print('Received message: ', num, msg)
```

More examples can be found in `examples` folder:
* `python -m a_bare_minimum.server` and `python -m a_bare_minimum.client`
* `python -m b_chat.server` followed by `python -m b_chat.client` and
`SECOND_CLIENT=1 python -m b_chat.client`

### Parser Flags

Each message can have one or more flags tied to it:
* `Flags.OwnerSend`: the message can be sent by the owner of the node. By default,
the nodes have no owner except for the avatar, `transfer_owner` changes it.
* `Flags.ClientSend`: the message can be sent by any client.
* `Flags.Database`: the message is saved in database when sent. Implies RAM.
* `Flags.RAM`: the message is saved in RAM when sent. Whenever a client enters the
zone with this object, this message is sent to the client with others.
* `Flags.Required`: Send the message to the client when the client enters the zone with
it, even if it's not saved in RAM. Uses `get_{message_name}` to get the message if it's
not in RAM, database, and does not have a default value.
* `Flags.Broadcast`: Rather than sending this only to the node's owner, send it to
every client in the zone with the object.

## Todo
* Add support for MongoDB
* Improve handling of malicious datagrams
* Add more packer types
* Simplify basic operations

## Notes
* This is a proof of concept. While I plan to expand this later, use at your own risk.
* `object_id` can be either an int32 or a tuple of three int32s (12 bytes = the size of
ObjectID in MongoDB). `int32` is used for dynamic objects that are not stored in the
database.
