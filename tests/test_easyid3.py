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
            if key == "date":
                continue
            elif key == "musicbrainz_trackid":
                continue

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
        self.failUnlessEqual(id3["date"], ["2004"])

        self.id3["date"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(id3["date"], ["2004"])

    def test_date_delete(self):
        self.id3["date"] = "2004"
        self.failUnlessEqual(self.id3["date"], ["2004"])
        del(self.id3["date"])
        self.failIf("date" in self.id3)
        
    def test_write_date_double(self):
        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(id3["date"], ["2004", "2005"])

        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(id3["date"], ["2004", "2005"])

    def test_write_invalid(self):
        self.failUnlessRaises(ValueError, self.id3.__getitem__, "notvalid")
        self.failUnlessRaises(ValueError, self.id3.__delitem__, "notvalid")
        self.failUnlessRaises(
            ValueError, self.id3.__setitem__, "notvalid", "tests")

    def test_perfomer(self):
        self.id3["performer:coder"] = ["piman", "mu"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(id3["performer:coder"], ["piman", "mu"])

    def test_no_performer(self):
        self.failIf("performer:foo" in self.id3)

    def test_performer_delete(self):
        self.id3["performer:foo"] = "Joe"
        self.id3["performer:bar"] = "Joe"
        self.failUnless("performer:foo" in self.id3)
        self.failUnless("performer:bar" in self.id3)
        del(self.id3["performer:foo"])
        self.failIf("performer:foo" in self.id3)
        self.failUnless("performer:bar" in self.id3)
        del(self.id3["performer:bar"])
        self.failIf("performer:bar" in self.id3)
        self.failIf("TMCL" in self.id3._EasyID3__id3)

    def test_performer_delete_dne(self):
        self.failUnlessRaises(KeyError, self.id3.__delitem__, "performer:bar")
        self.id3["performer:foo"] = "Joe"
        self.failUnlessRaises(KeyError, self.id3.__delitem__, "performer:bar")

    def test_txxx_set_get(self):
        self.failIf("asin" in self.id3)
        self.id3["asin"] = "Hello"
        self.failUnless("asin" in self.id3)
        self.failUnlessEqual(self.id3["asin"], ["Hello"])
        self.failUnless("TXXX:ASIN" in self.id3._EasyID3__id3)

    def test_txxx_del_set_del(self):
        self.failIf("asin" in self.id3)
        self.failUnlessRaises(KeyError, self.id3.__delitem__, "asin")
        self.id3["asin"] = "Hello"
        self.failUnless("asin" in self.id3)
        self.failUnlessEqual(self.id3["asin"], ["Hello"])
        del(self.id3["asin"])
        self.failIf("asin" in self.id3)
        self.failUnlessRaises(KeyError, self.id3.__delitem__, "asin")

    def test_txxx_save(self):
        self.id3["asin"] = "Hello"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.failUnlessEqual(id3["asin"], ["Hello"])

    def test_txxx_unicode(self):
        self.id3["asin"] = u"He\u1234llo"
        self.failUnlessEqual(self.id3["asin"], [u"He\u1234llo"])

    def test_bad_trackid(self):
        self.failUnlessRaises(ValueError, self.id3.__setitem__,
                              "musicbrainz_trackid", ["a", "b"])

    def tearDown(self):
        os.unlink(self.filename)

add(TEasyID3)
