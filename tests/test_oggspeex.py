
import os
import shutil
from io import BytesIO

from mutagen.ogg import OggPage
from mutagen.oggspeex import OggSpeex, OggSpeexInfo, delete, error
from tests import DATA_DIR, TestCase, get_temp_copy
from tests.test_ogg import TOggFileTypeMixin


class TOggSpeex(TestCase, TOggFileTypeMixin):
    Kind = OggSpeex

    def setUp(self):
        self.filename = get_temp_copy(os.path.join(DATA_DIR, "empty.spx"))
        self.audio = self.Kind(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.assertFalse(OggSpeex(self.filename).tags)

    def test_channels(self):
        self.assertEqual(2, self.audio.info.channels)

    def test_sample_rate(self):
        self.assertEqual(44100, self.audio.info.sample_rate)

    def test_bitrate(self):
        self.assertEqual(0, self.audio.info.bitrate)

    def test_invalid_not_first(self):
        with open(self.filename, "rb") as h:
            page = OggPage(h)
        page.first = False
        self.assertRaises(error, OggSpeexInfo, BytesIO(page.write()))

    def test_vendor(self):
        self.assertTrue(
            self.audio.tags.vendor.startswith("Encoded with Speex 1.1.12"))
        self.assertRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_not_my_ogg(self):
        fn = os.path.join(DATA_DIR, 'empty.oggflac')
        self.assertRaises(error, type(self.audio), fn)
        self.assertRaises(error, self.audio.save, fn)
        self.assertRaises(error, self.audio.delete, fn)

    def test_multiplexed_in_headers(self):
        shutil.copy(
            os.path.join(DATA_DIR, "multiplexed.spx"), self.filename)
        audio = self.Kind(self.filename)
        audio.tags["foo"] = ["bar"]
        audio.save()
        audio = self.Kind(self.filename)
        self.assertEqual(audio.tags["foo"], ["bar"])

    def test_mime(self):
        self.assertTrue("audio/x-speex" in self.audio.mime)

    def test_init_padding(self):
        self.assertEqual(self.audio.tags._padding, 0)
