import os
from tests import TestCase, add
from mutagen import File
from mutagen.oggvorbis import OggVorbis
from mutagen.oggflac import OggFLAC
from mutagen.mp3 import MP3
from mutagen.apev2 import APEv2File
from mutagen.flac import FLAC

class TFile(TestCase):
    def test_bad(self):
        try: self.failUnless(File("/dev/null") is None)
        except (OSError, IOError):
            print "WARNING: Unable to open /dev/null."
        self.failUnless(File(__file__) is None)

    def test_oggvorbis(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.ogg")), OggVorbis))

    def test_oggflac(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.oggflac")), OggFLAC))

    def test_mp3(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "bad-xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "silence-44-s.mp3")), MP3))

    def test_flac(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "silence-44-s.flac")), FLAC))

    def test_apev2(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "click.mpc")), APEv2File))

add(TFile)
