from tests import TestCase, add

from mutagen.id3 import BitPaddedInt


class SpecSanityChecks(TestCase):

    def test_bytespec(self):
        from mutagen.id3 import ByteSpec
        s = ByteSpec('name')
        self.assertEquals((97, 'bcdefg'), s.read(None, 'abcdefg'))
        self.assertEquals('a', s.write(None, 97))
        self.assertRaises(TypeError, s.write, None, 'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_encodingspec(self):
        from mutagen.id3 import EncodingSpec
        s = EncodingSpec('name')
        self.assertEquals((0, 'abcdefg'), s.read(None, 'abcdefg'))
        self.assertEquals((3, 'abcdefg'), s.read(None, '\x03abcdefg'))
        self.assertEquals('\x00', s.write(None, 0))
        self.assertRaises(TypeError, s.write, None, 'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_stringspec(self):
        from mutagen.id3 import StringSpec
        s = StringSpec('name', 3)
        self.assertEquals(('abc', 'defg'),  s.read(None, 'abcdefg'))
        self.assertEquals('abc', s.write(None, 'abcdefg'))
        self.assertEquals('\x00\x00\x00', s.write(None, None))
        self.assertEquals('\x00\x00\x00', s.write(None, '\x00'))
        self.assertEquals('a\x00\x00', s.write(None, 'a'))

    def test_binarydataspec(self):
        from mutagen.id3 import BinaryDataSpec
        s = BinaryDataSpec('name')
        self.assertEquals(('abcdefg', ''), s.read(None, 'abcdefg'))
        self.assertEquals('None',  s.write(None, None))
        self.assertEquals('43',  s.write(None, 43))

    def test_encodedtextspec(self):
        from mutagen.id3 import EncodedTextSpec, Frame
        s = EncodedTextSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals(('abcd', 'fg'), s.read(f, 'abcd\x00fg'))
        self.assertEquals('abcdefg\x00', s.write(f, 'abcdefg'))
        self.assertRaises(AttributeError, s.write, f, None)

    def test_timestampspec(self):
        from mutagen.id3 import TimeStampSpec, Frame, ID3TimeStamp
        s = TimeStampSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals((ID3TimeStamp('ab'), 'fg'), s.read(f, 'ab\x00fg'))
        self.assertEquals((ID3TimeStamp('1234'), ''), s.read(f, '1234\x00'))
        self.assertEquals('1234\x00', s.write(f, ID3TimeStamp('1234')))
        self.assertRaises(AttributeError, s.write, f, None)

    def test_volumeadjustmentspec(self):
        from mutagen.id3 import VolumeAdjustmentSpec
        s = VolumeAdjustmentSpec('gain')
        self.assertEquals((0.0, ''), s.read(None, '\x00\x00'))
        self.assertEquals((2.0, ''), s.read(None, '\x04\x00'))
        self.assertEquals((-2.0, ''), s.read(None, '\xfc\x00'))
        self.assertEquals('\x00\x00', s.write(None, 0.0))
        self.assertEquals('\x04\x00', s.write(None, 2.0))
        self.assertEquals('\xfc\x00', s.write(None, -2.0))

add(SpecSanityChecks)


class NoHashSpec(TestCase):

    def test_spec(self):
        from mutagen.id3 import Spec
        self.failUnlessRaises(TypeError, {}.__setitem__, Spec("foo"), None)

add(NoHashSpec)


class BitPaddedIntTest(TestCase):

    def test_zero(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x00'), 0)

    def test_1(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x01'), 1)

    def test_1l(self):
        self.assertEquals(BitPaddedInt('\x01\x00\x00\x00', bigendian=False), 1)

    def test_129(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x01'), 0x81)

    def test_129b(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81'), 0x81)

    def test_65(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81', 6), 0x41)

    def test_32b(self):
        self.assertEquals(BitPaddedInt('\xFF\xFF\xFF\xFF', bits=8),
            0xFFFFFFFF)

    def test_32bi(self):
        self.assertEquals(BitPaddedInt(0xFFFFFFFF, bits=8), 0xFFFFFFFF)

    def test_s32b(self):
        self.assertEquals(BitPaddedInt('\xFF\xFF\xFF\xFF', bits=8).as_str(),
            '\xFF\xFF\xFF\xFF')

    def test_s0(self):
        self.assertEquals(BitPaddedInt.to_str(0), '\x00\x00\x00\x00')

    def test_s1(self):
        self.assertEquals(BitPaddedInt.to_str(1), '\x00\x00\x00\x01')

    def test_s1l(self):
        self.assertEquals(
            BitPaddedInt.to_str(1, bigendian=False), '\x01\x00\x00\x00')

    def test_s129(self):
        self.assertEquals(BitPaddedInt.to_str(129), '\x00\x00\x01\x01')

    def test_s65(self):
        self.assertEquals(BitPaddedInt.to_str(0x41, 6), '\x00\x00\x01\x01')

    def test_w129(self):
        self.assertEquals(BitPaddedInt.to_str(129, width=2), '\x01\x01')

    def test_w129l(self):
        self.assertEquals(
            BitPaddedInt.to_str(129, width=2, bigendian=False), '\x01\x01')

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

add(BitPaddedIntTest)
