
import os

from mutagen.smf import SMF, SMFError
from tests import DATA_DIR, TestCase


class TSMF(TestCase):

    def setUp(self):
        self.audio = SMF(os.path.join(DATA_DIR, "sample.mid"))

    def test_length(self):
        self.assertAlmostEqual(self.audio.info.length, 127.997, 2)

    def test_not_my_file(self):
        self.assertRaises(
            SMFError, SMF, os.path.join(DATA_DIR, "empty.ogg"))

    def test_pprint(self):
        self.audio.pprint()
        self.audio.info.pprint()

    def test_mime(self):
        self.assertTrue("audio/x-midi" in self.audio.mime)
        self.assertTrue("audio/midi" in self.audio.mime)
