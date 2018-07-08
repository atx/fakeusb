

import enum
import collections
import struct


# TODO
___all__ = [
    "Header"
]


# See usb-redirection-protocol.txt for description of the structures

class T(enum.Enum):
    U8 = (b"B", 1)
    U16 = (b"H", 2)
    U32 = (b"I", 4)

    def __init__(self, format_, raw_length):
        self._format = format_
        self.raw_length = raw_length


class Status(enum.IntEnum):
    Success = 0
    Cancelled = 1
    Inval = 2
    Ioerror = 3
    Stall = 4
    Timeout = 5
    Babble = 6


class Capabilities(enum.IntEnum):
    BulkStreams = 0
    ConnectDeviceVersion = 1
    Filter = 2
    DeviceDisconnectAck = 3
    EpInfoMaxPacketSize = 4
    Bits64Ids = 5
    Bits32BulkLength = 6
    BulkReceiving = 7


class Types(enum.IntEnum):
    Hello = 0
    DeviceConnect = 1
    DeviceDisconnect = 2
    Reset = 3
    InterfaceInfo = 4
    EpInfo = 5
    SetConfiguration = 6
    GetConfiguration = 7
    ConfigurationStatus = 8
    SetAltSetting = 9
    GetAltSetting = 10
    AltSettingStatus = 11
    StartIsoStream = 12
    StopIsoStream = 13
    IsoStreamStatus = 14
    StartInterruptReceiving = 15
    StopInterruptReceiving = 16
    InterruptReceivingStatus = 17
    AllocBulkStreams = 18
    FreeBulkStreams = 19
    BulkStreamsStatus = 20
    CancelDataPacket = 21
    FilterReject = 22
    FilterFilter = 23
    DeviceDisconnectAck = 24
    StartBulkReceiving = 25
    StopBulkReceiving = 26
    BulkReceivingStatus = 27

    ControlPacket = 100
    BulkPacket = 101
    IsoPacket = 102
    InterruptPacket = 103
    BufferedBulkPacket = 104


type_registry = dict()


class Meta(type):

    @classmethod
    def __prepare__(self, name, bases):
        # Guarantees class attribute ordering
        return collections.OrderedDict()

    def __new__(meta, class_name, bases, dict_):
        fields = []
        dict_["_final"] = None
        dict_["_final_ann"] = None
        if "__annotations__" in dict_:
            raw_length = 0
            anns = dict_["__annotations__"]
            fmt = b""
            for name, ann in anns.items():
                if not hasattr(ann, "raw_length"):
                    continue
                assert getattr(ann, "_final", None) is None, "Nested variable length elements are forbidden"
                assert dict_["_final"] is None, "A variable length element can be only at the end"
                fields.append((name, ann))
                if ann.raw_length != 0:
                    fmt += ann._format
                    raw_length += ann.raw_length
                else:
                    dict_["_final"] = name
                    dict_["_final_ann"] = ann

            # TODO: Can we do __slots__ here somehow?
            # usbredir does not specify endianness, expects host byte order
            dict_["raw_length"] = raw_length
            dict_["_format"] = fmt
            dict_["_struct"] = struct.Struct(b"=" + fmt)

        dict_["_fields"] = tuple(fields)
        return super().__new__(meta, class_name, bases, dict_)

    def __init__(class_, name, bases, dict_):
        if hasattr(class_, "type_id"):
            type_registry[class_.type_id] = class_
        return super().__init__(name, bases, dict_)


class Base(metaclass=Meta):

    def __init__(self, **kwargs):
        for name, _ in self._fields:
            val = None
            if name in kwargs:
                val = kwargs[name]
            elif hasattr(type(self), name):
                val = getattr(type(self), name)
            else:
                raise KeyError("Expected attribute '{}' not found in kwargs!".format(name))
            setattr(self, name, val)

    @property
    def raw_values(self):
        """Returns flattened representation of this object."""
        # TODO: Make the objects immutable and cache this
        direct = [getattr(self, name) for name, _ in self._fields]
        ret = []
        for val in direct:
            if hasattr(val, "raw_values"):
                ret.extend(val.raw_values)
            else:
                ret.append(val)
        return ret

    @classmethod
    def _make_self(class_, vals, extra_val=None):
        kwargs = dict()
        for name, ann in class_._fields:
            if ann.raw_length == 0:
                assert name == class_._final, "Only the last member can be of variable length!"
                kwargs[name] = extra_val
            elif hasattr(ann, "_make_self"):
                kwargs[name] = ann._make_self(vals)
            else:
                kwargs[name] = vals.pop(0)
        return class_(**kwargs)

    @classmethod
    def unserialize(class_, bs):
        if not class_._fields:
            return class_()

        vals = list(class_._struct.unpack(bs[:class_.raw_length]))
        if len(bs) > class_.raw_length:
            extra_val = class_._final_ann.variable_unserialize(bs[class_.raw_length:])
            return class_._make_self(vals, extra_val=extra_val)
        return class_._make_self(vals)

    def serialize(self):
        if not self._fields:
            return b""
        vals = []
        for name, ann in self._fields:
            if name == self._final:
                continue  # This should be the final iteration
            attr = getattr(self, name)
            if hasattr(attr, "raw_values"):
                vals.extend(attr.raw_values)
            elif isinstance(attr, collections.Iterable):
                vals.extend(iter(attr))
            else:
                vals.append(attr)

        bs = self._struct.pack(*vals)

        if self._final:
            bs += self._final_ann.variable_serialize(getattr(self, self._final))

        return bs

    def __str__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            ", ".join(name + " = " + str(getattr(self, name))
                      for name, ann in self._fields)
        )
    __repr__ = __str__


def Array(type_, length_=0):

    class Array:

        length = length_
        raw_length = length * type_.raw_length
        _type = type_

        if length:
            _format = type_._format * length
            _struct = struct.Struct(b"=" + _format)

        def __init__(self, values):
            raise ValueError("This class is not supposed to be instantiated, use plain tuples instead")

        @classmethod
        def _make_self(class_, vals):
            ret = vals[:class_.length]
            for _ in range(class_.length):
                vals.pop(0)
            return ret

        @classmethod
        def variable_unserialize(class_, bs):
            if len(bs) % class_._type.raw_length != 0:
                raise ValueError("Byte count not evenly divisible by type size")

            count = len(bs) // class_._type.raw_length
            fmt = b"=" + class_._type._format*count
            vals = list(struct.unpack(fmt, bs))
            if hasattr(class_._type, "_make_self"):
                new_vals = []
                while vals:
                    new_vals.append(class_._type._make_self(vals))
                vals = new_vals
            return tuple(vals)

        @classmethod
        def variable_serialize(class_, vals):
            if hasattr(class_._type, "serialize"):
                # TODO: Check if this is at least reasonably fast...
                output = b""
                for val in vals:
                    output += val.serialize()
                return output
            else:
                # TODO: Cache these?
                fmt = (b"=" + class_._type._format*len(vals))
                return struct.pack(fmt, *vals)

    return Array


class Header(Base):
    type_: T.U32
    length: T.U32
    id_: T.U32


class Hello(Base):
    type_id = 0

    version: Array(T.U8, 64)
    capabilities: Array(T.U32, 0)


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


class CancelDataPacket(Base):
    type_id = 21


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