import abc
import hashlib
from typing import Callable

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.showbase.DirectObject import DirectObject
from direct.task.Task import Task
from panda3d.core import QueuedConnectionManager, ConnectionWriter, QueuedConnectionReader, NetDatagram, \
    PointerToConnection

from libpuns.connection.connection_globals import SpecialMessage
from libpuns.connection.datagram_util import extract_object_id, ObjectID, SClassDef
from libpuns.connection.message_registry import MsgRegistry
from libpuns.connection.network_node import NetworkNode


SpecialCallback = Callable[[PointerToConnection, PyDatagramIterator], None]


class MessageDirector(DirectObject):
    special_messages: dict[SpecialMessage, SpecialCallback | None]
    objects: dict[ObjectID, NetworkNode]
    signature: bytes
    notify = directNotify.newCategory('MessageDirector')

    def __init__(self):
        super().__init__()
        self.type_index = MsgRegistry.TypeIndex

        self.connman = QueuedConnectionManager()
        self.reader = QueuedConnectionReader(self.connman, 0)
        self.writer = ConnectionWriter(self.connman, 0)
        self.objects = {}
        self.special_messages = {sm: None for sm in SpecialMessage}
        self.signature = b''

    def register_special(self, message_type: SpecialMessage, callback: SpecialCallback) -> None:
        self.special_messages[message_type] = callback

    def compile_signature(self) -> None:
        signature_str = MsgRegistry.get_signature()
        h = hashlib.new('sha256')
        h.update(signature_str.encode('utf-8'))
        self.signature = h.digest()

    def poll_reader(self, task: Task):
        if self.reader.dataAvailable():
            datagram = NetDatagram()
            if self.reader.getData(datagram):
                self.parse_message(datagram)
        return task.cont

    def start_reader(self) -> None:
        taskMgr.add(self.poll_reader, 'Poll the connection reader', -40)

    @abc.abstractmethod
    def request_object_data(self, message: NetDatagram, oid: ObjectID):
        pass

    def parse_message(self, message: NetDatagram) -> None:
        pdi = PyDatagramIterator(message)
        message_type = pdi.getUint16()
        if message_type in self.special_messages:
            special_callback = self.special_messages.get(message_type)
            if special_callback:
                special_callback(message.getConnection(), pdi)
                return

            raise ValueError(f'Unknown special message type: {message_type}')

        oid = extract_object_id(pdi)
        if oid not in self.objects:
            self.notify.warning(f'Received message for unknown object: {oid}')
            self.request_object_data(message, oid)
            return

        obj = self.objects[oid]
        if obj.ClassNumber != message_type:
            raise ValueError(f'Received invalid object type: expected {obj.ClassNumber}, got {message_type}.')

        self.decompile_datagram(message.getConnection(), obj, pdi)

    def decompile_datagram(self, conn: PointerToConnection, obj: NetworkNode, pdi: PyDatagramIterator) -> None:
        typedef = MsgRegistry.TypeIndex[obj.ClassNumber]
        msg_name, msg_data = typedef.decompile_datagram(pdi)
        getattr(obj, f'do_{msg_name}')(*msg_data)
