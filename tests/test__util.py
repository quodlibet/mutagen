# -*- coding: utf-8 -*-

from mutagen._util import DictMixin, cdata, insert_bytes, delete_bytes
from mutagen._util import decode_terminated, dict_match, enum, get_size
from mutagen._util import BitReader, BitReaderError, resize_bytes, seek_end
from mutagen._compat import text_type, itervalues, iterkeys, iteritems, PY2, \
    cBytesIO, xrange
from tests import TestCase
import random
import mmap

try:
    import fcntl
except ImportError:
    fcntl = None


class FDict(DictMixin):

    def __init__(self):
        self.__d = {}
        self.keys = self.__d.keys

    def __getitem__(self, *args):
        return self.__d.__getitem__(*args)

    def __setitem__(self, *args):
        return self.__d.__setitem__(*args)

    def __delitem__(self, *args):
        return self.__d.__delitem__(*args)


class TDictMixin(TestCase):

    def setUp(self):
        self.fdict = FDict()
        self.rdict = {}
        self.fdict["foo"] = self.rdict["foo"] = "bar"

    def test_getsetitem(self):
        self.failUnlessEqual(self.fdict["foo"], "bar")
        self.failUnlessRaises(KeyError, self.fdict.__getitem__, "bar")

    def test_has_key_contains(self):
        self.failUnless("foo" in self.fdict)
        self.failIf("bar" in self.fdict)
        if PY2:
            self.failUnless(self.fdict.has_key("foo"))
            self.failIf(self.fdict.has_key("bar"))

    def test_iter(self):
        self.failUnlessEqual(list(iter(self.fdict)), ["foo"])

    def test_clear(self):
        self.fdict.clear()
        self.rdict.clear()
        self.failIf(self.fdict)

    def test_keys(self):
        self.failUnlessEqual(list(self.fdict.keys()), list(self.rdict.keys()))
        self.failUnlessEqual(
            list(iterkeys(self.fdict)), list(iterkeys(self.rdict)))

    def test_values(self):
        self.failUnlessEqual(
            list(self.fdict.values()), list(self.rdict.values()))
        self.failUnlessEqual(
            list(itervalues(self.fdict)), list(itervalues(self.rdict)))

    def test_items(self):
        self.failUnlessEqual(
            list(self.fdict.items()), list(self.rdict.items()))
        self.failUnlessEqual(
            list(iteritems(self.fdict)), list(iteritems(self.rdict)))

    def test_pop(self):
        self.failUnlessEqual(self.fdict.pop("foo"), self.rdict.pop("foo"))
        self.failUnlessRaises(KeyError, self.fdict.pop, "woo")

    def test_pop_bad(self):
        self.failUnlessRaises(TypeError, self.fdict.pop, "foo", 1, 2)

    def test_popitem(self):
        self.failUnlessEqual(self.fdict.popitem(), self.rdict.popitem())
        self.failUnlessRaises(KeyError, self.fdict.popitem)

    def test_update_other(self):
        other = {"a": 1, "b": 2}
        self.fdict.update(other)
        self.rdict.update(other)

    def test_update_other_is_list(self):
        other = [("a", 1), ("b", 2)]
        self.fdict.update(other)
        self.rdict.update(dict(other))

    def test_update_kwargs(self):
        self.fdict.update(a=1, b=2)
        # Ironically, the *real* dict doesn't support this on Python 2.3
        other = {"a": 1, "b": 2}
        self.rdict.update(other)

    def test_setdefault(self):
        self.fdict.setdefault("foo", "baz")
        self.rdict.setdefault("foo", "baz")
        self.fdict.setdefault("bar", "baz")
        self.rdict.setdefault("bar", "baz")

    def test_get(self):
        self.failUnlessEqual(self.rdict.get("a"), self.fdict.get("a"))
        self.failUnlessEqual(
            self.rdict.get("a", "b"), self.fdict.get("a", "b"))
        self.failUnlessEqual(self.rdict.get("foo"), self.fdict.get("foo"))

    def test_repr(self):
        self.failUnlessEqual(repr(self.rdict), repr(self.fdict))

    def test_len(self):
        self.failUnlessEqual(len(self.rdict), len(self.fdict))

    def tearDown(self):
        self.failUnlessEqual(self.fdict, self.rdict)
        self.failUnlessEqual(self.rdict, self.fdict)


