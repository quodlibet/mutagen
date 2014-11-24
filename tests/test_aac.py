import os
from tempfile import mkstemp
import shutil

from mutagen.id3 import ID3, TIT1
from mutagen.aac import AAC, AACError
from tests import TestCase, add


class TAAC(TestCase):

    def setUp(self):
        original = os.path.join("tests", "data", "empty.aac")
        fd, self.filename = mkstemp(suffix='.aac')
        os.close(fd)
        shutil.copy(original, self.filename)
        tag = ID3()
        tag.add(TIT1(text=[u"a" * 5000], encoding=3))
        tag.save(self.filename)

        self.aac = AAC(original)
        self.aac_id3 = AAC(self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_channels(self):
        self.failUnlessEqual(self.aac.info.channels, 2)
        self.failUnlessEqual(self.aac_id3.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.aac.info.sample_rate, 44100)
        self.failUnlessEqual(self.aac_id3.info.sample_rate, 44100)

    def test_length(self):
        self.failUnlessAlmostEqual(self.aac.info.length, 3.70, 2)
        self.failUnlessAlmostEqual(self.aac_id3.info.length, 3.70, 2)

    def test_not_my_file(self):
        self.failUnlessRaises(
            AACError, AAC,
            os.path.join("tests", "data", "empty.ogg"))

        self.failUnlessRaises(
            AACError, AAC,
            os.path.join("tests", "data", "silence-44-s.mp3"))

    def test_pprint(self):
        self.failUnless(self.aac.pprint())
        self.failUnless(self.aac_id3.pprint())

add(TAAC)
