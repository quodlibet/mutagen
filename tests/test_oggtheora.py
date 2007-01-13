import os
import shutil
import sys

from tempfile import mkstemp
from cStringIO import StringIO

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

    def test_theora_bad_version(self):
        page = OggPage(file(self.filename, "rb"))
        packet = page.packets[0]
        packet = packet[:7] + "\x03\x00" + packet[9:]
        page.packets = [packet]
        fileobj = StringIO(page.write())
        self.failUnlessRaises(IOError, OggTheoraInfo, fileobj)

    def test_theora_not_first_page(self):
        page = OggPage(file(self.filename, "rb"))
        page.first = False
        fileobj = StringIO(page.write())
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

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(OggTheora(self.filename).tags)

    def test_mime(self):
        self.failUnless("video/x-theora" in self.audio.mime)

add(TOggTheora)
