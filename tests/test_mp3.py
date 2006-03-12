import os
from unittest import TestCase
from tests import registerCase
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

class TMP3(TestCase):
    silence = os.path.join('tests', 'data', 'silence-44-s.mp3')
    def setUp(self):
        self.mp3 = MP3(self.silence)

    def test_id3(self):
        self.failUnlessEqual(self.mp3.tags, ID3(self.silence))

    def test_length(self):
        self.failUnlessEqual(int(round(self.mp3.info.length)), 4)
    def test_version(self):
        self.failUnlessEqual(self.mp3.info.version, 1)
    def test_layer(self):
        self.failUnlessEqual(self.mp3.info.layer, 3)
    def test_bitrate(self):
        self.failUnlessEqual(self.mp3.info.bitrate, 32000)
registerCase(TMP3)
