import sys

from tests import TestCase, add

from mutagen._compat import PY2, PY3, text_type
from mutagen.id3 import BitPaddedInt


class SpecSanityChecks(TestCase):

    def test_bytespec(self):
        from mutagen.id3 import ByteSpec
        s = ByteSpec('name')
        self.assertEquals((97, b'bcdefg'), s.read(None, b'abcdefg'))
        self.assertEquals(b'a', s.write(None, 97))
        self.assertRaises(TypeError, s.write, None, b'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_encodingspec(self):
        from mutagen.id3 import EncodingSpec
        s = EncodingSpec('name')
        self.assertEquals((0, b'abcdefg'), s.read(None, b'abcdefg'))
        self.assertEquals((3, b'abcdefg'), s.read(None, b'\x03abcdefg'))
        self.assertEquals(b'\x00', s.write(None, 0))
        self.assertRaises(TypeError, s.write, None, b'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_stringspec(self):
        from mutagen.id3 import StringSpec
        s = StringSpec('name', 3)
        self.assertEquals((b'abc', b'defg'),  s.read(None, b'abcdefg'))
        self.assertEquals(b'abc', s.write(None, b'abcdefg'))
        self.assertEquals(b'\x00\x00\x00', s.write(None, None))
        self.assertEquals(b'\x00\x00\x00', s.write(None, b'\x00'))
        self.assertEquals(b'a\x00\x00', s.write(None, b'a'))

    def test_binarydataspec(self):
        from mutagen.id3 import BinaryDataSpec
        s = BinaryDataSpec('name')
        self.assertEquals((b'abcdefg', b''), s.read(None, b'abcdefg'))
        self.assertEquals(b'',  s.write(None, None))
        self.assertEquals(b'43',  s.write(None, 43))
        self.assertEquals(b'abc',  s.write(None, b'abc'))

    def test_encodedtextspec(self):
        from mutagen.id3 import EncodedTextSpec, Frame
        s = EncodedTextSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals((u'abcd', b'fg'), s.read(f, b'abcd\x00fg'))
        self.assertEquals(b'abcdefg\x00', s.write(f, u'abcdefg'))
        self.assertRaises(AttributeError, s.write, f, None)

    def test_timestampspec(self):
        from mutagen.id3 import TimeStampSpec, Frame, ID3TimeStamp
        s = TimeStampSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals((ID3TimeStamp('ab'), b'fg'), s.read(f, b'ab\x00fg'))
        self.assertEquals((ID3TimeStamp('1234'), b''), s.read(f, b'1234\x00'))
        self.assertEquals(b'1234\x00', s.write(f, ID3TimeStamp('1234')))
        self.assertRaises(AttributeError, s.write, f, None)
        if PY3:
            self.assertRaises(TypeError, ID3TimeStamp, b"blah")
        self.assertEquals(
            text_type(ID3TimeStamp(u"2000-01-01")),  u"2000-01-01")
        self.assertEquals(
            bytes(ID3TimeStamp(u"2000-01-01")), b"2000-01-01")

    def test_volumeadjustmentspec(self):
        from mutagen.id3 import VolumeAdjustmentSpec
        s = VolumeAdjustmentSpec('gain')
        self.assertEquals((0.0, b''), s.read(None, b'\x00\x00'))
        self.assertEquals((2.0, b''), s.read(None, b'\x04\x00'))
        self.assertEquals((-2.0, b''), s.read(None, b'\xfc\x00'))
        self.assertEquals(b'\x00\x00', s.write(None, 0.0))
        self.assertEquals(b'\x04\x00', s.write(None, 2.0))
        self.assertEquals(b'\xfc\x00', s.write(None, -2.0))

    def test_synchronizedtextspec(self):
        from mutagen.id3 import SynchronizedTextSpec, Frame
        s = SynchronizedTextSpec('name')
        f = Frame()

        values = [(u"A", 100), (u"\xe4xy", 0), (u"", 42), (u"", 0)]

        # utf-16
        f.encoding = 1
        self.assertEqual(s.read(f, s.write(f, values)), (values, b""))
        self.assertEquals(
            s.write(f, [(u"A", 100)]), b"\xff\xfeA\x00\x00\x00\x00\x00\x00d")

        # utf-16be
        f.encoding = 2
        self.assertEqual(s.read(f, s.write(f, values)), (values, b""))
        self.assertEquals(
            s.write(f, [(u"A", 100)]), b"\x00A\x00\x00\x00\x00\x00d")

        # utf-8
        f.encoding = 3
        self.assertEqual(s.read(f, s.write(f, values)), (values, b""))
        self.assertEquals(s.write(f, [(u"A", 100)]), b"A\x00\x00\x00\x00d")


add(SpecSanityChecks)


class SpecValidateChecks(TestCase):

    def test_volumeadjustmentspec(self):
        from mutagen.id3 import VolumeAdjustmentSpec
        s = VolumeAdjustmentSpec('gain')
        self.assertRaises(ValueError, s.validate, None, 65)

    def test_volumepeakspec(self):
        from mutagen.id3 import VolumePeakSpec
        s = VolumePeakSpec('peak')
        self.assertRaises(ValueError, s.validate, None, 2)

    def test_bytespec(self):
        from mutagen.id3 import ByteSpec
        s = ByteSpec('byte')
        self.assertRaises(ValueError, s.validate, None, 1000)

add(SpecValidateChecks)


class NoHashSpec(TestCase):

    def test_spec(self):
        from mutagen.id3 import Spec
        self.failUnlessRaises(TypeError, {}.__setitem__, Spec("foo"), None)

add(NoHashSpec)


class BitPaddedIntTest(TestCase):

    def test_zero(self):
        self.assertEquals(BitPaddedInt(b'\x00\x00\x00\x00'), 0)

    def test_1(self):
        self.assertEquals(BitPaddedInt(b'\x00\x00\x00\x01'), 1)

    def test_1l(self):
        self.assertEquals(BitPaddedInt(b'\x01\x00\x00\x00', bigendian=False), 1)

    def test_129(self):
        self.assertEquals(BitPaddedInt(b'\x00\x00\x01\x01'), 0x81)

    def test_129b(self):
        self.assertEquals(BitPaddedInt(b'\x00\x00\x01\x81'), 0x81)

    def test_65(self):
        self.assertEquals(BitPaddedInt(b'\x00\x00\x01\x81', 6), 0x41)

    def test_32b(self):
        self.assertEquals(BitPaddedInt(b'\xFF\xFF\xFF\xFF', bits=8),
            0xFFFFFFFF)

    def test_32bi(self):
        self.assertEquals(BitPaddedInt(0xFFFFFFFF, bits=8), 0xFFFFFFFF)

    def test_s32b(self):
        self.assertEquals(BitPaddedInt(b'\xFF\xFF\xFF\xFF', bits=8).as_str(),
            b'\xFF\xFF\xFF\xFF')

    def test_s0(self):
        self.assertEquals(BitPaddedInt.to_str(0), b'\x00\x00\x00\x00')

    def test_s1(self):
        self.assertEquals(BitPaddedInt.to_str(1), b'\x00\x00\x00\x01')

    def test_s1l(self):
        self.assertEquals(
            BitPaddedInt.to_str(1, bigendian=False), b'\x01\x00\x00\x00')

    def test_s129(self):
        self.assertEquals(BitPaddedInt.to_str(129), b'\x00\x00\x01\x01')

    def test_s65(self):
        self.assertEquals(BitPaddedInt.to_str(0x41, 6), b'\x00\x00\x01\x01')

    def test_w129(self):
        self.assertEquals(BitPaddedInt.to_str(129, width=2), b'\x01\x01')

    def test_w129l(self):
        self.assertEquals(
            BitPaddedInt.to_str(129, width=2, bigendian=False), b'\x01\x01')

    def test_wsmall(self):
        self.assertRaises(ValueError, BitPaddedInt.to_str, 129, width=1)

    def test_str_int_init(self):
        from struct import pack
        self.assertEquals(BitPaddedInt(238).as_str(),
                BitPaddedInt(pack('>L', 238)).as_str())

    def test_varwidth(self):
        self.assertEquals(len(BitPaddedInt.to_str(100)), 4)
        self.assertEquals(len(BitPaddedInt.to_str(100, width=-1)), 4)
        self.assertEquals(len(BitPaddedInt.to_str(2**32, width=-1)), 5)

    def test_minwidth(self):
        self.assertEquals(
            len(BitPaddedInt.to_str(100, width=-1, minwidth=6)), 6)

    def test_inval_input(self):
        self.assertRaises(TypeError, BitPaddedInt, None)

    if PY2:
        def test_promote_long(self):
            l = BitPaddedInt(sys.maxint ** 2)
            self.assertTrue(isinstance(l, long))
            self.assertEqual(BitPaddedInt(l.as_str(width=-1)), l)

    def test_has_valid_padding(self):
        self.failUnless(BitPaddedInt.has_valid_padding(b"\xff\xff", bits=8))
        self.failIf(BitPaddedInt.has_valid_padding(b"\xff"))
        self.failIf(BitPaddedInt.has_valid_padding(b"\x00\xff"))
        self.failUnless(BitPaddedInt.has_valid_padding(b"\x7f\x7f"))
        self.failIf(BitPaddedInt.has_valid_padding(b"\x7f", bits=6))
        self.failIf(BitPaddedInt.has_valid_padding(b"\x9f", bits=6))
        self.failUnless(BitPaddedInt.has_valid_padding(b"\x3f", bits=6))

        self.failUnless(BitPaddedInt.has_valid_padding(0xff, bits=8))
        self.failIf(BitPaddedInt.has_valid_padding(0xff))
        self.failIf(BitPaddedInt.has_valid_padding(0xff << 8))
        self.failUnless(BitPaddedInt.has_valid_padding(0x7f << 8))
        self.failIf(BitPaddedInt.has_valid_padding(0x9f << 32, bits=6))
        self.failUnless(BitPaddedInt.has_valid_padding(0x3f << 16, bits=6))

add(BitPaddedIntTest)


class TestUnsynch(TestCase):

    def test_unsync_encode(self):
        from mutagen.id3 import unsynch as un
        for d in (b'\xff\xff\xff\xff', b'\xff\xf0\x0f\x00', b'\xff\x00\x0f\xf0'):
            self.assertEquals(d, un.decode(un.encode(d)))
            self.assertNotEqual(d, un.encode(d))
        self.assertEquals(b'\xff\x44', un.encode(b'\xff\x44'))
        self.assertEquals(b'\xff\x00\x00', un.encode(b'\xff\x00'))

    def test_unsync_decode(self):
        from mutagen.id3 import unsynch as un
        self.assertRaises(ValueError, un.decode, b'\xff\xff\xff\xff')
        self.assertRaises(ValueError, un.decode, b'\xff\xf0\x0f\x00')
        self.assertRaises(ValueError, un.decode, b'\xff\xe0')
        self.assertRaises(ValueError, un.decode, b'\xff')
        self.assertEquals(b'\xff\x44', un.decode(b'\xff\x44'))

add(TestUnsynch)
