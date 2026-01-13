
import os
from io import BytesIO

from mutagen.ogg import OggPage
from mutagen.oggtheora import OggTheora, OggTheoraInfo, delete, error
from tests import DATA_DIR, TestCase, get_temp_copy
from tests.test_ogg import TOggFileTypeMixin


class TOggTheora(TestCase, TOggFileTypeMixin):
    Kind = OggTheora

    def setUp(self):
        self.filename = get_temp_copy(
            os.path.join(DATA_DIR, "sample.oggtheora"))

        self.audio = OggTheora(self.filename)
        self.audio2 = OggTheora(
            os.path.join(DATA_DIR, "sample_length.oggtheora"))
        self.audio3 = OggTheora(
            os.path.join(DATA_DIR, "sample_bitrate.oggtheora"))

    def tearDown(self):
        os.unlink(self.filename)

    def test_theora_bad_version(self):
        with open(self.filename, "rb") as h:
            page = OggPage(h)
        packet = page.packets[0]
        packet = packet[:7] + b"\x03\x00" + packet[9:]
        page.packets = [packet]
        fileobj = BytesIO(page.write())
        self.assertRaises(error, OggTheoraInfo, fileobj)

    def test_theora_not_first_page(self):
        with open(self.filename, "rb") as h:
            page = OggPage(h)
        page.first = False
        fileobj = BytesIO(page.write())
        self.assertRaises(error, OggTheoraInfo, fileobj)

    def test_vendor(self):
        self.assertTrue(
            self.audio.tags.vendor.startswith("Xiph.Org libTheora"))
        self.assertRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_not_my_ogg(self):
        fn = os.path.join(DATA_DIR, 'empty.ogg')
        self.assertRaises(error, type(self.audio), fn)
        self.assertRaises(error, self.audio.save, fn)
        self.assertRaises(error, self.audio.delete, fn)

    def test_length(self):
        self.assertAlmostEqual(5.5, self.audio.info.length, 1)
        self.assertAlmostEqual(0.75, self.audio2.info.length, 2)

    def test_bitrate(self):
        self.assertEqual(16777215, self.audio3.info.bitrate)

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.assertFalse(OggTheora(self.filename).tags)

    def test_mime(self):
        self.assertTrue("video/x-theora" in self.audio.mime)

    def test_init_padding(self):
        self.assertEqual(self.audio.tags._padding, 0)
