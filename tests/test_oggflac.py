import os
import shutil
import sys

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
        badval = os.system("tools/notarealprogram 2> /dev/null")
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != badval)
        if value == badval:
            sys.stdout.write("\bS")
            return

        self.test_really_big()
        self.audio.save()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != badval)

        self.audio.delete()
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != badval)

    def test_huge_tag(self):
        pass

    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.ogg')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

add(TOggFLAC)
