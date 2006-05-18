from tests import TestCase, add
from mutagen import File
from mutagen.oggvorbis import OggVorbis
from mutagen.mp3 import MP3
from mutagen.apev2 import APEv2File
from mutagen.flac import FLAC

class TFile(TestCase):
    def test_bad(self):
        self.failUnless(File("/dev/null") is None)
        self.failUnless(File(__file__) is None)

    def test_oggvorbis(self):
        self.failUnless(isinstance(File("tests/data/empty.ogg"), OggVorbis))

    def test_mp3(self):
        self.failUnless(isinstance(File("tests/data/bad-xing.mp3"), MP3))
        self.failUnless(isinstance(File("tests/data/xing.mp3"), MP3))
        self.failUnless(isinstance(File("tests/data/silence-44-s.mp3"), MP3))

    def test_flac(self):
        self.failUnless(isinstance(File("tests/data/silence-44-s.flac"), FLAC))

    def test_apev2(self):
        self.failUnless(isinstance(File("tests/data/click.mpc"), APEv2File))

add(TFile)
