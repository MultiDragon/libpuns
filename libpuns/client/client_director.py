from typing import Callable, Type

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from panda3d.core import NetDatagram, PointerToConnection

from libpuns.client.client_node import CNetworkNode
from libpuns.connection.connection import MessageDirector
from libpuns.connection.connection_globals import SpecialMessage, KickReason
from libpuns.connection.datagram_util import ObjectID, add_object_id, extract_object_id
from libpuns.connection.message_registry import MsgRegistry
from libpuns.connection.network_node import NetworkNode


class ClientMessageDirector(MessageDirector):
    requested_objects: set[ObjectID]

    DisconnectionReasons = {
        KickReason.InvalidSignature: 'Outdated client signature',
        KickReason.InvalidObjectID: 'Created a clientside object',
        KickReason.InvalidConnectionRequest: 'Attempted to login before the connection was established',
        KickReason.InvalidMessage: 'Error while parsing a datagram',
        KickReason.PartialRequest: 'Started doing requests before the connection was established',
        KickReason.HiddenZone: 'Requested an object from the hidden zone',
        KickReason.PermissionDenied: 'Attempt to edit a readonly field',

        KickReason.InvalidLogin: 'Incorrect login or token',
        KickReason.DoubleLogin: 'Logged in from another place',
    }

    def __init__(self, player_class: Type[CNetworkNode], on_connect: Callable[[CNetworkNode], None]):
        super().__init__()
        self.class_index = MsgRegistry.ClientTypeIndex
        self.player_class, self.on_connect = player_class, on_connect
        self.avatar = self.connection = None
        self.requested_objects = set()
        self.initialized = False
        self.zone = -1

        self.register_special(SpecialMessage.ConnectionResponse, self.handle_connection_response)
        self.register_special(SpecialMessage.Disconnect, self.handle_disconnect)
        self.register_special(SpecialMessage.ZoneResponse, self.handle_zone_response)
        self.register_special(SpecialMessage.ObjectResponse, self.handle_object_response)
        self.register_special(SpecialMessage.TransferOwner, self.handle_transfer_owner)
        self.register_special(SpecialMessage.ZoneData, self.handle_zone_data)

    def handle_transfer_owner(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        oid = extract_object_id(pdi)
        print(f'Received control over node {oid}')

    def handle_zone_data(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        zone_id = pdi.getUint32()
        print(f'Received zone data for zone {zone_id}')
        self.zone = zone_id
        object_count = pdi.getUint16()
        for i in range(object_count):
            self.handle_object_response(conn, pdi)

    def handle_object_response(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        oid = extract_object_id(pdi)
        if oid in self.requested_objects:
            self.requested_objects.remove(oid)

        class_number = pdi.getUint16()
        if oid not in self.objects:
            obj = MsgRegistry.ClientIndex[class_number](self, oid) if oid != self.avatar.oid else self.avatar
            self.objects[oid] = obj
        else:
            obj = self.objects[oid]

        field_count = pdi.getUint16()
        for i in range(field_count):
            self.decompile_datagram(conn, obj, pdi)

    def handle_zone_response(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        self.zone = pdi.getUint32()
        if not self.initialized:
            self.initialized = True
            self.on_connect(self.avatar)

    def handle_disconnect(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        reason = pdi.getUint8()
        disconnect_reason = self.DisconnectionReasons.get(reason, str(reason))
        self.notify.warning(f'Requested server disconnection. Reason: {disconnect_reason}')
        taskMgr.stop()

    def send_datagram(self, datagram: PyDatagram) -> None:
        if not self.connection:
            raise ConnectionError('Not connected.')
        self.writer.send(datagram, self.connection)

    def send_datagram_to(self, obj: ObjectID | NetworkNode, flags: int, datagram: PyDatagram, **kwargs) -> None:
        self.send_datagram(datagram)

    def handle_connection_response(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        user_id = extract_object_id(pdi)
        zone_id = pdi.getUint32()
        self.avatar = self.player_class(self, user_id)
        # self.on_connect(self.avatar)

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ZoneRequest)
        dg.addUint32(zone_id)
        self.send_datagram(dg)

    def connect(self, host: str, port: int, login: str, password: str) -> None:
        self.compile_signature()
        connection = self.connman.openTCPClientConnection(host, port, 3000)
        if not connection:
            raise ConnectionError('Could not connect to server.')

        self.connection = connection
        self.reader.addConnection(connection)
        self.start_reader()

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ConnectionRequest)
        dg.addBlob(self.signature)
        dg.addString(login)
        dg.addString(password)
        self.send_datagram(dg)

    def uncache(self, oid: ObjectID):
        if oid in self.requested_objects:
            self.requested_objects.remove(oid)

    def request_object_data(self, message: NetDatagram, oid: ObjectID):
        if oid in self.requested_objects:
            return

        self.requested_objects.add(oid)
        taskMgr.doMethodLater(2, self.uncache, f'CMD.uncache_{oid}', extraArgs=[oid])
        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ObjectRequest)
        add_object_id(dg, oid)
        self.send_datagram(dg)
