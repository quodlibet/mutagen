import os
import shutil
from mutagen.oggvorbis import OggVorbis, OggVorbisNoHeaderError
from tests import TestCase, registerCase
from tempfile import mkstemp

class TOggVorbis(TestCase):
    def setUp(self):
        original = os.path.join("tests", "data", "empty.ogg")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
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
        self.failUnlessEqual(112000, self.vorbis.info.bitrate)

    def test_no_tags(self):
        self.failIf(self.vorbis.tags)
        self.failIf(self.vorbis.tags is None)

    def test_vendor(self):
        self.failUnless(
            self.vorbis.tags.vendor.startswith("Xiph.Org libVorbis"))
        self.failUnlessRaises(KeyError, self.vorbis.tags.__getitem__, "vendor")

    def test_vendor_safe(self):
        self.vorbis["vendor"] = "a vendor"
        self.vorbis.save()
        vorbis = OggVorbis(self.filename)
        self.failUnlessEqual(vorbis["vendor"], ["a vendor"])

    def test_set_two_tags(self):
        self.vorbis["foo"] = ["a"]
        self.vorbis["bar"] = ["b"]
        self.vorbis.save()
        vorbis = OggVorbis(self.filename)
        self.failUnlessEqual(len(vorbis.tags.keys()), 2)
        self.failUnlessEqual(vorbis["foo"], ["a"])
        self.failUnlessEqual(vorbis["bar"], ["b"])

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

    def test_really_big(self):
        self.vorbis["foo"] = "foo" * (2**16)
        self.vorbis["bar"] = "bar" * (2**16)
        self.vorbis["bar"] = "quux" * (2**16)
        self.vorbis.save()

    def test_invalid_open(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, OggVorbis,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_vorbiscomment(self):
        self.vorbis.save()
        self.failUnless(ogg.vorbis.VorbisFile(self.filename))

        self.test_really_big()
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.vorbis["foo"], vfc["foo"])

        self.vorbis.delete()
        self.vorbis["foobar"] = "foobar" * 1000
        self.vorbis.save()
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.vorbis["foobar"], vfc["foobar"])

    def test_invalid_delete(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, self.vorbis.delete,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_invalid_save(self):
        self.failUnlessRaises(OggVorbisNoHeaderError, self.vorbis.save,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_huge_tag(self):
        vorbis = OggVorbis(
            os.path.join("tests", "data", "multipagecomment.ogg"))
        self.failUnless("big" in vorbis.tags)
        self.failUnless("bigger" in vorbis.tags)
        self.failUnlessEqual(vorbis.tags["big"], ["foobar" * 10000])
        self.failUnlessEqual(vorbis.tags["bigger"], ["quuxbaz" * 10000])

    def tearDown(self):
        os.unlink(self.filename)

try: import ogg.vorbis
except ImportError:
    print "WARNING: Disabling pyvorbis crosscheck."
    del(TOggVorbis.test_vorbiscomment)

registerCase(TOggVorbis)
