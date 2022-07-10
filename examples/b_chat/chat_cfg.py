from enum import IntEnum, auto

from libpuns.client.client_node import CNetworkNode
from libpuns.connection.connection_globals import SpecialMessage
from libpuns.connection.datagram_util import ObjectID
from libpuns.connection.message_registry import Flags, MsgRegistry
from libpuns.connection.network_node import DirectorProto
from libpuns.connection.packers import String
from libpuns.server.server_node import SNetworkNode


class NodeTypes(IntEnum):
    _skip = max(SpecialMessage) + 1
    Talker = auto()


MsgRegistry.configure(
    NodeTypes.Talker, [
        ('request_username', Flags.OwnerSend, (String(), )),
        ('request_message', Flags.OwnerSend, (String(), )),
        ('username', 0, (String(), )),
        ('message', Flags.Broadcast | Flags.RAM, (String(), String(), )),
    ]
)


@MsgRegistry.server_class(NodeTypes.Talker)
class STalker(SNetworkNode):
    def __init__(self, director: DirectorProto, oid: ObjectID):
        super().__init__(director, oid)
        self.username = str(oid)

    def do_request_username(self, username: str) -> None:
        self.username = username
        self.send_update('username', username)

    def do_request_message(self, message: str) -> None:
        self.send_update('message', self.username, message, broadcast_ignore=self.oid)


@MsgRegistry.client_class(NodeTypes.Talker)
class CTalker(CNetworkNode):
    def __init__(self, director: DirectorProto, oid: ObjectID):
        super().__init__(director, oid)
        self.username = str(oid)

    def do_username(self, username: str) -> None:
        self.username = username
        base.append_log(f'Set own username to {username}')

    def do_message(self, username: str, message: str) -> None:
        base.append_log(f'{username}: {message}')

    def send_message(self, message: str) -> None:
        base.append_log(f'\n{self.username}: {message}')
        self.send_update('request_message', message)
