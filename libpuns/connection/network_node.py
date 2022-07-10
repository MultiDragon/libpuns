from typing import Protocol, Type, Union

from direct.distributed.PyDatagram import PyDatagram
from direct.showbase.DirectObject import DirectObject

from libpuns.connection.datagram_util import ObjectID, add_object_id, SClassDef


class DirectorProto(Protocol):
    # class_definitions: dict[Type['NetworkNode'], SClassDef]
    class_index: dict[Type['NetworkNode'], int]
    type_index: dict[int, SClassDef]

    def send_datagram_to(self, obj: Union[ObjectID, 'NetworkNode'], flags: int, datagram: PyDatagram, **kwargs) -> None:
        ...


class NetworkNode(DirectObject):
    ClassNumber: int = None
    DClass: Type['NetworkNode']

    def __init__(self, director: DirectorProto, oid: ObjectID):
        super().__init__()
        self.director = director
        self.oid = oid

        if not hasattr(self, 'DClass'):
            self.DClass = self.__class__

    def send_update(self, message_type: str, *args, **kwargs) -> None:
        cindex = self.director.class_index[self.DClass]
        cdef = self.director.type_index[cindex]
        dg = PyDatagram()
        dg.addUint16(cindex)
        add_object_id(dg, self.oid)
        dg = cdef.compile_datagram(message_type, *args, init_datagram=dg)
        self.director.send_datagram_to(self, cdef.get_flags(message_type), dg, **kwargs)
