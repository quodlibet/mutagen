import os
import sys
import shutil
from tests import add, TestCase
from mutagen.easyid3 import EasyID3, error as ID3Error, delete
from tempfile import mkstemp

class TEasyID3(TestCase):

    def setUp(self):
        fd, self.filename = mkstemp('.mp3')
        os.close(fd)
        empty = os.path.join('tests', 'data', 'emptyfile.mp3')
        shutil.copy(empty, self.filename)
        self.id3 = EasyID3()

    def test_delete(self):
        self.id3["artist"] = "foobar"
        self.id3.save(self.filename)
        self.failUnless(os.path.getsize(self.filename))
        self.id3.delete(self.filename)
        self.failIf(os.path.getsize(self.filename))
        self.failIf(self.id3)

    def test_pprint(self):
        self.id3["artist"] = "baz"
        self.id3.pprint()

    def test_has_key(self):
        self.failIf(self.id3.has_key("foo"))

    def test_empty_file(self):
        empty = os.path.join('tests', 'data', 'emptyfile.mp3')
        self.assertRaises(ID3Error, EasyID3, filename=empty)

    def test_nonexistent_file(self):
        empty = os.path.join('tests', 'data', 'does', 'not', 'exist')
        self.assertRaises(IOError, EasyID3, filename=empty)

    def test_write_single(self):
        for key in EasyID3.valid_keys:
            if key == "date": continue

            # Test creation
            self.id3[key] = "a test value"
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.failUnlessEqual(id3[key], ["a test value"])
            self.failUnlessEqual(id3.keys(), [key])

            # And non-creation setting.
            self.id3[key] = "a test value"
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.failUnlessEqual(id3[key], ["a test value"])
            self.failUnlessEqual(id3.keys(), [key])

            del(self.id3[key])

    def test_write_double(self):
        for key in EasyID3.valid_keys:
            if key == "date": continue

            self.id3[key] = ["a test", "value"]
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.failUnlessEqual(id3.get(key), ["a test", "value"])
            self.failUnlessEqual(id3.keys(), [key])

            self.id3[key] = ["a test", "value"]
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.failUnlessEqual(id3.get(key), ["a test", "value"])
            self.failUnlessEqual(id3.keys(), [key])

            del(self.id3[key])

    def test_write_date(self):
        self.id3["date"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(self.id3["date"], ["2004"])

        self.id3["date"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(self.id3["date"], ["2004"])

    def test_write_date_double(self):
        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(self.id3["date"], ["2004", "2005"])

        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(self.id3["date"], ["2004", "2005"])

    def test_write_invalid(self):
        self.failUnlessRaises(ValueError, self.id3.__getitem__, "notvalid")
        self.failUnlessRaises(ValueError, self.id3.__delitem__, "notvalid")
        self.failUnlessRaises(
            ValueError, self.id3.__setitem__, "notvalid", "tests")

    def tearDown(self):
        os.unlink(self.filename)

add(TEasyID3)
