import os
import shutil
import sys
from mutagen.ogg import OggPage
from mutagen.oggvorbis import OggVorbis
from tests import TestCase, registerCase
from tests.test_ogg import TOggFileType
from tempfile import mkstemp

class TOggVorbis(TOggFileType):
    Kind = OggVorbis
    
    def setUp(self):
        original = os.path.join("tests", "data", "empty.ogg")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = self.Kind(self.filename)

    def test_bitrate(self):
        self.failUnlessEqual(112000, self.audio.info.bitrate)

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("Xiph.Org libVorbis"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

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
        self.scan_file()

    def test_huge_tag(self):
        vorbis = self.Kind(
            os.path.join("tests", "data", "multipagecomment.ogg"))
        self.failUnless("big" in vorbis.tags)
        self.failUnless("bigger" in vorbis.tags)
        self.failUnlessEqual(vorbis.tags["big"], ["foobar" * 10000])
        self.failUnlessEqual(vorbis.tags["bigger"], ["quuxbaz" * 10000])
        self.scan_file()

    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.oggflac')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

try: import ogg.vorbis
except ImportError:
    TOggVorbis.test_vorbiscomment = lambda self: sys.stdout.write("\bS")

registerCase(TOggVorbis)
