import os
import shutil

from tempfile import mkstemp

from mutagen._compat import cBytesIO
from mutagen.oggtheora import OggTheora, OggTheoraInfo, delete
from mutagen.ogg import OggPage
from tests import add
from tests.test_ogg import TOggFileType

class TOggTheora(TOggFileType):
    Kind = OggTheora

    def setUp(self):
        original = os.path.join("tests", "data", "sample.oggtheora")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = OggTheora(self.filename)
        self.audio2 = OggTheora(
            os.path.join("tests", "data", "sample_length.oggtheora"))
        self.audio3 = OggTheora(
            os.path.join("tests", "data", "sample_bitrate.oggtheora"))

    def test_theora_bad_version(self):
        page = OggPage(open(self.filename, "rb"))
        packet = page.packets[0]
        packet = packet[:7] + b"\x03\x00" + packet[9:]
        page.packets = [packet]
        fileobj = cBytesIO(page.write())
        self.failUnlessRaises(IOError, OggTheoraInfo, fileobj)

    def test_theora_not_first_page(self):
        page = OggPage(open(self.filename, "rb"))
        page.first = False
        fileobj = cBytesIO(page.write())
        self.failUnlessRaises(IOError, OggTheoraInfo, fileobj)

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("Xiph.Org libTheora"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.ogg')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

    def test_length(self):
        self.failUnlessAlmostEqual(5.5, self.audio.info.length, 1)
        self.failUnlessAlmostEqual(0.75, self.audio2.info.length, 2)

    def test_bitrate(self):
        self.failUnlessEqual(16777215, self.audio3.info.bitrate)

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(OggTheora(self.filename).tags)

    def test_mime(self):
        self.failUnless("video/x-theora" in self.audio.mime)

add(TOggTheora)
