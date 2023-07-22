
import os
import io

from mutagen.ac3 import AC3, AC3Error

from tests import TestCase, DATA_DIR


class TAC3(TestCase):

    def setUp(self):
        self.ac3 = AC3(os.path.join(DATA_DIR, "silence-44-s.ac3"))
        self.eac3 = AC3(os.path.join(DATA_DIR, "silence-44-s.eac3"))

    def test_channels(self):
        self.failUnlessEqual(self.ac3.info.channels, 2)
        self.failUnlessEqual(self.eac3.info.channels, 2)

    def test_bitrate(self):
        self.failUnlessEqual(self.ac3.info.bitrate, 192000)
        self.failUnlessAlmostEqual(self.eac3.info.bitrate, 192000, delta=500)

    def test_sample_rate(self):
        self.failUnlessEqual(self.ac3.info.sample_rate, 44100)
        self.failUnlessEqual(self.eac3.info.sample_rate, 44100)

    def test_length(self):
        self.failUnlessAlmostEqual(self.ac3.info.length, 3.70, delta=0.009)
        self.failUnlessAlmostEqual(self.eac3.info.length, 3.70, delta=0.009)

    def test_type(self):
        self.failUnlessEqual(self.ac3.info.codec, "ac-3")
        self.failUnlessEqual(self.eac3.info.codec, "ec-3")

    def test_not_my_file(self):
        self.failUnlessRaises(
            AC3Error, AC3,
            os.path.join(DATA_DIR, "empty.ogg"))

        self.failUnlessRaises(
            AC3Error, AC3,
            os.path.join(DATA_DIR, "silence-44-s.mp3"))

    def test_pprint(self):
        self.assertTrue("ac-3" in self.ac3.pprint())
        self.assertTrue("ec-3" in self.eac3.pprint())

    def test_fuzz_extra_bitstream_info(self):
        with self.assertRaises(AC3Error):
            AC3(io.BytesIO(b'\x0bwII\x00\x00\xe3\xe3//'))
