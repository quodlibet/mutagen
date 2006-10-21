import os

from mutagen.optimfrog import OptimFROG, OptimFROGHeaderError
from cStringIO import StringIO
from tests import TestCase, add

class TOptimFROG(TestCase):
    uses_mmap = False

    def setUp(self):
        self.ofr = OptimFROG(os.path.join("tests", "data", "empty.ofr"))
        self.ofs = OptimFROG(os.path.join("tests", "data", "empty.ofs"))

    def test_channels(self):
        self.failUnlessEqual(self.ofr.info.channels, 2)
        self.failUnlessEqual(self.ofs.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.ofr.info.sample_rate, 44100)
        self.failUnlessEqual(self.ofs.info.sample_rate, 44100)

    def test_length(self):
        self.failUnlessAlmostEqual(self.ofr.info.length, 3.68, 2)
        self.failUnlessAlmostEqual(self.ofs.info.length, 3.68, 2)

    def test_not_my_file(self):
        self.failUnlessRaises(
            OptimFROGHeaderError, OptimFROG,
            os.path.join("tests", "data", "empty.ogg"))
        self.failUnlessRaises(
            OptimFROGHeaderError, OptimFROG,
            os.path.join("tests", "data", "click.mpc"))

    def test_pprint(self):
        self.failUnless(self.ofr.pprint())
        self.failUnless(self.ofs.pprint())

add(TOptimFROG)
