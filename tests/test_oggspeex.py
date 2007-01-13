import os
import shutil
import sys

from cStringIO import StringIO
from mutagen.ogg import OggPage
from mutagen.oggspeex import OggSpeex, OggSpeexInfo, delete
from tests import TestCase, add
from tests.test_ogg import TOggFileType
from tempfile import mkstemp

class TOggSpeex(TOggFileType):
    Kind = OggSpeex
    
    def setUp(self):
        original = os.path.join("tests", "data", "empty.spx")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = self.Kind(self.filename)

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(OggSpeex(self.filename).tags)

    def test_channels(self):
        self.failUnlessEqual(2, self.audio.info.channels)

    def test_sample_rate(self):
        self.failUnlessEqual(44100, self.audio.info.sample_rate)

    def test_bitrate(self):
        self.failUnlessEqual(0, self.audio.info.bitrate)

    def test_invalid_not_first(self):
        page = OggPage(file(self.filename, "rb"))
        page.first = False
        self.failUnlessRaises(IOError, OggSpeexInfo, StringIO(page.write()))

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("Encoded with Speex 1.1.12"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.oggflac')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

    def test_multiplexed_in_headers(self):
        shutil.copy(
            os.path.join("tests", "data", "multiplexed.spx"), self.filename)
        audio = self.Kind(self.filename)
        audio.tags["foo"] = ["bar"]
        audio.save()
        audio = self.Kind(self.filename)
        self.failUnlessEqual(audio.tags["foo"], ["bar"])

    def test_mime(self):
        self.failUnless("audio/x-speex" in self.audio.mime)

add(TOggSpeex)
