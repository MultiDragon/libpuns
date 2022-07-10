import abc
from typing import Sequence, Any

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

ObjectID = tuple[int, int, int] | int


class Packable(abc.ABC):
    def get_signature(self) -> str:
        return f'P-{self.__class__.__name__}'

    @abc.abstractmethod
    def pack(self, message: PyDatagram, item) -> None:
        ...

    @abc.abstractmethod
    def unpack(self, pdi: PyDatagramIterator) -> Any:
        ...


def extract_object_id(pdi: PyDatagramIterator) -> ObjectID:
    timestamp = pdi.getUint32()
    if timestamp < 1000000000:
        return timestamp
    return timestamp, pdi.getUint32(), pdi.getUint32()


def add_object_id(dg: PyDatagram, oid: ObjectID) -> None:
    if isinstance(oid, int):
        dg.addUint32(oid)
        return

    dg.addUint32(oid[0])
    dg.addUint32(oid[1])
    dg.addUint32(oid[2])


class CallbackConfig:
    arg_types: list[Packable]

    def __init__(self, flags: int, args: Sequence[Packable], default_value=None):
        self.flags = flags
        self.arg_types = list(args)

        self.default = default_value

    def pack(self, message: PyDatagram, args: tuple[...]) -> None:
        for arg, arg_type in zip(args, self.arg_types):
            arg_type.pack(message, arg)

    def unpack(self, pdi: PyDatagramIterator) -> tuple[...]:
        return tuple(arg_type.unpack(pdi) for arg_type in self.arg_types)

    def get_signature(self) -> str:
        return f'C-{self.flags}-' + '|'.join(arg_type.get_signature() for arg_type in self.arg_types)


class SClassDef:
    message_numbers: dict[str, int]
    message_types: dict[int, str]
    configurations: dict[int, CallbackConfig]
    conf_index: list[tuple[str, int, CallbackConfig]]

    def __init__(self):
        self.message_numbers = {}
        self.message_types = {}
        self.configurations = {}
        self.conf_index = []

    def add_message(self, message_type: str, message_number: int, cfg: CallbackConfig) -> None:
        self.message_numbers[message_type] = message_number
        self.message_types[message_number] = message_type
        self.configurations[message_number] = cfg
        self.conf_index.append((message_type, message_number, cfg))

    def get_message_number(self, message_type: str) -> int:
        return self.message_numbers[message_type]

    def get_message_name(self, message_number: int) -> str:
        return self.message_types[message_number]

    def get_message_data(self, message_number: int) -> tuple[str, CallbackConfig]:
        return self.message_types[message_number], self.configurations[message_number]

    def compile_datagram(self, message_type: str, *args, init_datagram: PyDatagram = None) -> PyDatagram:
        message_number = self.message_numbers[message_type]
        message = init_datagram or PyDatagram()
        message.addUint16(message_number)
        self.configurations[message_number].pack(message, args)
        return message

    def decompile_datagram(self, pdi: PyDatagramIterator) -> tuple[str, tuple[...]]:
        message_number = pdi.getUint16()
        message_type = self.message_types[message_number]
        return message_type, self.configurations[message_number].unpack(pdi)

    def get_signature(self) -> str:
        return 'S-' + '~'.join(f'{k}:{v.get_signature()}' for k, v in self.configurations.items())

    def get_flags(self, message_type: str) -> int:
        return self.configurations[self.message_numbers[message_type]].flags
