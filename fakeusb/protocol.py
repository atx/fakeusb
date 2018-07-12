

import enum

from fakeusb.serdes import Array, Base, T


__all__ = [
    "Status",
    "Header", "Hello", "DeviceConnect", "DeviceDisconnect", "Reset",
    "InterfaceInfo", "EpInfo", "SetConfiguration", "GetConfiguration",
    "ConfigurationStatus", "CancelDataPacket",
    "ControlPacket", "BulkPacket"
]


# See usb-redirection-protocol.txt for description of the structures

class Status(enum.IntEnum):
    SUCCESS = 0
    CANCELLED = 1
    INVAL = 2
    IOERROR = 3
    STALL = 4
    TIMEOUT = 5
    BABBLE = 6


class Header(Base):
    type_: T.U32
    length: T.U32
    id_: T.U32


class Hello(Base):
    type_id = 0

    version: Array(T.U8, 64)
    capabilities: Array(T.U32)


class DeviceConnect(Base):
    type_id = 1

    class Speed:
        LOW = 0
        FULL = 1
        HIGH = 2
        SUPER = 4
        UNKNOWN = 255

    speed: T.U8
    device_class: T.U8
    device_subclass: T.U8
    device_protocol: T.U8
    vendor_id: T.U16
    product_id: T.U16
    #device_version_bcd: T.U16


class DeviceDisconnect(Base):
    type_id = 2


class Reset(Base):
    type_id = 3


class InterfaceInfo(Base):
    type_id = 4

    interface_count: T.U32
    interface: Array(T.U8, 32)
    interface_class: Array(T.U8, 32)
    interface_subclass: Array(T.U8, 32)
    interface_protocol: Array(T.U8, 32)


class EpInfo(Base):
    type_id = 5

    class Type:
        CONTROL = 0
        ISO = 1
        BULK = 2
        INTERRUPT = 3
        INVALID = 255

    type_: Array(T.U8, 32)
    interval: Array(T.U8, 32)
    interface: Array(T.U8, 32)


class SetConfiguration(Base):
    type_id = 6

    configuration: T.U8


class GetConfiguration(Base):
    type_id = 7


class ConfigurationStatus(Base):
    type_id = 8

    status: T.U8
    configuration: T.U8


class SetAltSetting(Base):
    type_id = 9

    interface: T.U8
    alt: T.U8


class GetAltSetting(Base):
    type_id = 10

    interface: T.U8


class AltSettingStatus(Base):
    type_id = 11

    status: T.U8
    interface: T.U8
    alt: T.U8


class StartIsoStream(Base):
    type_id = 12

    endpoint: T.U8
    pkts_per_urb: T.U8
    no_urbs: T.U8


class StopIsoStream(Base):
    type_id = 13

    endpoint: T.U8


class IsoStreamStatus(Base):
    type_id = 14

    status: T.U8
    endpoint: T.U8


class StartInterruptReceiving(Base):
    type_id = 15

    endpoint: T.U8


class StopInterruptReceiving(Base):
    type_id = 16

    endpoint: T.U8


class InterruptReceivingStatus(Base):
    type_id = 17

    status: T.U8
    endpoint: T.U8


class AllocBulkStreams(Base):
    type_id = 18

    endpoints: T.U32
    no_streams: T.U32


class FreeBulkStreams(Base):
    type_id = 19

    endpoints: T.U32


class BulkStreamsStatus(Base):
    type_id = 20

    endpoints: T.U32
    no_streams: T.U32
    status: T.U8


class CancelDataPacket(Base):
    type_id = 21


class FilterReject(Base):
    type_id = 22


class FilterFilter(Base):
    type_id = 23

    string: Array(T.U8)


class DeviceDisconnectAck(Base):
    type_id = 24


class StartBulkReceiving(Base):
    type_id = 25

    stream_id: T.U32
    bytes_per_transfer: T.U32
    endpoint: T.U8
    no_transfers: T.U8


class StopBulkReceiving(Base):
    type_id = 26

    stream_id: T.U32
    endpoint: T.U8


class BulkReceivingStatus(Base):
    type_id = 27

    stream_id: T.U32
    endpoint: T.U8
    status: T.U8


class ControlPacket(Base):
    type_id = 100

    endpoint: T.U8
    request: T.U8
    request_type: T.U8
    status: T.U8
    value: T.U16
    index: T.U16
    length: T.U16
    data: Array(T.U8)


class BulkPacket(Base):
    type_id = 101

    endpoint: T.U8
    status: T.U8
    length: T.U16
    stream_id: T.U32
    data: Array(T.U8)


class IsoPacket(Base):
    type_id = 102

    endpoint: T.U8
    status: T.U8
    length: T.U16
    data: Array(T.U8)


class InterruptPacket(Base):
    type_id = 103

    endpoint: T.U8
    status: T.U8
    length: T.U16
    data: Array(T.U8)


class BufferedBulkPacket(Base):
    type_id = 104

    stream_id: T.U32
    length: T.U32
    endpoint: T.U8
    status: T.U8
    data: Array(T.U8)