class Tcdata(TestCase):

    ZERO = staticmethod(lambda s: b"\x00" * s)
    LEONE = staticmethod(lambda s: b"\x01" + b"\x00" * (s - 1))
    BEONE = staticmethod(lambda s: b"\x00" * (s - 1) + b"\x01")
    NEGONE = staticmethod(lambda s: b"\xff" * s)

    def test_char(self):
        self.failUnlessEqual(cdata.char(self.ZERO(1)), 0)
        self.failUnlessEqual(cdata.char(self.LEONE(1)), 1)
        self.failUnlessEqual(cdata.char(self.BEONE(1)), 1)
        self.failUnlessEqual(cdata.char(self.NEGONE(1)), -1)
        self.assertTrue(cdata.char is cdata.int8)
        self.assertTrue(cdata.to_char is cdata.to_int8)
        self.assertTrue(cdata.char_from is cdata.int8_from)

    def test_char_from_to(self):
        self.assertEqual(cdata.to_char(-2), b"\xfe")
        self.assertEqual(cdata.char_from(b"\xfe"), (-2, 1))
        self.assertEqual(cdata.char_from(b"\x00\xfe", 1), (-2, 2))
        self.assertRaises(cdata.error, cdata.char_from, b"\x00\xfe", 3)

    def test_uchar(self):
        self.failUnlessEqual(cdata.uchar(self.ZERO(1)), 0)
        self.failUnlessEqual(cdata.uchar(self.LEONE(1)), 1)
        self.failUnlessEqual(cdata.uchar(self.BEONE(1)), 1)
        self.failUnlessEqual(cdata.uchar(self.NEGONE(1)), 255)
        self.assertTrue(cdata.uchar is cdata.uint8)
        self.assertTrue(cdata.to_uchar is cdata.to_uint8)
        self.assertTrue(cdata.uchar_from is cdata.uint8_from)

    def test_short(self):
        self.failUnlessEqual(cdata.short_le(self.ZERO(2)), 0)
        self.failUnlessEqual(cdata.short_le(self.LEONE(2)), 1)
        self.failUnlessEqual(cdata.short_le(self.BEONE(2)), 256)
        self.failUnlessEqual(cdata.short_le(self.NEGONE(2)), -1)
        self.assertTrue(cdata.short_le is cdata.int16_le)

        self.failUnlessEqual(cdata.short_be(self.ZERO(2)), 0)
        self.failUnlessEqual(cdata.short_be(self.LEONE(2)), 256)
        self.failUnlessEqual(cdata.short_be(self.BEONE(2)), 1)
        self.failUnlessEqual(cdata.short_be(self.NEGONE(2)), -1)
        self.assertTrue(cdata.short_be is cdata.int16_be)

    def test_ushort(self):
        self.failUnlessEqual(cdata.ushort_le(self.ZERO(2)), 0)
        self.failUnlessEqual(cdata.ushort_le(self.LEONE(2)), 1)
        self.failUnlessEqual(cdata.ushort_le(self.BEONE(2)), 2 ** 16 >> 8)
        self.failUnlessEqual(cdata.ushort_le(self.NEGONE(2)), 65535)
        self.assertTrue(cdata.ushort_le is cdata.uint16_le)

        self.failUnlessEqual(cdata.ushort_be(self.ZERO(2)), 0)
        self.failUnlessEqual(cdata.ushort_be(self.LEONE(2)), 2 ** 16 >> 8)
        self.failUnlessEqual(cdata.ushort_be(self.BEONE(2)), 1)
        self.failUnlessEqual(cdata.ushort_be(self.NEGONE(2)), 65535)
        self.assertTrue(cdata.ushort_be is cdata.uint16_be)

    def test_int(self):
        self.failUnlessEqual(cdata.int_le(self.ZERO(4)), 0)
        self.failUnlessEqual(cdata.int_le(self.LEONE(4)), 1)
        self.failUnlessEqual(cdata.int_le(self.BEONE(4)), 2 ** 32 >> 8)
        self.failUnlessEqual(cdata.int_le(self.NEGONE(4)), -1)
        self.assertTrue(cdata.int_le is cdata.int32_le)

        self.failUnlessEqual(cdata.int_be(self.ZERO(4)), 0)
        self.failUnlessEqual(cdata.int_be(self.LEONE(4)), 2 ** 32 >> 8)
        self.failUnlessEqual(cdata.int_be(self.BEONE(4)), 1)
        self.failUnlessEqual(cdata.int_be(self.NEGONE(4)), -1)
        self.assertTrue(cdata.int_be is cdata.int32_be)

    def test_uint(self):
        self.failUnlessEqual(cdata.uint_le(self.ZERO(4)), 0)
        self.failUnlessEqual(cdata.uint_le(self.LEONE(4)), 1)
        self.failUnlessEqual(cdata.uint_le(self.BEONE(4)), 2 ** 32 >> 8)
        self.failUnlessEqual(cdata.uint_le(self.NEGONE(4)), 2 ** 32 - 1)
        self.assertTrue(cdata.uint_le is cdata.uint32_le)

        self.failUnlessEqual(cdata.uint_be(self.ZERO(4)), 0)
        self.failUnlessEqual(cdata.uint_be(self.LEONE(4)), 2 ** 32 >> 8)
        self.failUnlessEqual(cdata.uint_be(self.BEONE(4)), 1)
        self.failUnlessEqual(cdata.uint_be(self.NEGONE(4)), 2 ** 32 - 1)
        self.assertTrue(cdata.uint_be is cdata.uint32_be)

    def test_longlong(self):
        self.failUnlessEqual(cdata.longlong_le(self.ZERO(8)), 0)
        self.failUnlessEqual(cdata.longlong_le(self.LEONE(8)), 1)
        self.failUnlessEqual(cdata.longlong_le(self.BEONE(8)), 2 ** 64 >> 8)
        self.failUnlessEqual(cdata.longlong_le(self.NEGONE(8)), -1)
        self.assertTrue(cdata.longlong_le is cdata.int64_le)

        self.failUnlessEqual(cdata.longlong_be(self.ZERO(8)), 0)
        self.failUnlessEqual(cdata.longlong_be(self.LEONE(8)), 2 ** 64 >> 8)
        self.failUnlessEqual(cdata.longlong_be(self.BEONE(8)), 1)
        self.failUnlessEqual(cdata.longlong_be(self.NEGONE(8)), -1)
        self.assertTrue(cdata.longlong_be is cdata.int64_be)

    def test_ulonglong(self):
        self.failUnlessEqual(cdata.ulonglong_le(self.ZERO(8)), 0)
        self.failUnlessEqual(cdata.ulonglong_le(self.LEONE(8)), 1)
        self.failUnlessEqual(cdata.longlong_le(self.BEONE(8)), 2 ** 64 >> 8)
        self.failUnlessEqual(cdata.ulonglong_le(self.NEGONE(8)), 2 ** 64 - 1)
        self.assertTrue(cdata.ulonglong_le is cdata.uint64_le)

        self.failUnlessEqual(cdata.ulonglong_be(self.ZERO(8)), 0)
        self.failUnlessEqual(cdata.ulonglong_be(self.LEONE(8)), 2 ** 64 >> 8)
        self.failUnlessEqual(cdata.longlong_be(self.BEONE(8)), 1)
        self.failUnlessEqual(cdata.ulonglong_be(self.NEGONE(8)), 2 ** 64 - 1)
        self.assertTrue(cdata.ulonglong_be is cdata.uint64_be)

    def test_invalid_lengths(self):
        self.failUnlessRaises(cdata.error, cdata.char, b"")
        self.failUnlessRaises(cdata.error, cdata.uchar, b"")
        self.failUnlessRaises(cdata.error, cdata.int_le, b"")
        self.failUnlessRaises(cdata.error, cdata.longlong_le, b"")
        self.failUnlessRaises(cdata.error, cdata.uint_le, b"")
        self.failUnlessRaises(cdata.error, cdata.ulonglong_le, b"")
        self.failUnlessRaises(cdata.error, cdata.int_be, b"")
        self.failUnlessRaises(cdata.error, cdata.longlong_be, b"")
        self.failUnlessRaises(cdata.error, cdata.uint_be, b"")
        self.failUnlessRaises(cdata.error, cdata.ulonglong_be, b"")

    def test_test(self):
        self.failUnless(cdata.test_bit((1), 0))
        self.failIf(cdata.test_bit(1, 1))

        self.failUnless(cdata.test_bit(2, 1))
        self.failIf(cdata.test_bit(2, 0))

        v = (1 << 12) + (1 << 5) + 1
        self.failUnless(cdata.test_bit(v, 0))
        self.failUnless(cdata.test_bit(v, 5))
        self.failUnless(cdata.test_bit(v, 12))
        self.failIf(cdata.test_bit(v, 3))
        self.failIf(cdata.test_bit(v, 8))
        self.failIf(cdata.test_bit(v, 13))


