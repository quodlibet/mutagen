from mutagen._util import DictMixin, cdata, utf8, insert_bytes, delete_bytes
from tests import TestCase, add
import mmap
import random

class FDict(DictMixin):
    uses_mmap = False

    def __init__(self):
        self.__d = {}
        self.keys = self.__d.keys

    def __getitem__(self, *args): return self.__d.__getitem__(*args)
    def __setitem__(self, *args): return self.__d.__setitem__(*args)
    def __delitem__(self, *args): return self.__d.__delitem__(*args)

class Tutf8(TestCase):
    uses_mmap = False

    def test_str(self):
        value = utf8("1234")
        self.failUnlessEqual(value, "1234")
        self.failUnless(isinstance(value, str))

    def test_bad_str(self):
        value = utf8("\xab\xde")
        # Two '?' symbols.
        self.failUnlessEqual(value, "\xef\xbf\xbd\xef\xbf\xbd")
        self.failUnless(isinstance(value, str))

    def test_low_unicode(self):
        value = utf8(u"1234")
        self.failUnlessEqual(value, "1234")
        self.failUnless(isinstance(value, str))

    def test_high_unicode(self):
        value = utf8(u"\u1234")
        self.failUnlessEqual(value, '\xe1\x88\xb4')
        self.failUnless(isinstance(value, str))

    def test_invalid(self):
        self.failUnlessRaises(TypeError, utf8, 1234)

add(Tutf8)

class TDictMixin(TestCase):
    uses_mmap = False

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
            list(self.fdict.iterkeys()), list(self.rdict.iterkeys()))

    def test_values(self):
        self.failUnlessEqual(
            list(self.fdict.values()), list(self.rdict.values()))
        self.failUnlessEqual(
            list(self.fdict.itervalues()), list(self.rdict.itervalues()))

    def test_items(self):
        self.failUnlessEqual(
            list(self.fdict.items()), list(self.rdict.items()))
        self.failUnlessEqual(
            list(self.fdict.iteritems()), list(self.rdict.iteritems()))

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

add(TDictMixin)

class Tcdata(TestCase):
    uses_mmap = False

    ZERO = "\x00\x00\x00\x00"
    LEONE = "\x01\x00\x00\x00"
    BEONE = "\x00\x00\x00\x01"
    NEGONE = "\xff\xff\xff\xff"

    def test_int_le(self):
        self.failUnlessEqual(cdata.int_le(self.ZERO), 0)
        self.failUnlessEqual(cdata.int_le(self.LEONE), 1)
        self.failUnlessEqual(cdata.int_le(self.BEONE), 16777216)
        self.failUnlessEqual(cdata.int_le(self.NEGONE), -1)

    def test_uint_le(self):
        self.failUnlessEqual(cdata.uint_le(self.ZERO), 0)
        self.failUnlessEqual(cdata.uint_le(self.LEONE), 1)
        self.failUnlessEqual(cdata.uint_le(self.BEONE), 16777216)
        self.failUnlessEqual(cdata.uint_le(self.NEGONE), 2**32-1)

    def test_longlong_le(self):
        self.failUnlessEqual(cdata.longlong_le(self.ZERO * 2), 0)
        self.failUnlessEqual(cdata.longlong_le(self.LEONE + self.ZERO), 1)
        self.failUnlessEqual(cdata.longlong_le(self.NEGONE * 2), -1)

    def test_ulonglong_le(self):
        self.failUnlessEqual(cdata.ulonglong_le(self.ZERO * 2), 0)
        self.failUnlessEqual(cdata.ulonglong_le(self.LEONE + self.ZERO), 1)
        self.failUnlessEqual(cdata.ulonglong_le(self.NEGONE * 2), 2**64-1)

    def test_invalid_lengths(self):
        self.failUnlessRaises(cdata.error, cdata.int_le, "")
        self.failUnlessRaises(cdata.error, cdata.longlong_le, "")
        self.failUnlessRaises(cdata.error, cdata.uint_le, "")
        self.failUnlessRaises(cdata.error, cdata.ulonglong_le, "")

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

