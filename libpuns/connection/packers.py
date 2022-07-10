import abc
from typing import Any

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

from libpuns.connection.datagram_util import add_object_id, extract_object_id, Packable


class Int32(Packable):
    def pack(self, message: PyDatagram, item: int) -> None:
        message.addInt32(item)

    def unpack(self, pdi: PyDatagramIterator) -> int:
        return pdi.getInt32()


class String(Packable):
    def pack(self, message: PyDatagram, item: str) -> None:
        message.addString(item)

    def unpack(self, pdi: PyDatagramIterator) -> str:
        return pdi.getString()


class ObjectIDPacker(Packable):
    pack = add_object_id
    unpack = extract_object_id
