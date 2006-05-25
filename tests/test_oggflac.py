import os
import shutil

from tempfile import mkstemp

from mutagen.oggflac import OggFLAC
from tests import add
from tests.test_oggvorbis import TOggVorbis

class TOggFLAC(TOggVorbis):
    Kind = OggFLAC

    def setUp(self):
        original = os.path.join("tests", "data", "empty.oggflac")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = OggFLAC(self.filename)

    def test_bitrate(self):
        pass

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("reference libFLAC"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_vorbiscomment(self):
        self.audio.save()
        self.failIf(os.system("flac --ogg -t %s 2> /dev/null" % self.filename))

        self.test_really_big()
        self.audio.save()
        self.failIf(os.system("flac --ogg -t %s 2> /dev/null" % self.filename))

        self.audio.delete()
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        self.failIf(os.system("flac --ogg -t %s 2> /dev/null" % self.filename))

    def test_huge_tag(self):
        pass

add(TOggFLAC)
