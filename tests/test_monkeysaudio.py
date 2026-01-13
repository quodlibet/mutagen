
import os

from mutagen.monkeysaudio import MonkeysAudio, MonkeysAudioHeaderError
from tests import DATA_DIR, TestCase


class TMonkeysAudio(TestCase):

    def setUp(self):
        self.mac399 = MonkeysAudio(os.path.join(DATA_DIR, "mac-399.ape"))
        self.mac396 = MonkeysAudio(os.path.join(DATA_DIR, "mac-396.ape"))
        self.mac390 = MonkeysAudio(os.path.join(DATA_DIR, "mac-390-hdr.ape"))

    def test_channels(self):
        self.assertEqual(self.mac399.info.channels, 2)
        self.assertEqual(self.mac396.info.channels, 2)
        self.assertEqual(self.mac390.info.channels, 2)

    def test_sample_rate(self):
        self.assertEqual(self.mac399.info.sample_rate, 44100)
        self.assertEqual(self.mac396.info.sample_rate, 44100)
        self.assertEqual(self.mac390.info.sample_rate, 44100)

    def test_length(self):
        self.assertAlmostEqual(self.mac399.info.length, 3.68, 2)
        self.assertAlmostEqual(self.mac396.info.length, 3.68, 2)
        self.assertAlmostEqual(self.mac390.info.length, 15.63, 2)

    def test_bits_per_sample(self):
        assert self.mac399.info.bits_per_sample == 16
        assert self.mac396.info.bits_per_sample == 16
        assert self.mac390.info.bits_per_sample == 16

    def test_version(self):
        self.assertEqual(self.mac399.info.version, 3.99)
        self.assertEqual(self.mac396.info.version, 3.96)
        self.assertEqual(self.mac390.info.version, 3.90)

    def test_not_my_file(self):
        self.assertRaises(
            MonkeysAudioHeaderError, MonkeysAudio,
            os.path.join(DATA_DIR, "empty.ogg"))
        self.assertRaises(
            MonkeysAudioHeaderError, MonkeysAudio,
            os.path.join(DATA_DIR, "click.mpc"))

    def test_mime(self):
        self.assertTrue("audio/x-ape" in self.mac399.mime)

    def test_pprint(self):
        self.assertTrue(self.mac399.pprint())
        self.assertTrue(self.mac396.pprint())
