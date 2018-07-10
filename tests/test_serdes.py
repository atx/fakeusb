

import pytest

from fakeusb.serdes import Array, Base, T


class TestSimple:

    class Packet(Base):
        alpha: T.U8
        beta: T.U16
        gamma: T.U32

    def test_init(self):
        assert TestSimple.Packet.raw_length == 1 + 2 + 4
        p = TestSimple.Packet(alpha=1, beta=2, gamma=3)
        assert p.alpha == 1 and p.beta == 2 and p.gamma == 3

    def test_require_all_params(self):
        with pytest.raises(KeyError):
            TestSimple.Packet(alpha=1, beta=2)

    def test_simple_serialization(self):
        p = TestSimple.Packet(alpha=1, beta=0x7700, gamma=0x112233)
        # Assuming little-endian packing
        print(p._struct.format)
        assert p.serialize() == bytes([0x01, 0x00, 0x77, 0x33, 0x22, 0x11, 0x00])

    def test_unserialization(self):
        bs = bytes([0x01, 0x00, 0x77, 0x33, 0x22, 0x11, 0x00])
        p = TestSimple.Packet.unserialize(bs)
        assert p.alpha == 1 and p.beta == 0x7700 and p.gamma == 0x112233

    def test_derive(self):
        a = TestSimple.Packet(alpha=1, beta=0x7700, gamma=0x112233)
        b = a.derive(beta=123)
        assert b.alpha == a.alpha and b.beta == 123 and b.gamma == a.gamma


class TestZeroLength:

    class Packet(Base):
        pass

    def test_serialize(self):
        p = TestZeroLength.Packet()
        assert p.serialize() == b""

    def test_zero_length_unserialize(self):
        # Ugh, what do we even test for here?
        TestZeroLength.Packet.unserialize(b"")


class TestNested:

    class Packet(Base):
        one: T.U16
        nested: TestSimple.Packet
        two: T.U8

    def test_init(self):
        assert TestNested.Packet.raw_length == 2 + TestSimple.Packet.raw_length + 1
        p = TestNested.Packet(
            one=1,
            nested=TestSimple.Packet(alpha=1, beta=2, gamma=3),
            two=4,
        )
        assert p.one == 1 and p.two == 4
        assert p.nested.alpha == 1 and p.nested.beta == 2 and p.nested.gamma == 3

    def test_nested_require_all_params(self):
        with pytest.raises(KeyError):
            TestNested.Packet(one=1, two=2)

    def test_nested_serialization(self):
        p = TestNested.Packet(
            one=1,
            nested=TestSimple.Packet(alpha=1, beta=2, gamma=0xff),
            two=4,
        )
        assert p.serialize() == bytes([
            0x01, 0x00,
            0x01, 0x02, 0x00,  0xff, 0x00, 0x00, 0x00,
            0x04
        ])

    def test_nested_unserialization(self):
        bs = bytes([
            0x01, 0x00,
            0x01, 0x02, 0x00,  0xff, 0x00, 0x00, 0x00,
            0x04
        ])
        p = TestNested.Packet.unserialize(bs)
        assert p.one == 1 and p.two == 4
        assert p.nested.alpha == 1 and p.nested.beta == 2 and p.nested.gamma == 0xff


class TestArray:

    class Packet(Base):
        one: T.U16
        arr: Array(T.U8, 8)
        two: T.U8

    def test_array_length(self):
        assert TestArray.Packet.raw_length == 2 + 8 + 1

    def test_array_serialize(self):
        p = TestArray.Packet(
            one=0xabcd,
            arr=list(range(8)),
            two=0xbb,
        )
        assert p.serialize() == bytes([
            0xcd, 0xab,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0xbb
        ])

    def test_array_unserialize(self):
        bs = bytes([
            0xcd, 0xab,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0xbb
        ])
        p = TestArray.Packet.unserialize(bs)
        assert p.one == 0xabcd and p.two == 0xbb
        assert p.arr == list(range(8))


