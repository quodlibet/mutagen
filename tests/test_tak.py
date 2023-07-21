
import os
import io

from mutagen.tak import TAK, TAKHeaderError
from tests import TestCase, DATA_DIR


class TTAK(TestCase):

    def setUp(self):
        self.tak_no_tags = TAK(os.path.join(DATA_DIR, "silence-44-s.tak"))
        self.tak_tags = TAK(os.path.join(DATA_DIR, "has-tags.tak"))

    def test_channels(self):
        self.failUnlessEqual(self.tak_no_tags.info.channels, 2)
        self.failUnlessEqual(self.tak_tags.info.channels, 2)

    def test_length(self):
        self.failUnlessAlmostEqual(self.tak_no_tags.info.length, 3.68,
                                   delta=0.009)
        self.failUnlessAlmostEqual(self.tak_tags.info.length, 0.08,
                                   delta=0.009)

    def test_sample_rate(self):
        self.failUnlessEqual(self.tak_no_tags.info.sample_rate, 44100)
        self.failUnlessEqual(self.tak_tags.info.sample_rate, 44100)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.tak_no_tags.info.bits_per_sample, 16)
        self.failUnlessAlmostEqual(self.tak_tags.info.bits_per_sample, 16)

    def test_encoder_info(self):
        self.failUnlessEqual(self.tak_no_tags.info.encoder_info, "TAK 2.3.0")
        self.failUnlessEqual(self.tak_tags.info.encoder_info, "TAK 2.3.0")

    def test_not_my_file(self):
        self.failUnlessRaises(
            TAKHeaderError, TAK,
            os.path.join(DATA_DIR, "empty.ogg"))
        self.failUnlessRaises(
            TAKHeaderError, TAK,
            os.path.join(DATA_DIR, "click.mpc"))

    def test_mime(self):
        self.failUnless("audio/x-tak" in self.tak_no_tags.mime)

    def test_pprint(self):
        self.failUnless(self.tak_no_tags.pprint())
        self.failUnless(self.tak_tags.pprint())

    def test_fuzz_only_end(self):
        with self.assertRaises(TAKHeaderError):
            TAK(io.BytesIO(b'tBaK\x00\x00\x00\x00'))
