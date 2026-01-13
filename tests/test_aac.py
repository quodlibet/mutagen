
import os

from mutagen.aac import AAC, AACError
from mutagen.id3 import ID3, TIT1
from tests import DATA_DIR, TestCase, get_temp_copy


class TADTS(TestCase):

    def setUp(self):
        original = os.path.join(DATA_DIR, "empty.aac")
        self.filename = get_temp_copy(original)

        tag = ID3()
        tag.add(TIT1(text=["a" * 5000], encoding=3))
        tag.save(self.filename)

        self.aac = AAC(original)
        self.aac_id3 = AAC(self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_channels(self):
        self.assertEqual(self.aac.info.channels, 2)
        self.assertEqual(self.aac_id3.info.channels, 2)

    def test_bitrate(self):
        self.assertEqual(self.aac.info.bitrate, 3159)
        self.assertEqual(self.aac_id3.info.bitrate, 3159)

    def test_sample_rate(self):
        self.assertEqual(self.aac.info.sample_rate, 44100)
        self.assertEqual(self.aac_id3.info.sample_rate, 44100)

    def test_length(self):
        self.assertAlmostEqual(self.aac.info.length, 3.70, 2)
        self.assertAlmostEqual(self.aac_id3.info.length, 3.70, 2)

    def test_not_my_file(self):
        self.assertRaises(
            AACError, AAC,
            os.path.join(DATA_DIR, "empty.ogg"))

        self.assertRaises(
            AACError, AAC,
            os.path.join(DATA_DIR, "silence-44-s.mp3"))

    def test_pprint(self):
        self.assertEqual(self.aac.pprint(), self.aac_id3.pprint())
        self.assertTrue("ADTS" in self.aac.pprint())


class TADIF(TestCase):

    def setUp(self):
        original = os.path.join(DATA_DIR, "adif.aac")
        self.filename = get_temp_copy(original)

        tag = ID3()
        tag.add(TIT1(text=["a" * 5000], encoding=3))
        tag.save(self.filename)

        self.aac = AAC(original)
        self.aac_id3 = AAC(self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_channels(self):
        self.assertEqual(self.aac.info.channels, 2)
        self.assertEqual(self.aac_id3.info.channels, 2)

    def test_bitrate(self):
        self.assertEqual(self.aac.info.bitrate, 128000)
        self.assertEqual(self.aac_id3.info.bitrate, 128000)

    def test_sample_rate(self):
        self.assertEqual(self.aac.info.sample_rate, 48000)
        self.assertEqual(self.aac_id3.info.sample_rate, 48000)

    def test_length(self):
        self.assertAlmostEqual(self.aac.info.length, 0.25, 2)
        self.assertAlmostEqual(self.aac_id3.info.length, 0.25, 2)

    def test_not_my_file(self):
        self.assertRaises(
            AACError, AAC,
            os.path.join(DATA_DIR, "empty.ogg"))

        self.assertRaises(
            AACError, AAC,
            os.path.join(DATA_DIR, "silence-44-s.mp3"))

    def test_pprint(self):
        self.assertEqual(self.aac.pprint(), self.aac_id3.pprint())
        self.assertTrue("ADIF" in self.aac.pprint())
