import os
from mutagen.trueaudio import TrueAudio, delete
from tests import TestCase, add

class TTrueAudio(TestCase):
    uses_mmap = False

    def setUp(self):
        self.audio = TrueAudio(os.path.join("tests", "data", "empty.tta"))

    def test_tags(self):
        self.failUnless(self.audio.tags is None)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 3.7, 1)

    def test_sample_rate(self):
        self.failUnlessEqual(44100, self.audio.info.sample_rate)

    def test_not_my_file(self):
        filename = os.path.join("tests", "data", "empty.ogg")
        self.failUnlessRaises(IOError, TrueAudio, filename)

    def test_module_delete(self):
        delete(os.path.join("tests", "data", "empty.tta"))

    def test_delete(self):
        self.audio.delete()
        self.failIf(self.audio.tags)

    def test_pprint(self):
        self.audio.pprint()

add(TTrueAudio)
