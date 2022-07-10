from enum import IntEnum, auto
from typing import Sequence, Type

from libpuns.connection.datagram_util import SClassDef, CallbackConfig
from libpuns.connection.network_node import NetworkNode
from libpuns.connection.packers import Packable


class CallbackObject:
    def __init__(self, name: str, flags: int, packables: Sequence[Packable], default_value=None):
        self.name = name
        self.flags = flags
        self.packables = packables
        self.default_value = default_value

    def make_tuple(self) -> tuple[str, CallbackConfig]:
        return self.name, CallbackConfig(self.flags, self.packables, default_value=self.default_value)


CallbackTuple = tuple[str, int, Sequence[Packable]]
Callback = CallbackTuple | CallbackObject


class RegistryTargets(IntEnum):
    Client = auto()
    Server = auto()


class Flags(IntEnum):
    ClientSend = 1
    OwnerSend = 2
    Database = 4 | 8
    RAM = 8
    Broadcast = 16
    Required = 32


class MsgRegistry:
    TypeIndex: dict[int, SClassDef] = {}
    ClientIndex: dict[int, Type[NetworkNode]] = {}
    ServerIndex: dict[int, Type[NetworkNode]] = {}
    ClientTypeIndex: dict[Type[NetworkNode], int] = {}
    ServerTypeIndex: dict[Type[NetworkNode], int] = {}

    @staticmethod
    def get_signature() -> str:
        return '\n'.join(f'{k}: {v.get_signature()}' for k, v in MsgRegistry.TypeIndex.items())

    @staticmethod
    def configure(class_num: int, callbacks: Sequence[Callback], extends: list[int] = None) -> None:
        if class_num not in MsgRegistry.TypeIndex:
            MsgRegistry.TypeIndex[class_num] = SClassDef()

        callback_cfg: list[tuple[str, CallbackConfig]] = []
        for callback in callbacks:
            if isinstance(callback, tuple):
                callback_cfg.append((callback[0], CallbackConfig(callback[1], callback[2])))
            else:
                callback_cfg.append(callback.make_tuple())

        if extends:
            extends_types = [MsgRegistry.TypeIndex[extend] for extend in extends]
            callback_cfg = [(mt, c) for ptype in extends_types for mt, n, c in ptype.conf_index] + callback_cfg

        stype = MsgRegistry.TypeIndex[class_num]
        for message_number, (message_type, callback) in enumerate(callback_cfg):
            stype.add_message(message_type, message_number, callback)

    @staticmethod
    def server_class(class_num: int):
        def decorate(cls: Type[NetworkNode]):
            cls.ClassNumber = class_num
            MsgRegistry.ServerIndex[class_num] = cls
            MsgRegistry.ServerTypeIndex[cls] = class_num
            return cls

        return decorate

    @staticmethod
    def client_class(class_num: int):
        def decorate(cls: Type[NetworkNode]):
            cls.ClassNumber = class_num
            MsgRegistry.ClientIndex[class_num] = cls
            MsgRegistry.ClientTypeIndex[cls] = class_num
            return cls

        return decorate
