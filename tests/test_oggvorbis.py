import os
import shutil
import sys

from cStringIO import StringIO
from mutagen.ogg import OggPage
from mutagen.oggvorbis import OggVorbis, OggVorbisInfo, delete
from tests import TestCase, add
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

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(OggVorbis(self.filename).tags)

    def test_bitrate(self):
        self.failUnlessEqual(112000, self.audio.info.bitrate)

    def test_channels(self):
        self.failUnlessEqual(2, self.audio.info.channels)

    def test_sample_rate(self):
        self.failUnlessEqual(44100, self.audio.info.sample_rate)

    def test_invalid_not_first(self):
        page = OggPage(file(self.filename, "rb"))
        page.first = False
        self.failUnlessRaises(IOError, OggVorbisInfo, StringIO(page.write()))

    def test_avg_bitrate(self):
        page = OggPage(file(self.filename, "rb"))
        packet = page.packets[0]
        packet = (packet[:16] + "\x00\x00\x01\x00" + "\x00\x00\x00\x00" +
                  "\x00\x00\x00\x00" + packet[28:])
        page.packets[0] = packet
        info = OggVorbisInfo(StringIO(page.write()))
        self.failUnlessEqual(info.bitrate, 32768)

    def test_overestimated_bitrate(self):
        page = OggPage(file(self.filename, "rb"))
        packet = page.packets[0]
        packet = (packet[:16] + "\x00\x00\x01\x00" + "\x00\x00\x00\x01" +
                  "\x00\x00\x00\x00" + packet[28:])
        page.packets[0] = packet
        info = OggVorbisInfo(StringIO(page.write()))
        self.failUnlessEqual(info.bitrate, 65536)

    def test_underestimated_bitrate(self):
        page = OggPage(file(self.filename, "rb"))
        packet = page.packets[0]
        packet = (packet[:16] + "\x00\x00\x01\x00" + "\x01\x00\x00\x00" +
                  "\x00\x00\x01\x00" + packet[28:])
        page.packets[0] = packet
        info = OggVorbisInfo(StringIO(page.write()))
        self.failUnlessEqual(info.bitrate, 65536)

    def test_negative_bitrate(self):
        page = OggPage(file(self.filename, "rb"))
        packet = page.packets[0]
        packet = (packet[:16] + "\xff\xff\xff\xff" + "\xff\xff\xff\xff" +
                  "\xff\xff\xff\xff" + packet[28:])
        page.packets[0] = packet
        info = OggVorbisInfo(StringIO(page.write()))
        self.failUnlessEqual(info.bitrate, 0)

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("Xiph.Org libVorbis"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_vorbiscomment(self):
        self.audio.save()
        self.scan_file()
        if ogg is None: return
        self.failUnless(ogg.vorbis.VorbisFile(self.filename))

    def test_vorbiscomment_big(self):
        self.test_really_big()
        self.audio.save()
        self.scan_file()
        if ogg is None: return
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.audio["foo"], vfc["foo"])

    def test_vorbiscomment_delete(self):
        self.audio.delete()
        self.scan_file()
        if ogg is None: return
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(vfc.keys(), ["VENDOR"])

    def test_vorbiscomment_delete_readd(self):
        self.audio.delete()
        self.audio.tags.clear()
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        self.scan_file()
        if ogg is None: return
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        self.failUnlessEqual(self.audio["foobar"], vfc["foobar"])
        self.failUnless("FOOBAR" in vfc.keys())
        self.failUnless("VENDOR" in vfc.keys())

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

    def test_save_split_setup_packet(self):
        fn = os.path.join("tests", "data", "multipage-setup.ogg")
        shutil.copy(fn, self.filename)
        audio = OggVorbis(self.filename)
        tags = audio.tags
        self.failUnless(tags)
        audio.save()
        self.audio = OggVorbis(self.filename)
        self.failUnlessEqual(self.audio.tags, tags)

    def test_save_split_setup_packet_reference(self):
        if ogg is None: return
        self.test_save_split_setup_packet()
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        for key in self.audio:
            self.failUnlessEqual(vfc[key], self.audio[key])
        self.ogg_reference(self.filename)

    def test_save_grown_split_setup_packet_reference(self):
        if ogg is None: return
        fn = os.path.join("tests", "data", "multipage-setup.ogg")
        shutil.copy(fn, self.filename)
        audio = OggVorbis(self.filename)
        audio["foobar"] = ["quux" * 50000]
        tags = audio.tags
        self.failUnless(tags)
        audio.save()
        self.audio = OggVorbis(self.filename)
        self.failUnlessEqual(self.audio.tags, tags)
        vfc = ogg.vorbis.VorbisFile(self.filename).comment()
        for key in self.audio:
            self.failUnlessEqual(vfc[key], self.audio[key])
        self.ogg_reference(self.filename)

    def test_mime(self):
        self.failUnless("audio/vorbis" in self.audio.mime)

try: import ogg.vorbis
except ImportError:
    print "WARNING: Skipping Ogg Vorbis reference tests."
    ogg = None

add(TOggVorbis)
