import os
from mutagen.tta import TTA, delete
from tests import TestCase, add

class TTTA(TestCase):
    uses_mmap = False

    def setUp(self):
        self.audio = TTA(os.path.join("tests", "data", "empty.tta"))

    def test_tags(self):
        self.failUnless(self.audio.tags is None)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 3.7, 1)

    def test_sample_rate(self):
        self.failUnlessEqual(44100, self.audio.info.sample_rate)

    def test_not_my_file(self):
        filename = os.path.join("tests", "data", "empty.ogg")
        self.failUnlessRaises(IOError, TTA, filename)

    def test_delete(self):
        delete(os.path.join("tests", "data", "empty.tta"))

    def test_pprint(self):
        self.audio.pprint()

add(TTTA)
