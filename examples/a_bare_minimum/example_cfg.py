from enum import IntEnum, auto

from libpuns.client.client_node import CNetworkNode
from libpuns.connection.connection_globals import SpecialMessage
from libpuns.connection.message_registry import Flags, MsgRegistry
from libpuns.connection.packers import Int32, String
from libpuns.server.server_node import SNetworkNode


class NodeTypes(IntEnum):
    _skip = max(SpecialMessage) + 1
    ExamplePlayer = auto()


MsgRegistry.configure(
    NodeTypes.ExamplePlayer, [
        ('test', Flags.OwnerSend, (Int32(), )),
        ('second_test', Flags.Broadcast, (String(), )),
    ]
)


@MsgRegistry.server_class(NodeTypes.ExamplePlayer)
class SExamplePlayer(SNetworkNode):
    def do_test(self, value: int) -> None:
        print('test called', value)
        self.send_update('second_test', f'hello {value}')


@MsgRegistry.client_class(NodeTypes.ExamplePlayer)
class CExamplePlayer(CNetworkNode):
    def do_second_test(self, value: str) -> None:
        print('string received:', value)


class ExampleLocalPlayer(CExamplePlayer):
    DClass = CExamplePlayer

    def do_second_test(self, value: str) -> None:
        print('this is a local player')
        super().do_second_test(value)
