import os

from mutagen.musepack import Musepack, MusepackInfo, MusepackHeaderError
from cStringIO import StringIO
from tests import TestCase, add

class TMusepack(TestCase):
    uses_mmap = False

    def setUp(self):
        self.sv7 = Musepack(os.path.join("tests", "data", "click.mpc"))
        self.sv5 = Musepack(os.path.join("tests", "data", "sv5_header.mpc"))
        self.sv4 = Musepack(os.path.join("tests", "data", "sv4_header.mpc"))

    def test_channels(self):
        self.failUnlessEqual(self.sv7.info.channels, 2)
        self.failUnlessEqual(self.sv5.info.channels, 2)
        self.failUnlessEqual(self.sv4.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.sv7.info.sample_rate, 44100)
        self.failUnlessEqual(self.sv5.info.sample_rate, 44100)
        self.failUnlessEqual(self.sv4.info.sample_rate, 44100)

    def test_bitrate(self):
        self.failUnlessEqual(self.sv7.info.bitrate, 195)
        self.failUnlessEqual(self.sv5.info.bitrate, 0)
        self.failUnlessEqual(self.sv4.info.bitrate, 0)

    def test_length(self):
        self.failUnlessAlmostEqual(self.sv7.info.length, 0.07, 2)
        self.failUnlessAlmostEqual(self.sv5.info.length, 26.3, 1)
        self.failUnlessAlmostEqual(self.sv4.info.length, 26.3, 1)

    def test_not_my_file(self):
        self.failUnlessRaises(
            MusepackHeaderError, Musepack,
            os.path.join("tests", "data", "empty.ogg"))
        self.failUnlessRaises(
            MusepackHeaderError, Musepack,
            os.path.join("tests", "data", "emptyfile.mp3"))

    def test_almost_my_file(self):
        self.failUnlessRaises(
            MusepackHeaderError, MusepackInfo, StringIO("MP+" + "\x00" * 100))

    def test_pprint(self):
        self.sv7.pprint()
        self.sv5.pprint()
        self.sv4.pprint()
add(TMusepack)
