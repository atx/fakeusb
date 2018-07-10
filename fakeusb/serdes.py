

import collections
import enum
import struct


__all__ = [
    "T", "Base", "Array"
]


# See usb-redirection-protocol.txt for description of the structures

class T(enum.Enum):
    U8 = (b"B", 1)
    U16 = (b"H", 2)
    U32 = (b"I", 4)

    def __init__(self, format_, raw_length):
        self._format = format_
        self.raw_length = raw_length
        self.is_variable = False


class Meta(type):

    @classmethod
    def __prepare__(self, name, bases):
        # Guarantees class attribute ordering
        return collections.OrderedDict()

    def __new__(meta, class_name, bases, dict_):
        fields = []
        trailers = []
        if "__annotations__" in dict_:
            raw_length = 0
            anns = dict_["__annotations__"]
            fmt = b""
            for name, ann in anns.items():
                if not hasattr(ann, "raw_length"):
                    continue
                pair = name, ann
                if ann.is_variable:
                    trailers.append(pair)
                else:
                    if trailers:
                        print(fields, trailers, name, ann)
                        raise TypeError("A constant-length element in a variable trailer is not allowed")
                    fields.append(pair)
                    fmt += ann._format
                    raw_length += ann.raw_length

            # TODO: Can we do __slots__ here somehow?
            # usbredir does not specify endianness, expects host byte order
            dict_["raw_length"] = raw_length
            dict_["_format"] = fmt
            dict_["_struct"] = struct.Struct(b"=" + fmt)
        else:
            # We are in a zero-length packet (or Base)
            pass

        dict_["_fields"] = tuple(fields)
        dict_["_trailers"] = tuple(trailers)
        dict_["_all_fields"] = tuple(fields + trailers)
        dict_["is_variable"] = bool(trailers)
        dict_["is_empty"] = not (fields or trailers)
        return super().__new__(meta, class_name, bases, dict_)

    def __init__(class_, name, bases, dict_):
        return super().__init__(name, bases, dict_)


class Base(metaclass=Meta):

    def __init__(self, **kwargs):
        for name, _ in self._all_fields:
            val = None
            if name in kwargs:
                val = kwargs[name]
                del kwargs[name]
            elif hasattr(type(self), name):
                val = getattr(type(self), name)
            else:
                raise KeyError("Expected attribute '{}' not found in kwargs!".format(name))
            super().__setattr__(name, val)
        if kwargs:
            raise KeyError("Extraneous constructor arguments {}".format(kwargs))

    def derive(self, **kwargs):
        merged_kwargs = {
            name: getattr(self, name) for name, _ in self._fields
        }
        merged_kwargs.update(kwargs)
        return type(self)(**merged_kwargs)

    def __setattr__(self, name, val):
        raise AttributeError("Can't set attribute")

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
    def _make_self(class_, vals, trailer_vals=[]):
        kwargs = dict()
        for name, ann in class_._fields:
            if hasattr(ann, "_make_self"):
                kwargs[name] = ann._make_self(vals)
            else:
                kwargs[name] = vals.pop(0)

        if class_.is_variable or trailer_vals:
            if len(trailer_vals) != len(class_._trailers):
                print(class_)
                print(class_._trailers)
                raise ValueError("Unexpected trailer_vals value {}".format(trailer_vals))

            for (name, ann), val in zip(class_._trailers, trailer_vals):
                kwargs[name] = val

        return class_(**kwargs)

    @classmethod
    def unserialize(class_, bs):
        if class_.is_empty:
            return class_()

        vals = list(class_._struct.unpack(bs[:class_.raw_length]))

        if class_._trailers:
            if len(class_._trailers) > 1:
                # TODO
                raise TypeError("Unserialization not supported for types with multiple trailers")
            extra_val = class_._trailers[0][1].variable_unserialize(bs[class_.raw_length:])
            return class_._make_self(vals, trailer_vals=[extra_val])
        return class_._make_self(vals)

    def serialize(self):
        if self.is_empty:
            return b""
        vals = []
        for name, ann in self._fields:
            attr = getattr(self, name)
            if hasattr(attr, "raw_values"):
                vals.extend(attr.raw_values)
            elif isinstance(attr, collections.Iterable):
                vals.extend(iter(attr))
            else:
                vals.append(attr)

        bs = self._struct.pack(*vals)

        for name, ann in self._trailers:
            bs += ann.variable_serialize(getattr(self, name))

        return bs

    def __str__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            ", ".join(name + " = " + str(getattr(self, name))
                      for name, ann in self._fields)
        )
    __repr__ = __str__


def Array(type_, length_=None):
    # TODO: Test for type_ = None

    class Array:

        _type = type_
        is_variable = not length_

        if length_:
            length = length_
            raw_length = length * _type.raw_length

        else:
            length = 0
            raw_length = 0

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
            if not bs:
                return tuple()

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
            if class_._type is None or hasattr(class_._type, "serialize"):
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
