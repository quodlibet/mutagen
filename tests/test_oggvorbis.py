import os
import shutil
from mutagen.oggvorbis import OggVorbis
from tests import TestCase, registerCase
from tempfile import mkstemp

class TOggVorbis(TestCase):
    Kind = OggVorbis
    
    def setUp(self):
        original = os.path.join("tests", "data", "empty.ogg")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = self.Kind(self.filename)

    def test_pprint_empty(self):
        self.audio.pprint()

    def test_pprint_stuff(self):
        self.test_set_two_tags()
        self.audio.pprint()

    def test_length(self):
        self.failUnlessAlmostEqual(3.7, self.audio.info.length, 1)

    def test_bitrate(self):
        self.failUnlessEqual(112000, self.audio.info.bitrate)

    def test_no_tags(self):
        self.failIf(self.audio.tags)
        self.failIf(self.audio.tags is None)

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("Xiph.Org libVorbis"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_vendor_safe(self):
        self.audio["vendor"] = "a vendor"
        self.audio.save()
        vorbis = self.Kind(self.filename)
        self.failUnlessEqual(vorbis["vendor"], ["a vendor"])

    def test_set_two_tags(self):
        self.audio["foo"] = ["a"]
        self.audio["bar"] = ["b"]
        self.audio.save()
        vorbis = self.Kind(self.filename)
        self.failUnlessEqual(len(vorbis.tags.keys()), 2)
        self.failUnlessEqual(vorbis["foo"], ["a"])
        self.failUnlessEqual(vorbis["bar"], ["b"])

    def test_save_twice(self):
        self.audio.save()
        self.audio.save()
        self.failUnlessEqual(self.Kind(self.filename).tags, self.audio.tags)

    def test_set_delete(self):
        self.test_set_two_tags()
        self.audio.tags.clear()
        self.audio.save()
        vorbis = self.Kind(self.filename)
        self.failIf(vorbis.tags)

    def test_delete(self):
        self.test_set_two_tags()
        self.audio.delete()
        vorbis = self.Kind(self.filename)
        self.failIf(vorbis.tags)

    def test_really_big(self):
        self.audio["foo"] = "foo" * (2**16)
        self.audio["bar"] = "bar" * (2**16)
        self.audio["bar"] = "quux" * (2**16)
        self.audio.save()

    def test_invalid_open(self):
        self.failUnlessRaises(IOError, self.Kind,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_vorbiscomment(self):
        self.audio.save()
        self.failUnless(ogg.vorbis.VorbisFile(self.filename))

        self.test_really_big()
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.audio["foo"], vfc["foo"])

        self.audio.delete()
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.audio["foobar"], vfc["foobar"])

    def test_invalid_delete(self):
        self.failUnlessRaises(IOError, self.audio.delete,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_invalid_save(self):
        self.failUnlessRaises(IOError, self.audio.save,
                              os.path.join('tests', 'data', 'xing.mp3'))

    def test_huge_tag(self):
        vorbis = self.Kind(
            os.path.join("tests", "data", "multipagecomment.ogg"))
        self.failUnless("big" in vorbis.tags)
        self.failUnless("bigger" in vorbis.tags)
        self.failUnlessEqual(vorbis.tags["big"], ["foobar" * 10000])
        self.failUnlessEqual(vorbis.tags["bigger"], ["quuxbaz" * 10000])

    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.oggflac')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

    def tearDown(self):
        os.unlink(self.filename)

try: import ogg.vorbis
except ImportError:
    print "WARNING: Disabling pyvorbis crosscheck."
    del(TOggVorbis.test_vorbiscomment)

registerCase(TOggVorbis)
