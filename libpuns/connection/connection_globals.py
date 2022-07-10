from enum import IntEnum, auto


class SpecialMessage(IntEnum):
    # Sent by the client when connecting. Stores the signature hash (int64) and the login data (string + string).
    ConnectionRequest = auto()
    # Sent by the server when the connection is complete. Stores the user ID (three int32s) and a zone ID (int32)
    ConnectionResponse = auto()
    # Sent by the client to trigger object visibility.
    ZoneRequest = auto()
    ZoneResponse = auto()
    # Sent by the server before the user is kicked. Stores the kick reason (int8).
    Disconnect = auto()
    # ObjectUpdate is sent using (NodeType uint16, OId ObjectID, Method uint8, *data)
    # this is sent when a user receives a signal that does not have the object in memory
    ObjectRequest = auto()
    ObjectResponse = auto()
    TransferOwner = auto()
    ZoneData = auto()


class KickReason(IntEnum):
    InvalidSignature = auto()
    InvalidObjectID = auto()
    InvalidConnectionRequest = auto()
    InvalidMessage = auto()
    PartialRequest = auto()
    HiddenZone = auto()
    PermissionDenied = auto()

    InvalidLogin = auto()
    DoubleLogin = auto()
