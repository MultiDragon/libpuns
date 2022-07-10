from typing import Any

from direct.distributed.PyDatagram import PyDatagram

from libpuns.connection.datagram_util import ObjectID
from libpuns.connection.message_registry import Flags
from libpuns.server.database_interface import DatabaseInterface
from libpuns.server.server_node import SNetworkNode


class MemoryHandler:
    query_memory: dict[ObjectID, dict[str, Any]]

    def __init__(self, db_interface: DatabaseInterface):
        self.db_interface = db_interface
        self.query_memory = {}

    def set_data(self, oid: ObjectID, field: str, value, update_db: bool = False):
        if oid not in self.query_memory:
            self.query_memory[oid] = {}

        self.query_memory[oid][field] = value
        if update_db and not isinstance(oid, int):
            self.db_interface.update_object(oid, field, value)

    def pack_object(self, obj: SNetworkNode, dg: PyDatagram) -> None:
        if obj.oid not in self.query_memory:
            self.query_memory[obj.oid] = {}

        compilation_data = []

        sclass = obj.director.type_index[obj.ClassNumber]
        for field, data in sclass.configurations.items():
            message_name = sclass.get_message_name(field)
            if message_name in self.query_memory[obj.oid]:
                compilation_data.append((field, message_name, self.query_memory[obj.oid][message_name]))
            elif data.default is not None:
                compilation_data.append((field, message_name, data.default))
            elif data.flags & Flags.Required:
                default_data = getattr(obj, f'get_{message_name}')
                compilation_data.append((field, message_name, default_data))

        dg.addUint16(len(compilation_data))
        for field_number, message_name, data in compilation_data:
            print(field_number, message_name, data)
            dg.addUint16(field_number)
            sclass.compile_datagram(message_name, data, dg)
