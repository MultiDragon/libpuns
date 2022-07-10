from direct.showbase.ShowBase import ShowBase

from libpuns.client.client_director import ClientMessageDirector
from libpuns.client.client_node import CNetworkNode

from .example_cfg import ExampleLocalPlayer


def on_connect(node: CNetworkNode) -> None:
    print('Connected to the server')
    node.send_update('test', 1234)


client = ClientMessageDirector(ExampleLocalPlayer, on_connect)
base = ShowBase()
client.connect('127.0.0.1', 7201, 'login', 'password')
base.run()
