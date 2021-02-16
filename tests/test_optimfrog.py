
import os

from mutagen.optimfrog import OptimFROG, OptimFROGHeaderError
from tests import TestCase, DATA_DIR


class TOptimFROG(TestCase):

    def setUp(self):
        self.ofr = OptimFROG(os.path.join(DATA_DIR, "empty.ofr"))
        self.ofs = OptimFROG(os.path.join(DATA_DIR, "empty.ofs"))
        self.ofr_5100 = OptimFROG(
            os.path.join(DATA_DIR, "silence-2s-44100-16.ofr"))
        self.ofs_5100 = OptimFROG(
            os.path.join(DATA_DIR, "silence-2s-44100-16.ofs"))

    def test_channels(self):
        self.failUnlessEqual(self.ofr.info.channels, 2)
        self.failUnlessEqual(self.ofs.info.channels, 2)
        self.failUnlessEqual(self.ofr_5100.info.channels, 2)
        self.failUnlessEqual(self.ofs_5100.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.ofr.info.sample_rate, 44100)
        self.failUnlessEqual(self.ofs.info.sample_rate, 44100)
        self.failUnlessEqual(self.ofr_5100.info.sample_rate, 44100)
        self.failUnlessEqual(self.ofs_5100.info.sample_rate, 44100)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.ofr.info.bits_per_sample, 16)
        self.failUnlessEqual(self.ofs.info.bits_per_sample, 16)
        self.failUnlessEqual(self.ofr_5100.info.bits_per_sample, 16)
        self.failUnlessEqual(self.ofs_5100.info.bits_per_sample, 16)

    def test_length(self):
        self.failUnlessAlmostEqual(self.ofr.info.length, 3.68, 2)
        self.failUnlessAlmostEqual(self.ofs.info.length, 3.68, 2)
        self.failUnlessAlmostEqual(self.ofr_5100.info.length, 2.0, 2)
        self.failUnlessAlmostEqual(self.ofs_5100.info.length, 2.0, 2)

    def test_encoder_info(self):
        self.failUnlessEqual(self.ofr.info.encoder_info, "4.520")
        self.failUnlessEqual(self.ofs.info.encoder_info, "4.520")
        self.failUnlessEqual(self.ofr_5100.info.encoder_info, "5.100")
        self.failUnlessEqual(self.ofs_5100.info.encoder_info, "5.100")

    def test_not_my_file(self):
        self.failUnlessRaises(
            OptimFROGHeaderError, OptimFROG,
            os.path.join(DATA_DIR, "empty.ogg"))
        self.failUnlessRaises(
            OptimFROGHeaderError, OptimFROG,
            os.path.join(DATA_DIR, "click.mpc"))

    def test_pprint(self):
        self.failUnless(self.ofr.pprint())
        self.failUnless(self.ofs.pprint())
