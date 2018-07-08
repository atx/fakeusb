
import pytest

import fakeusb.protocol as p


class SimplePacket(p.Base):
    alpha: p.T.U8
    beta: p.T.U16
    gamma: p.T.U32


def test_simple_init():
    assert SimplePacket.raw_length == 1 + 2 + 4
    p = SimplePacket(alpha=1, beta=2, gamma=3)
    assert p.alpha == 1 and p.beta == 2 and p.gamma == 3


def test_require_all_params():
    with pytest.raises(KeyError):
        SimplePacket(alpha=1, beta=2)


def test_simple_serialization():
    p = SimplePacket(alpha=1, beta=0x7700, gamma=0x112233)
    # Assuming little-endian packing
    print(p._struct.format)
    assert p.serialize() == bytes([0x01, 0x00, 0x77, 0x33, 0x22, 0x11, 0x00])


def test_simple_unserialization():
    bs = bytes([0x01, 0x00, 0x77, 0x33, 0x22, 0x11, 0x00])
    p = SimplePacket.unserialize(bs)
    assert p.alpha == 1 and p.beta == 0x7700 and p.gamma == 0x112233


def test_simple_derive():
    a = SimplePacket(alpha=1, beta=0x7700, gamma=0x112233)
    b = a.derive(beta=123)
    assert b.alpha == a.alpha and b.beta == 123 and b.gamma == a.gamma


class ZeroLengthPacket(p.Base):
    pass


def test_zero_length_serialize():
    p = ZeroLengthPacket()
    assert p.serialize() == b""


def test_zero_length_unserialize():
    # Ugh, what do we even test for here?
    ZeroLengthPacket.unserialize(b"")


class NestedPacket(p.Base):
    one: p.T.U16
    nested: SimplePacket
    two: p.T.U8


def test_nested_init():
    assert NestedPacket.raw_length == 2 + SimplePacket.raw_length + 1
    p = NestedPacket(
        one=1,
        nested=SimplePacket(alpha=1, beta=2, gamma=3),
        two=4,
    )
    assert p.one == 1 and p.two == 4
    assert p.nested.alpha == 1 and p.nested.beta == 2 and p.nested.gamma == 3


def test_nested_require_all_params():
    with pytest.raises(KeyError):
        NestedPacket(one=1, two=2)


def test_nested_serialization():
    p = NestedPacket(
        one=1,
        nested=SimplePacket(alpha=1, beta=2, gamma=0xff),
        two=4,
    )
    assert p.serialize() == bytes([
        0x01, 0x00,
        0x01, 0x02, 0x00,  0xff, 0x00, 0x00, 0x00,
        0x04
    ])


def test_nested_unserialization():
    bs = bytes([
        0x01, 0x00,
        0x01, 0x02, 0x00,  0xff, 0x00, 0x00, 0x00,
        0x04
    ])
    print(bs)
    p = NestedPacket.unserialize(bs)
    assert p.one == 1 and p.two == 4
    assert p.nested.alpha == 1 and p.nested.beta == 2 and p.nested.gamma == 0xff


class ArrayPacket(p.Base):
    one: p.T.U16
    arr: p.Array(p.T.U8, 8)
    two: p.T.U8


def test_array_length():
    assert ArrayPacket.raw_length == 2 + 8 + 1


def test_array_serialize():
    p = ArrayPacket(
        one=0xabcd,
        arr=list(range(8)),
        two=0xbb,
    )
    assert p.serialize() == bytes([
        0xcd, 0xab,
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0xbb
    ])


def test_array_unserialize():
    bs = bytes([
        0xcd, 0xab,
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0xbb
    ])
    p = ArrayPacket.unserialize(bs)
    assert p.one == 0xabcd and p.two == 0xbb
    assert p.arr == list(range(8))


class ArrayVariablePacket(p.Base):
    one: p.T.U8
    two: p.T.U32
    arr: p.Array(p.T.U16)


def test_variable_array_serialize():
    p = ArrayVariablePacket(
        one=0x66,
        two=0x3311,
        arr=[1, 2, 3, 4, 5]
    )
    assert ArrayVariablePacket.raw_length == 5
    assert p.serialize() == bytes([
        0x66,
        0x11, 0x33, 0x00, 0x00,
        0x01, 0x00,  0x02, 0x00,  0x03, 0x00,  0x04, 0x00,  0x05, 0x00
    ])


def test_variable_array_unserialize():
    bs = bytes([
        0x66,
        0x11, 0x33, 0x00, 0x00,
        0x01, 0x00,  0x02, 0x00,  0x03, 0x00,  0x04, 0x00,  0x05, 0x00
    ])
    p = ArrayVariablePacket.unserialize(bs)
    assert p.one == 0x66 and p.two == 0x3311
    assert p.arr == (1, 2, 3, 4, 5)


class ArrayVarNontrivialPacket(p.Base):
    one: p.T.U32
    two: p.T.U8
    arr: p.Array(SimplePacket)


def test_variable_nontrivial_serialize():
    p = ArrayVarNontrivialPacket(
        one=0xaabb1233,
        two=0x11,
        arr=[
            SimplePacket(alpha=0x12, beta=0xcc33, gamma=0x003100a1),
            SimplePacket(alpha=0x31, beta=0x1065, gamma=0x44a1aa12),
            SimplePacket(alpha=0xe2, beta=0x31f1, gamma=0x2733111b),
        ]
    )
    assert p.raw_length == 5
    assert p.serialize() == bytes([
        0x33, 0x12, 0xbb, 0xaa,
        0x11,
        0x12,  0x33, 0xcc,  0xa1, 0x00, 0x31, 0x00,
        0x31,  0x65, 0x10,  0x12, 0xaa, 0xa1, 0x44,
        0xe2,  0xf1, 0x31,  0x1b, 0x11, 0x33, 0x27,
    ])


def test_variable_nontrivial_unserialize():
    bs = bytes([
        0x33, 0x12, 0xbb, 0xaa,
        0x11,
        0x12,  0x33, 0xcc,  0xa1, 0x00, 0x31, 0x00,
        0x31,  0x65, 0x10,  0x12, 0xaa, 0xa1, 0x44,
        0xe2,  0xf1, 0x31,  0x1b, 0x11, 0x33, 0x27,
    ])
    p = ArrayVarNontrivialPacket.unserialize(bs)
    assert p.one == 0xaabb1233 and p.two == 0x11
    print(p.arr)
    assert len(p.arr) == 3


class DefaultPacket(p.Base):
    alpha: p.T.U16 = 0xa0
    beta: p.T.U8
    gamma: p.T.U8 = 0x11


def test_default_init():
    p = DefaultPacket(alpha=0x44, beta=0x99)
    assert p.alpha == 0x44 and p.beta == 0x99 and p.gamma == 0x11