add(Tcdata)

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

    def test_insert_into_empty(self):
        o = self.file('')
        insert_bytes(o, 8, 0)
        self.assertEquals('\x00' * 8, self.read(o))

    def test_insert_before_one(self):
        o = self.file('a')
        insert_bytes(o, 8, 0)
        self.assertEquals('a' + '\x00' * 7 + 'a', self.read(o))

    def test_insert_after_one(self):
        o = self.file('a')
        insert_bytes(o, 8, 1)
        self.assertEquals('a' + '\x00' * 8, self.read(o))

    def test_smaller_than_file_middle(self):
        o = self.file('abcdefghij')
        insert_bytes(o, 4, 4)
        self.assertEquals('abcdefghefghij', self.read(o))

    def test_smaller_than_file_to_end(self):
        o = self.file('abcdefghij')
        insert_bytes(o, 4, 6)
        self.assertEquals('abcdefghijghij', self.read(o))

    def test_smaller_than_file_across_end(self):
        o = self.file('abcdefghij')
        insert_bytes(o, 4, 8)
        self.assertEquals('abcdefghij\x00\x00ij', self.read(o))

    def test_smaller_than_file_at_end(self):
        o = self.file('abcdefghij')
        insert_bytes(o, 3, 10)
        self.assertEquals('abcdefghij\x00\x00\x00', self.read(o))

    def test_smaller_than_file_at_beginning(self):
        o = self.file('abcdefghij')
        insert_bytes(o, 3, 0)
        self.assertEquals('abcabcdefghij', self.read(o))

    def test_zero(self):
        o = self.file('abcdefghij')
        self.assertRaises((AssertionError, ValueError), insert_bytes, o, 0, 1)

    def test_negative(self):
        o = self.file('abcdefghij')
        self.assertRaises((AssertionError, ValueError), insert_bytes, o, 8, -1)

    def test_delete_one(self):
        o = self.file('a')
        delete_bytes(o, 1, 0)
        self.assertEquals('', self.read(o))

    def test_delete_first_of_two(self):
        o = self.file('ab')
        delete_bytes(o, 1, 0)
        self.assertEquals('b', self.read(o))

    def test_delete_second_of_two(self):
        o = self.file('ab')
        delete_bytes(o, 1, 1)
        self.assertEquals('a', self.read(o))

    def test_delete_third_of_two(self):
        o = self.file('ab')
        self.assertRaises(AssertionError, delete_bytes, o, 1, 2)

    def test_delete_middle(self):
        o = self.file('abcdefg')
        delete_bytes(o, 3, 2)
        self.assertEquals('abfg', self.read(o))

    def test_delete_across_end(self):
        o = self.file('abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 4, 8)

    def test_delete_zero(self):
        o = self.file('abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 0, 3)

    def test_delete_negative(self):
        o = self.file('abcdefg')
        self.assertRaises(AssertionError, delete_bytes, o, 4, -8)

    def test_insert_6106_79_51760(self):
        # This appears to be due to ANSI C limitations in read/write on rb+
        # files. The problematic behavior only showed up in our mmap fallback
        # code for transfers of this or similar sizes. 
        data = ''.join(map(str, range(12574))) # 51760 bytes
        o = self.file(data)
        insert_bytes(o, 6106, 79)
        self.failUnless(data[:6106+79] + data[79:] == self.read(o))

    def test_delete_6106_79_51760(self):
        # This appears to be due to ANSI C limitations in read/write on rb+
        # files. The problematic behavior only showed up in our mmap fallback
        # code for transfers of this or similar sizes. 
        data = ''.join(map(str, range(12574))) # 51760 bytes
        o = self.file(data[:6106+79] + data[79:])
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
        for j in range(num_runs):
            data = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 1024
            fobj = self.file(data)
            filesize = len(data)
            # Generate the list of changes to apply
            changes = []
            for i in range(num_changes):
                change_size = random.randrange(min_change_size, max_change_size)
                change_offset = random.randrange(0, filesize)
                filesize += change_size
                changes.append((change_offset, change_size))

            # Apply the changes, and make sure they all took.
            for offset, size in changes:
                buffer_size = random.randrange(min_buffer_size, max_buffer_size)
                insert_bytes(fobj, size, offset, BUFFER_SIZE=buffer_size)
            fobj.seek(0)
            self.failIfEqual(fobj.read(len(data)), data)
            fobj.seek(0, 2)
            self.failUnlessEqual(fobj.tell(), filesize)

            # Then, undo them.
            changes.reverse()
            for offset, size in changes:
                buffer_size = random.randrange(min_buffer_size, max_buffer_size)
                delete_bytes(fobj, size, offset, BUFFER_SIZE=buffer_size)
            fobj.seek(0)
            self.failUnless(fobj.read() == data)

add(FileHandling)
