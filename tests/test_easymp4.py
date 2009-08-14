import os
import sys
import shutil
from tests import add, TestCase
from mutagen.easymp4 import EasyMP4, error as MP4Error, delete
from tempfile import mkstemp

class TEasyMP4(TestCase):

    def setUp(self):
        fd, self.filename = mkstemp('.mp4')
        os.close(fd)
        empty = os.path.join('tests', 'data', 'has-tags.m4a')
        shutil.copy(empty, self.filename)
        self.mp4 = EasyMP4(self.filename)
        self.mp4.delete()

    def test_pprint(self):
        self.mp4["artist"] = "baz"
        self.mp4.pprint()

    def test_has_key(self):
        self.failIf(self.mp4.has_key("foo"))

    def test_empty_file(self):
        empty = os.path.join('tests', 'data', 'emptyfile.mp3')
        self.assertRaises(MP4Error, EasyMP4, filename=empty)

    def test_nonexistent_file(self):
        empty = os.path.join('tests', 'data', 'does', 'not', 'exist')
        self.assertRaises(IOError, EasyMP4, filename=empty)

    def test_write_single(self):
        for key in EasyMP4.Get:
            if key in ["tracknumber", "discnumber", "date", "bpm"]:
                continue

            # Test creation
            self.mp4[key] = "a test value"
            self.mp4.save(self.filename)
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4[key], ["a test value"])
            self.failUnlessEqual(mp4.keys(), [key])

            # And non-creation setting.
            self.mp4[key] = "a test value"
            self.mp4.save(self.filename)
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4[key], ["a test value"])
            self.failUnlessEqual(mp4.keys(), [key])

            del(self.mp4[key])

    def test_write_double(self):
        for key in EasyMP4.Get:
            if key in ["tracknumber", "discnumber", "date", "bpm"]:
                continue

            self.mp4[key] = ["a test", "value"]
            self.mp4.save(self.filename)
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4.get(key), ["a test", "value"])
            self.failUnlessEqual(mp4.keys(), [key])

            self.mp4[key] = ["a test", "value"]
            self.mp4.save(self.filename)
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4.get(key), ["a test", "value"])
            self.failUnlessEqual(mp4.keys(), [key])

            del(self.mp4[key])

    def test_write_date(self):
        self.mp4["date"] = "2004"
        self.mp4.save(self.filename)
        mp4 = EasyMP4(self.filename)
        self.failUnlessEqual(mp4["date"], ["2004"])

        self.mp4["date"] = "2004"
        self.mp4.save(self.filename)
        mp4 = EasyMP4(self.filename)
        self.failUnlessEqual(mp4["date"], ["2004"])

    def test_date_delete(self):
        self.mp4["date"] = "2004"
        self.failUnlessEqual(self.mp4["date"], ["2004"])
        del(self.mp4["date"])
        self.failIf("date" in self.mp4)
        
    def test_write_date_double(self):
        self.mp4["date"] = ["2004", "2005"]
        self.mp4.save(self.filename)
        mp4 = EasyMP4(self.filename)
        self.failUnlessEqual(mp4["date"], ["2004", "2005"])

        self.mp4["date"] = ["2004", "2005"]
        self.mp4.save(self.filename)
        mp4 = EasyMP4(self.filename)
        self.failUnlessEqual(mp4["date"], ["2004", "2005"])

    def test_write_invalid(self):
        self.failUnlessRaises(ValueError, self.mp4.__getitem__, "notvalid")
        self.failUnlessRaises(ValueError, self.mp4.__delitem__, "notvalid")
        self.failUnlessRaises(
            ValueError, self.mp4.__setitem__, "notvalid", "tests")

    def test_numeric(self):
        for tag in ["bpm"]:
            self.mp4[tag] = "3"
            self.failUnlessEqual(self.mp4[tag], ["3"])
            self.mp4.save()
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4[tag], ["3"])

            del(mp4[tag])
            self.failIf(tag in mp4)
            self.failUnlessRaises(KeyError, mp4.__delitem__, tag)

            self.failUnlessRaises(
                ValueError, self.mp4.__setitem__, tag, "hello")

    def test_numeric_pairs(self):
        for tag in ["tracknumber", "discnumber"]:
            self.mp4[tag] = "3"
            self.failUnlessEqual(self.mp4[tag], ["3"])
            self.mp4.save()
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4[tag], ["3"])

            del(mp4[tag])
            self.failIf(tag in mp4)
            self.failUnlessRaises(KeyError, mp4.__delitem__, tag)

            self.mp4[tag] = "3/10"
            self.failUnlessEqual(self.mp4[tag], ["3/10"])
            self.mp4.save()
            mp4 = EasyMP4(self.filename)
            self.failUnlessEqual(mp4[tag], ["3/10"])

            del(mp4[tag])
            self.failIf(tag in mp4)
            self.failUnlessRaises(KeyError, mp4.__delitem__, tag)

            self.failUnlessRaises(
                ValueError, self.mp4.__setitem__, tag, "hello")

    def tearDown(self):
        os.unlink(self.filename)

add(TEasyMP4)
