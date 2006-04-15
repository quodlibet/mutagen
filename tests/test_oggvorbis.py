import os
import shutil
from mutagen.oggvorbis import OggVorbis, OggVorbisNoHeaderError
from tests import TestCase, registerCase
from tempfile import mkstemp

class TOggVorbis(TestCase):
    def setUp(self):
        original = os.path.join("tests", "data", "empty.ogg")
        self.filename = mkstemp(suffix='.ogg')[1]
        shutil.copy(original, self.filename)
        self.vorbis = OggVorbis(self.filename)

    def test_pprint_empty(self):
        self.vorbis.pprint()

    def test_pprint_stuff(self):
        self.test_set_two_tags()
        self.vorbis.pprint()

    def test_length(self):
        self.failUnlessAlmostEqual(3.7, self.vorbis.info.length, 1)

    def test_bitrate(self):
        self.failUnlessEqual(758, self.vorbis.info.bitrate)

    def test_no_tags(self):
        self.failIf(self.vorbis.tags)
        self.failIf(self.vorbis.tags is None)

    def test_vendor(self):
        self.failUnless(
            self.vorbis.tags.vendor.startswith("Xiph.Org libVorbis"))
        self.failUnlessRaises(KeyError, self.vorbis.tags.__getitem__, "vendor")

    def test_vendor_safe(self):
        self.vorbis.tags["vendor"] = "a vendor"
        self.vorbis.save()
        vorbis = OggVorbis(self.filename)
        self.failUnlessEqual(vorbis.tags["vendor"], ["a vendor"])

    def test_set_two_tags(self):
        self.vorbis.tags["foo"] = ["a"]
        self.vorbis.tags["bar"] = ["b"]
        self.vorbis.save()
        vorbis = OggVorbis(self.filename)
        self.failUnlessEqual(len(vorbis.tags.keys()), 2)
        self.failUnlessEqual(vorbis.tags["foo"], ["a"])
        self.failUnlessEqual(vorbis.tags["bar"], ["b"])

    def test_save_twice(self):
        self.vorbis.save()
        self.vorbis.save()
        self.failUnlessEqual(OggVorbis(self.filename).tags, self.vorbis.tags)

    def test_set_delete(self):
        self.test_set_two_tags()
        self.vorbis.tags.clear()
        self.vorbis.save()
        vorbis = OggVorbis(self.filename)
        self.failIf(vorbis.tags)

    def test_delete(self):
        self.test_set_two_tags()
        self.vorbis.delete()
        vorbis = OggVorbis(self.filename)
        self.failIf(vorbis.tags)

    def test_invalid_open(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, OggVorbis,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_invalid_delete(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, self.vorbis.delete,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_invalid_save(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, self.vorbis.save,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def tearDown(self):
        os.unlink(self.filename)
registerCase(TOggVorbis)