class FileHandling(TestCase):
    def file(self, contents):
        import tempfile
        temp = tempfile.TemporaryFile()
        temp.write(contents)
        temp.flush()
        temp.seek(0)
        return temp

    def read(self, fobj):
        fobj.seek(0, 0)
        return fobj.read()

    def test_resize_decrease(self):
        o = self.file(b'abcd')
        resize_bytes(o, 2, 1, 1)
        self.assertEqual(self.read(o), b"abd")

    def test_resize_increase(self):
        o = self.file(b'abcd')
        resize_bytes(o, 2, 4, 1)
        self.assertEqual(self.read(o), b"abcd\x00d")

    def test_resize_nothing(self):
        o = self.file(b'abcd')
        resize_bytes(o, 2, 2, 1)
        self.assertEqual(self.read(o), b"abcd")

    def test_insert_into_empty(self):
        o = self.file(b'')
        insert_bytes(o, 8, 0)
        self.assertEquals(b'\x00' * 8, self.read(o))

    def test_insert_before_one(self):
        o = self.file(b'a')
        insert_bytes(o, 8, 0)
        self.assertEquals(b'a' + b'\x00' * 7 + b'a', self.read(o))

    def test_insert_after_one(self):
        o = self.file(b'a')
        insert_bytes(o, 8, 1)
        self.assertEquals(b'a' + b'\x00' * 8, self.read(o))

    def test_smaller_than_file_middle(self):
        o = self.file(b'abcdefghij')
        insert_bytes(o, 4, 4)
        self.assertEquals(b'abcdefghefghij', self.read(o))

    def test_smaller_than_file_to_end(self):
        o = self.file(b'abcdefghij')
        insert_bytes(o, 4, 6)
        self.assertEquals(b'abcdefghijghij', self.read(o))

    def test_smaller_than_file_across_end(self):
        o = self.file(b'abcdefghij')
        insert_bytes(o, 4, 8)
        self.assertEquals(b'abcdefghij\x00\x00ij', self.read(o))

    def test_smaller_than_file_at_end(self):
        o = self.file(b'abcdefghij')
        insert_bytes(o, 3, 10)
        self.assertEquals(b'abcdefghij\x00\x00\x00', self.read(o))

    def test_smaller_than_file_at_beginning(self):
        o = self.file(b'abcdefghij')
        insert_bytes(o, 3, 0)
        self.assertEquals(b'abcabcdefghij', self.read(o))

    def test_zero(self):
        o = self.file(b'abcdefghij')
        self.assertRaises((AssertionError, ValueError), insert_bytes, o, 0, 1)

    def test_negative(self):
        o = self.file(b'abcdefghij')
        self.assertRaises((AssertionError, ValueError), insert_bytes, o, 8, -1)

    def test_delete_one(self):
        o = self.file(b'a')
        delete_bytes(o, 1, 0)
        self.assertEquals(b'', self.read(o))

    def test_delete_first_of_two(self):
        o = self.file(b'ab')
        delete_bytes(o, 1, 0)
        self.assertEquals(b'b', self.read(o))

    def test_delete_second_of_two(self):
        o = self.file(b'ab')
        delete_bytes(o, 1, 1)
        self.assertEquals(b'a', self.read(o))

    def test_delete_third_of_two(self):
        o = self.file(b'ab')
        self.assertRaises(AssertionError, delete_bytes, o, 1, 2)

    def test_delete_middle(self):
        o = self.file(b'abcdefg')
        delete_bytes(o, 3, 2)
        self.assertEquals(b'abfg', self.read(o))

    def test_delete_across_end(self):
        o = self.file(b'abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 4, 8)

    def test_delete_zero(self):
        o = self.file(b'abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 0, 3)

    def test_delete_negative(self):
        o = self.file(b'abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 4, -8)

    def test_insert_6106_79_51760(self):
        # This appears to be due to ANSI C limitations in read/write on rb+
        # files. The problematic behavior only showed up in our mmap fallback
        # code for transfers of this or similar sizes.
        data = u''.join(map(text_type, xrange(12574)))  # 51760 bytes
        data = data.encode("ascii")
        o = self.file(data)
        insert_bytes(o, 6106, 79)
        self.failUnless(data[:6106 + 79] + data[79:] == self.read(o))

    def test_delete_6106_79_51760(self):
        # This appears to be due to ANSI C limitations in read/write on rb+
        # files. The problematic behavior only showed up in our mmap fallback
        # code for transfers of this or similar sizes.
        data = u''.join(map(text_type, xrange(12574)))  # 51760 bytes
        data = data.encode("ascii")
        o = self.file(data[:6106 + 79] + data[79:])
        delete_bytes(o, 6106, 79)
        self.failUnless(data == self.read(o))

    # Generate a bunch of random insertions, apply them, delete them,
    # and make sure everything is still correct.
    #
    # The num_runs and num_changes values are tuned to take about 10s
    # on my laptop, or about 30 seconds since we we have 3 variations
    # on insert/delete_bytes brokenness. If I ever get a faster
    # laptop, it's probably a good idea to increase them. :)
    def test_many_changes(self, num_runs=5, num_changes=300,
                          min_change_size=500, max_change_size=1000,
                          min_buffer_size=1, max_buffer_size=2000):
        self.failUnless(min_buffer_size < min_change_size and
                        max_buffer_size > max_change_size and
                        min_change_size < max_change_size and
                        min_buffer_size < max_buffer_size,
                        "Given testing parameters make this test useless")
        for j in xrange(num_runs):
            data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 1024
            fobj = self.file(data)
            filesize = len(data)
            # Generate the list of changes to apply
            changes = []
            for i in xrange(num_changes):
                change_size = random.randrange(
                    min_change_size, max_change_size)
                change_offset = random.randrange(0, filesize)
                filesize += change_size
                changes.append((change_offset, change_size))

            # Apply the changes, and make sure they all took.
            for offset, size in changes:
                buffer_size = random.randrange(
                    min_buffer_size, max_buffer_size)
                insert_bytes(fobj, size, offset, BUFFER_SIZE=buffer_size)
            fobj.seek(0)
            self.failIfEqual(fobj.read(len(data)), data)
            fobj.seek(0, 2)
            self.failUnlessEqual(fobj.tell(), filesize)

            # Then, undo them.
            changes.reverse()
            for offset, size in changes:
                buffer_size = random.randrange(
                    min_buffer_size, max_buffer_size)
                delete_bytes(fobj, size, offset, BUFFER_SIZE=buffer_size)
            fobj.seek(0)
            self.failUnless(fobj.read() == data)


class FileHandlingMockedMMapMove(FileHandling):

    def setUp(self):
        class MockMMap(object):
            def __init__(self, *args, **kwargs):
                pass

            def move(self, dest, src, count):
                raise ValueError

            def close(self):
                pass

        self._orig_mmap = mmap.mmap
        mmap.mmap = MockMMap

    def tearDown(self):
        mmap.mmap = self._orig_mmap


class FileHandlingMockedMMap(FileHandling):

    def setUp(self):
        def MockMMap2(*args, **kwargs):
            raise EnvironmentError

        self._orig_mmap = mmap.mmap
        mmap.mmap = MockMMap2

    def tearDown(self):
        mmap.mmap = self._orig_mmap


class Tdict_match(TestCase):

    def test_match(self):
        self.assertEqual(dict_match({"*": 1}, "a"), 1)
        self.assertEqual(dict_match({"*": 1}, "*"), 1)
        self.assertEqual(dict_match({"*a": 1}, "ba"), 1)
        self.assertEqual(dict_match({"?": 1}, "b"), 1)
        self.assertEqual(dict_match({"[ab]": 1}, "b"), 1)

    def test_nomatch(self):
        self.assertEqual(dict_match({"*a": 1}, "ab"), None)
        self.assertEqual(dict_match({"??": 1}, "a"), None)
        self.assertEqual(dict_match({"[ab]": 1}, "c"), None)
        self.assertEqual(dict_match({"[ab]": 1}, "[ab]"), None)


class Tenum(TestCase):

    def test_enum(self):
        @enum
        class Foo(object):
            FOO = 1
            BAR = 3

        self.assertEqual(Foo.FOO, 1)
        self.assertTrue(isinstance(Foo.FOO, Foo))
        self.assertEqual(repr(Foo.FOO), "<Foo.FOO: 1>")
        self.assertEqual(repr(Foo(3)), "<Foo.BAR: 3>")
        self.assertEqual(repr(Foo(42)), "42")
        self.assertEqual(str(Foo(42)), "42")
        self.assertEqual(int(Foo(42)), 42)
        self.assertEqual(str(Foo(1)), "Foo.FOO")
        self.assertEqual(int(Foo(1)), 1)

        self.assertTrue(isinstance(str(Foo.FOO), str))
        self.assertTrue(isinstance(repr(Foo.FOO), str))


class Tseek_end(TestCase):

    def file(self, contents):
        import tempfile
        temp = tempfile.TemporaryFile()
        temp.write(contents)
        temp.flush()
        temp.seek(0)
        return temp

    def test_seek_end(self):
        with self.file(b"foo") as f:
            seek_end(f, 2)
            self.assertEqual(f.tell(), 1)
            seek_end(f, 3)
            self.assertEqual(f.tell(), 0)
            seek_end(f, 4)
            self.assertEqual(f.tell(), 0)
            seek_end(f, 0)
            self.assertEqual(f.tell(), 3)
            self.assertRaises(ValueError, seek_end, f, -1)

    def test_seek_end_pos(self):
        with self.file(b"foo") as f:
            f.seek(10)
            seek_end(f, 10)
            self.assertEqual(f.tell(), 0)


class Tget_size(TestCase):

    def test_get_size(self):
        f = cBytesIO(b"foo")
        f.seek(1, 0)
        self.assertEqual(f.tell(), 1)
        self.assertEqual(get_size(f), 3)
        self.assertEqual(f.tell(), 1)


class Tdecode_terminated(TestCase):

    def test_all(self):
        values = [u"", u"", u"\xe4", u"abc", u"", u""]

        for codec in ["utf8", "utf-8", "utf-16", "latin-1", "utf-16be"]:
            # NULL without the BOM
            term = u"\x00".encode(codec)[-2:]
            data = b"".join(v.encode(codec) + term for v in values)

            for v in values:
                dec, data = decode_terminated(data, codec)
                self.assertEqual(dec, v)
            self.assertEqual(data, b"")

    def test_invalid(self):
        # invalid
        self.assertRaises(
            UnicodeDecodeError, decode_terminated, b"\xff", "utf-8")
        # truncated
        self.assertRaises(
            UnicodeDecodeError, decode_terminated, b"\xff\xfe\x00", "utf-16")
        # not null terminated
        self.assertRaises(ValueError, decode_terminated, b"abc", "utf-8")
        # invalid encoding
        self.assertRaises(LookupError, decode_terminated, b"abc", "foobar")

    def test_lax(self):
        # missing termination
        self.assertEqual(
            decode_terminated(b"abc", "utf-8", strict=False), (u"abc", b""))

        # missing termination and truncated data
        truncated = u"\xe4\xe4".encode("utf-8")[:-1]
        self.assertRaises(
            UnicodeDecodeError, decode_terminated,
            truncated, "utf-8", strict=False)


class TBitReader(TestCase):

    def test_bits(self):
        data = b"\x12\x34\x56\x78\x89\xAB\xCD\xEF"
        ref = cdata.uint64_be(data)

        for i in xrange(64):
            fo = cBytesIO(data)
            r = BitReader(fo)
            v = r.bits(i) << (64 - i) | r.bits(64 - i)
            self.assertEqual(v, ref)

    def test_read_too_much(self):
        r = BitReader(cBytesIO(b""))
        self.assertEqual(r.bits(0), 0)
        self.assertRaises(BitReaderError, r.bits, 1)

    def test_skip(self):
        r = BitReader(cBytesIO(b"\xEF"))
        r.skip(4)
        self.assertEqual(r.bits(4), 0xf)

    def test_skip_more(self):
        r = BitReader(cBytesIO(b"\xAB\xCD"))
        self.assertEqual(r.bits(4), 0xa)
        r.skip(8)
        self.assertEqual(r.bits(4), 0xd)
        self.assertRaises(BitReaderError, r.bits, 1)

    def test_skip_too_much(self):
        r = BitReader(cBytesIO(b"\xAB\xCD"))
        # aligned skips don't fail, but the following read will
        r.skip(32 + 8)
        self.assertRaises(BitReaderError, r.bits, 1)
        self.assertRaises(BitReaderError, r.skip, 1)

    def test_bytes(self):
        r = BitReader(cBytesIO(b"\xAB\xCD\xEF"))
        self.assertEqual(r.bytes(2), b"\xAB\xCD")
        self.assertEqual(r.bytes(0), b"")

    def test_bytes_unaligned(self):
        r = BitReader(cBytesIO(b"\xAB\xCD\xEF"))
        r.skip(4)
        self.assertEqual(r.bytes(2), b"\xBC\xDE")

    def test_get_position(self):
        r = BitReader(cBytesIO(b"\xAB\xCD"))
        self.assertEqual(r.get_position(), 0)
        r.bits(3)
        self.assertEqual(r.get_position(), 3)
        r.skip(9)
        self.assertEqual(r.get_position(), 3 + 9)
        r.align()
        self.assertEqual(r.get_position(), 16)

    def test_align(self):
        r = BitReader(cBytesIO(b"\xAB\xCD\xEF"))
        r.skip(3)
        self.assertEqual(r.align(), 5)
        self.assertEqual(r.get_position(), 8)

    def test_is_aligned(self):
        r = BitReader(cBytesIO(b"\xAB\xCD\xEF"))
        self.assertTrue(r.is_aligned())

        r.skip(1)
        self.assertFalse(r.is_aligned())
        r.skip(7)
        self.assertTrue(r.is_aligned())

        r.bits(7)
        self.assertFalse(r.is_aligned())
        r.bits(1)
        self.assertTrue(r.is_aligned())