class TestVariable:

    class ArrayPacket(Base):
        one: T.U8
        two: T.U32
        arr: Array(T.U16)

    def test_serialize(self):
        p = TestVariable.ArrayPacket(
            one=0x66,
            two=0x3311,
            arr=[1, 2, 3, 4, 5]
        )
        assert TestVariable.ArrayPacket.is_variable
        assert TestVariable.ArrayPacket.raw_length == 5
        assert p.serialize() == bytes([
            0x66,
            0x11, 0x33, 0x00, 0x00,
            0x01, 0x00,  0x02, 0x00,  0x03, 0x00,  0x04, 0x00,  0x05, 0x00
        ])

    def test_unserialize(self):
        bs = bytes([
            0x66,
            0x11, 0x33, 0x00, 0x00,
            0x01, 0x00,  0x02, 0x00,  0x03, 0x00,  0x04, 0x00,  0x05, 0x00
        ])
        p = TestVariable.ArrayPacket.unserialize(bs)
        assert p.one == 0x66 and p.two == 0x3311
        assert p.arr == (1, 2, 3, 4, 5)

    class OnlyArrayPacket(Base):
        arr: Array(T.U16)

    def test_only_serialize(self):
        p = TestVariable.OnlyArrayPacket(
            arr=[4, 3, 2, 1]
        )
        assert TestVariable.OnlyArrayPacket.raw_length == 0
        assert p.serialize() == bytes([
            0x04, 0x00,  0x03, 0x00,  0x02, 0x00,  0x01, 0x00
        ])

    def test_only_unserialize(self):
        bs = bytes([
            0x04, 0x00,  0x03, 0x00,  0x02, 0x00,  0x01, 0x00
        ])
        p = TestVariable.OnlyArrayPacket.unserialize(bs)
        assert p.arr == (4, 3, 2, 1)

    class ArrayNontrivialPacket(Base):
        one: T.U32
        two: T.U8
        arr: Array(TestSimple.Packet)

    def test_nontrivial_serialize(self):
        p = TestVariable.ArrayNontrivialPacket(
            one=0xaabb1233,
            two=0x11,
            arr=[
                TestSimple.Packet(alpha=0x12, beta=0xcc33, gamma=0x003100a1),
                TestSimple.Packet(alpha=0x31, beta=0x1065, gamma=0x44a1aa12),
                TestSimple.Packet(alpha=0xe2, beta=0x31f1, gamma=0x2733111b),
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

    def test_nontrivial_unserialize(self):
        bs = bytes([
            0x33, 0x12, 0xbb, 0xaa,
            0x11,
            0x12,  0x33, 0xcc,  0xa1, 0x00, 0x31, 0x00,
            0x31,  0x65, 0x10,  0x12, 0xaa, 0xa1, 0x44,
            0xe2,  0xf1, 0x31,  0x1b, 0x11, 0x33, 0x27,
        ])
        p = TestVariable.ArrayNontrivialPacket.unserialize(bs)
        assert p.one == 0xaabb1233 and p.two == 0x11
        print(p.arr)
        assert len(p.arr) == 3

    class MultipleVariablePacket(Base):
        one: T.U8
        arr1: Array(T.U8)
        arr2: Array(T.U16)

    def test_multiple_serialize(self):
        p = TestVariable.MultipleVariablePacket(
            one=0x11,
            arr1=[1, 2, 3],
            arr2=[0x33, 0x44, 0x55]
        )
        assert p.serialize() == bytes([
            0x11,
            0x01, 0x02, 0x03,
            0x33, 0x00,  0x44, 0x00,  0x55, 0x00
        ])


class TestDefault:

    class Packet(Base):
        alpha: T.U16 = 0xa0
        beta: T.U8
        gamma: T.U8 = 0x11

    def test_init(self):
        p = TestDefault.Packet(alpha=0x44, beta=0x99)
        assert p.alpha == 0x44 and p.beta == 0x99 and p.gamma == 0x11
