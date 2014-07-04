import os
import shutil

from tests import TestCase
from mutagen._compat import cBytesIO
from tests import add
from mutagen.mp3 import MP3, error as MP3Error, delete, MPEGInfo, EasyMP3
from mutagen.id3 import ID3
from tempfile import mkstemp

class TMP3(TestCase):
    silence = os.path.join('tests', 'data', 'silence-44-s.mp3')
    silence_nov2 = os.path.join('tests', 'data', 'silence-44-s-v1.mp3')
    silence_mpeg2 = os.path.join('tests', 'data', 'silence-44-s-mpeg2.mp3')
    silence_mpeg25 = os.path.join('tests', 'data', 'silence-44-s-mpeg25.mp3')

    def setUp(self):
        original = os.path.join("tests", "data", "silence-44-s.mp3")
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.mp3 = MP3(self.filename)
        self.mp3_2 = MP3(self.silence_nov2)
        self.mp3_3 = MP3(self.silence_mpeg2)
        self.mp3_4 = MP3(self.silence_mpeg25)

    def test_mode(self):
        from mutagen.mp3 import JOINTSTEREO
        self.failUnlessEqual(self.mp3.info.mode, JOINTSTEREO)
        self.failUnlessEqual(self.mp3_2.info.mode, JOINTSTEREO)
        self.failUnlessEqual(self.mp3_3.info.mode, JOINTSTEREO)
        self.failUnlessEqual(self.mp3_4.info.mode, JOINTSTEREO)

    def test_id3(self):
        self.failUnlessEqual(self.mp3.tags, ID3(self.silence))
        self.failUnlessEqual(self.mp3_2.tags, ID3(self.silence_nov2))

    def test_length(self):
        self.assertAlmostEquals(self.mp3.info.length, 3.77, 2)
        self.assertAlmostEquals(self.mp3_2.info.length, 3.77, 2)
        self.assertAlmostEquals(self.mp3_3.info.length, 3.77, 2)
        self.assertAlmostEquals(self.mp3_4.info.length, 3.84, 2)
    def test_version(self):
        self.failUnlessEqual(self.mp3.info.version, 1)
        self.failUnlessEqual(self.mp3_2.info.version, 1)
        self.failUnlessEqual(self.mp3_3.info.version, 2)
        self.failUnlessEqual(self.mp3_4.info.version, 2.5)
    def test_layer(self):
        self.failUnlessEqual(self.mp3.info.layer, 3)
        self.failUnlessEqual(self.mp3_2.info.layer, 3)
        self.failUnlessEqual(self.mp3_3.info.layer, 3)
        self.failUnlessEqual(self.mp3_4.info.layer, 3)
    def test_bitrate(self):
        self.failUnlessEqual(self.mp3.info.bitrate, 32000)
        self.failUnlessEqual(self.mp3_2.info.bitrate, 32000)
        self.failUnlessEqual(self.mp3_3.info.bitrate, 18191)
        self.failUnlessEqual(self.mp3_4.info.bitrate, 9300)

    def test_notmp3(self):
        self.failUnlessRaises(
            MP3Error, MP3, os.path.join('tests', 'data', 'empty.ofr'))

    def test_sketchy(self):
        self.failIf(self.mp3.info.sketchy)
        self.failIf(self.mp3_2.info.sketchy)
        self.failIf(self.mp3_3.info.sketchy)
        self.failIf(self.mp3_4.info.sketchy)

    def test_sketchy_notmp3(self):
        notmp3 = MP3(os.path.join("tests", "data", "silence-44-s.flac"))
        self.failUnless(notmp3.info.sketchy)

    def test_pprint(self):
        self.failUnless(self.mp3.pprint())

    def test_pprint_no_tags(self):
        self.mp3.tags = None
        self.failUnless(self.mp3.pprint())

    def test_xing(self):
        mp3 = MP3(os.path.join("tests", "data", "xing.mp3"))
        self.failUnlessEqual(int(round(mp3.info.length)), 26122)
        self.failUnlessEqual(mp3.info.bitrate, 306)

    def test_vbri(self):
        mp3 = MP3(os.path.join("tests", "data", "vbri.mp3"))
        self.failUnlessEqual(int(round(mp3.info.length)), 222)

    def test_empty_xing(self):
        MP3(os.path.join("tests", "data", "bad-xing.mp3"))

    def test_delete(self):
        self.mp3.delete()
        self.failIf(self.mp3.tags)
        self.failUnless(MP3(self.filename).tags is None)

    def test_module_delete(self):
        delete(self.filename)
        self.failUnless(MP3(self.filename).tags is None)

    def test_save(self):
        self.mp3["TIT1"].text = ["foobar"]
        self.mp3.save()
        self.failUnless(MP3(self.filename)["TIT1"] == "foobar")

    def test_load_non_id3(self):
        filename = os.path.join("tests", "data", "apev2-lyricsv2.mp3")
        from mutagen.apev2 import APEv2
        mp3 = MP3(filename, ID3=APEv2)
        self.failUnless("replaygain_track_peak" in mp3.tags)

    def test_add_tags(self):
        mp3 = MP3(os.path.join("tests", "data", "xing.mp3"))
        self.failIf(mp3.tags)
        mp3.add_tags()
        self.failUnless(isinstance(mp3.tags, ID3))

    def test_add_tags_already_there(self):
        mp3 = MP3(os.path.join("tests", "data", "silence-44-s.mp3"))
        self.failUnless(mp3.tags)
        self.failUnlessRaises(Exception, mp3.add_tags)

    def test_save_no_tags(self):
        self.mp3.tags = None
        self.failUnlessRaises(ValueError, self.mp3.save)

    def test_mime(self):
        self.failUnless("audio/mp3" in self.mp3.mime)
        # XXX
        self.mp3.info.layer = 2
        self.failIf("audio/mp3" in self.mp3.mime)
        self.failUnless("audio/mp2" in self.mp3.mime)

    def tearDown(self):
        os.unlink(self.filename)

add(TMP3)

class TMPEGInfo(TestCase):

    def test_not_real_file(self):
        filename = os.path.join("tests", "data", "silence-44-s-v1.mp3")
        fileobj = cBytesIO(open(filename, "rb").read(20))
        MPEGInfo(fileobj)

    def test_empty(self):
        fileobj = cBytesIO(b"")
        self.failUnlessRaises(IOError, MPEGInfo, fileobj)
add(TMPEGInfo)

class TEasyMP3(TestCase):

    def setUp(self):
        original = os.path.join("tests", "data", "silence-44-s.mp3")
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.mp3 = EasyMP3(self.filename)

    def test_artist(self):
        self.failUnless("artist" in self.mp3)

    def test_no_composer(self):
        self.failIf("composer" in self.mp3)

    def test_length(self):
        # http://code.google.com/p/mutagen/issues/detail?id=125
        # easyid3, normal id3 and mpeg loading without tags should skip
        # the tags and get the right offset of the first frame
        easy = self.mp3.info
        noneasy = MP3(self.filename).info
        nonid3 = MPEGInfo(open(self.filename, "rb"))

        self.failUnlessEqual(easy.length, noneasy.length)
        self.failUnlessEqual(noneasy.length, nonid3.length)

    def tearDown(self):
        os.unlink(self.filename)
add(TEasyMP3)

class Issue72_TooShortFile(TestCase):
    def test_load(self):
        mp3 = MP3(os.path.join('tests', 'data', 'too-short.mp3'))
        self.failUnlessEqual(mp3["TIT2"], "Track 10")
        self.failUnlessAlmostEqual(mp3.info.length, 0.03, 2)
add(Issue72_TooShortFile)
