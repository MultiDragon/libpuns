import builtins
from typing import Type, cast

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.showbase import EventManagerGlobal, MessengerGlobal, DConfig
from direct.task import TaskManagerGlobal
from direct.task.Task import Task
from panda3d.core import PointerToConnection, QueuedConnectionListener, NetAddress, NetDatagram

from libpuns.connection.connection import MessageDirector
from libpuns.connection.connection_globals import KickReason, SpecialMessage
from libpuns.connection.datagram_util import ObjectID, add_object_id, extract_object_id
from libpuns.connection.message_registry import MsgRegistry, Flags
from libpuns.connection.network_node import NetworkNode
from libpuns.server.database_interface import DatabaseInterface
from libpuns.server.memory_handler import MemoryHandler
from libpuns.server.server_node import SNetworkNode


class ServerMessageDirector(MessageDirector):
    partial_connections: list[PointerToConnection]
    identified_connections: dict[ObjectID, PointerToConnection]
    reverse_identified_connections: dict[PointerToConnection, ObjectID]
    db_interface: DatabaseInterface
    zone_connections: dict[int, set[ObjectID]]
    reverse_zone_connections: dict[ObjectID, int]
    objects: dict[ObjectID, SNetworkNode]

    def __init__(self, db_interface: DatabaseInterface, player_class: Type[SNetworkNode]):
        super().__init__()
        self.class_index = MsgRegistry.ServerTypeIndex
        self.player_class = player_class
        self.listener = QueuedConnectionListener(self.connman, 0)
        self.partial_connections = []
        self.identified_connections = {}
        self.db_interface = db_interface
        self.memory_handler = MemoryHandler(db_interface)

        self.zone_connections = {}
        self.reverse_zone_connections = {}
        self.reverse_identified_connections = {}

        self.register_special(SpecialMessage.ConnectionRequest, self.handle_connection_request)
        self.register_special(SpecialMessage.ZoneRequest, self.handle_zone_request)
        self.register_special(SpecialMessage.ObjectRequest, self.handle_object_request)

    def handle_object_request(self, conn: PointerToConnection, pdi: PyDatagramIterator):
        if conn not in self.reverse_identified_connections:
            self.notify.warning(f'Client {self.get_connection_descriptor(conn)} used ObjectRequest '
                                f'while not initialized')
            self.eject_client(conn, KickReason.PartialRequest)
            return

        client_oid = self.reverse_identified_connections[conn]
        if client_oid not in self.reverse_zone_connections:
            self.notify.warning(f'Client {self.get_connection_descriptor(conn)} used ObjectRequest '
                                f'while not initialized')
            self.eject_client(conn, KickReason.PartialRequest)
            return

        oid = extract_object_id(pdi)
        if self.reverse_zone_connections.get(oid) != self.reverse_zone_connections.get(client_oid):
            self.notify.warning(f'Client {self.get_connection_descriptor(conn)} used ObjectRequest in the wrong zone!')
            self.eject_client(conn, KickReason.HiddenZone)
            return

        obj = self.objects[oid]
        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ObjectResponse)
        add_object_id(dg, oid)
        dg.addUint16(obj.ClassNumber)
        self.memory_handler.pack_object(cast(SNetworkNode, obj), dg)
        self.send_datagram(conn, dg)

    def generate_with_zone(self, obj: SNetworkNode, zone: int):
        if zone not in self.zone_connections:
            self.zone_connections[zone] = set()

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ObjectResponse)
        add_object_id(dg, obj.oid)
        dg.addUint16(obj.ClassNumber)
        self.memory_handler.pack_object(cast(SNetworkNode, obj), dg)
        self.broadcast_to_zone(zone, dg)

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ZoneData)
        dg.addUint32(zone)
        dg.addUint16(len(self.zone_connections[zone]))
        for x in self.zone_connections[zone]:
            add_object_id(dg, x)
            dg.addUint16(self.objects[x].ClassNumber)
            self.memory_handler.pack_object(cast(SNetworkNode, self.objects[x]), dg)
        self.send_datagram(self.identified_connections[obj.oid], dg)

        self.zone_connections[zone].add(obj.oid)

    def disconnect_from_zone(self, oid: ObjectID):
        if oid in self.reverse_zone_connections:
            current_zone = self.reverse_zone_connections[oid]
            del self.reverse_zone_connections[oid]
            self.zone_connections[current_zone].remove(oid)

    def handle_zone_request(self, conn: PointerToConnection, pdi: PyDatagramIterator):
        if conn not in self.reverse_identified_connections:
            self.notify.warning(f'Client {self.get_connection_descriptor(conn)} used ZoneRequest while not initialized')
            self.eject_client(conn, KickReason.PartialRequest)
            return

        oid = self.reverse_identified_connections[conn]
        self.disconnect_from_zone(oid)
        zone = pdi.getUint32()
        self.reverse_zone_connections[oid] = zone
        if zone not in self.zone_connections:
            self.zone_connections[zone] = set()
        self.zone_connections[zone].add(oid)

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ZoneResponse)
        dg.addUint32(zone)
        self.send_datagram(conn, dg)
        self.generate_with_zone(self.objects[oid], zone)

    def broadcast_to_zone(self, zone: int, datagram: PyDatagram, ignore: ObjectID = None) -> None:
        if zone not in self.zone_connections:
            self.notify.warning(f'Trying to broadcast to a zone {zone} that does not exist!')
            return

        for oid in self.zone_connections[zone]:
            if oid == ignore:
                continue

            self.send_datagram(self.identified_connections[oid], datagram)

    def parse_message(self, message: NetDatagram) -> None:
        try:
            super().parse_message(message)
        except ValueError as e:
            self.notify.warning(f'Error parsing message: {str(e)}')
            self.eject_client(message.getConnection(), KickReason.InvalidMessage)

    def send_datagram(self, connection: PointerToConnection, datagram: PyDatagram) -> None:
        self.writer.send(datagram, connection)

    def get_connection_descriptor(self, conn: PointerToConnection) -> str:
        if conn in self.reverse_identified_connections:
            return f'OID-{self.reverse_identified_connections[conn]}'
        return f'@ {conn.getAddress().getIpString()}:{conn.getAddress().getPort()}'

    def eject_client(self, conn: PointerToConnection, kick_reason: int) -> None:
        self.notify.warning(f'Kicking client {self.get_connection_descriptor(conn)} for reason {kick_reason}')
        dg = PyDatagram()
        dg.addUint16(SpecialMessage.Disconnect)
        dg.addUint8(kick_reason)
        self.send_datagram(conn, dg)

        if conn in self.reverse_identified_connections:
            user_id = self.reverse_identified_connections[conn]
            del self.identified_connections[user_id]
            self.disconnect_from_zone(user_id)
            del self.reverse_identified_connections[conn]
        self.reader.removeConnection(conn)

    def handle_connection_request(self, conn: PointerToConnection, pdi: PyDatagramIterator) -> None:
        if conn not in self.partial_connections:
            self.eject_client(conn, KickReason.InvalidConnectionRequest)
            return

        signature_hash = pdi.getBlob()
        login = pdi.getString()
        token = pdi.getString()

        if self.signature != signature_hash:
            self.notify.warning(f'Signature mismatch from {self.get_connection_descriptor(conn)}: '
                                f'expected {self.signature}, got {signature_hash}')
            self.eject_client(conn, KickReason.InvalidSignature)
            return

        oid = self.db_interface.attempt_login(login, token)
        if oid is None:
            self.eject_client(conn, KickReason.InvalidLogin)
            return

        if oid in self.identified_connections:
            self.eject_client(self.identified_connections[oid], KickReason.DoubleLogin)

        self.reverse_identified_connections[conn] = oid
        self.identified_connections[oid] = conn
        self.partial_connections.remove(conn)
        self.objects[oid] = self.player_class(self, oid)
        self.objects[oid].transfer_owner(oid)

        dg = PyDatagram()
        dg.addUint16(SpecialMessage.ConnectionResponse)
        add_object_id(dg, oid)
        dg.addUint32(0)  # Zone ID
        self.send_datagram(conn, dg)

    def send_datagram_to(self, obj: ObjectID | NetworkNode, flags: int, datagram: PyDatagram,
                         bypass_zone_required: bool = False, broadcast_ignore: ObjectID = None, **kwargs) -> None:
        if isinstance(obj, NetworkNode):
            oid = obj.oid
        else:
            oid = obj

        if not bypass_zone_required and oid not in self.reverse_zone_connections:
            self.notify.warning(f'Trying to send datagram to object {oid} without zone')
            if oid in self.identified_connections:
                self.eject_client(self.identified_connections[oid], KickReason.PartialRequest)
            return

        if flags & Flags.Broadcast:
            self.broadcast_to_zone(self.reverse_zone_connections[oid], datagram, ignore=broadcast_ignore)
        else:
            self.send_datagram(self.identified_connections[oid], datagram)

    def poll_rendezvous(self, task: Task):
        if self.listener.newConnectionAvailable():
            rendezvous, connection = PointerToConnection(), PointerToConnection()
            address = NetAddress()
            if self.listener.getNewConnection(rendezvous, address, connection):
                connection_ptr = connection.p()
                self.partial_connections.append(connection_ptr)
                self.reader.addConnection(connection_ptr)
        return task.cont

    def launch(self, port: int, configure_panda: bool = True) -> None:
        if configure_panda:
            builtins.config = DConfig
            builtins.taskMgr = TaskManagerGlobal.taskMgr
            builtins.eventMgr = EventManagerGlobal.eventMgr
            builtins.messenger = MessengerGlobal.messenger

        self.compile_signature()
        rendezvous = self.connman.openTCPServerRendezvous(port, 1000)
        self.listener.addConnection(rendezvous)
        taskMgr.add(self.poll_rendezvous, 'Poll the connection listener', -39)
        self.start_reader()
        self.notify.warning(f'Launched server on port {port}')

        if configure_panda:
            taskMgr.run()

    def request_object_data(self, message: NetDatagram, oid: ObjectID):
        self.notify.warning(f'Requested object data for ObjectID {oid}')
        self.eject_client(message.getConnection(), KickReason.InvalidObjectID)

    def decompile_datagram(self, conn: PointerToConnection, obj: SNetworkNode, pdi: PyDatagramIterator) -> None:
        typedef = MsgRegistry.TypeIndex[obj.ClassNumber]
        msg_name, msg_data = typedef.decompile_datagram(pdi)
        flags = typedef.get_flags(msg_name)

        client_oid = self.reverse_identified_connections.get(conn)
        if client_oid is None:
            self.notify.warning(f'Received message {msg_name} from unidentified client {conn}')
            self.eject_client(conn, KickReason.PartialRequest)
            return

        if not (flags & Flags.ClientSend) and not (flags & Flags.OwnerSend and obj.owner == client_oid):
            self.notify.warning(f'Received message {msg_name} from client {conn} without permission')
            self.eject_client(conn, KickReason.PermissionDenied)
            return

        if flags & Flags.RAM:
            self.memory_handler.set_data(obj.oid, msg_name, msg_data, update_db=flags & Flags.Database != 0)

        getattr(obj, f'do_{msg_name}')(*msg_data)

