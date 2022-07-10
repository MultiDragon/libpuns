from typing import Optional, Protocol, Union

from direct.distributed.PyDatagram import PyDatagram

from libpuns.connection.connection_globals import SpecialMessage
from libpuns.connection.datagram_util import ObjectID, add_object_id
from libpuns.connection.network_node import NetworkNode, DirectorProto


class SDirectorProto(DirectorProto, Protocol):
    def send_datagram_to(self, obj: Union[ObjectID, 'NetworkNode'], flags: int, datagram: PyDatagram,
                         bypass_zone_required: bool = False) -> None:
        ...


class SNetworkNode(NetworkNode):
    director: SDirectorProto
    owner: Optional[ObjectID] = None

    def transfer_owner(self, new_owner: ObjectID) -> None:
        self.owner = new_owner

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.TransferOwner)
        add_object_id(dg, self.oid)
        self.director.send_datagram_to(new_owner, 0, dg, bypass_zone_required=True)
