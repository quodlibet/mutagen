import os
import shutil
from tempfile import mkstemp
from tests import TestCase, add
from mutagen.asf import ASF, ASFHeaderError, ASFValue, UNICODE, DWORD, QWORD
from mutagen.asf import BOOL, WORD, BYTEARRAY

class TASFFile(TestCase):

    def test_not_my_file(self):
        self.failUnlessRaises(
            ASFHeaderError, ASF,
            os.path.join("tests", "data", "empty.ogg"))
        self.failUnlessRaises(
            ASFHeaderError, ASF,
            os.path.join("tests", "data", "click.mpc"))

add(TASFFile)

try: sorted
except NameError:
    def sorted(l):
        n = list(l)
        n.sort()
        return n

class TASFInfo(TestCase):

    def setUp(self):
        # WMA 9.1 64kbps CBR 48khz
        self.wma1 = ASF(os.path.join("tests", "data", "silence-1.wma"))
        # WMA 9.1 Professional 192kbps VBR 44khz
        self.wma2 = ASF(os.path.join("tests", "data", "silence-2.wma"))
        # WMA 9.1 Lossless 44khz
        self.wma3 = ASF(os.path.join("tests", "data", "silence-3.wma"))

    def test_length(self):
        self.failUnlessAlmostEqual(self.wma1.info.length, 3.7, 1)
        self.failUnlessAlmostEqual(self.wma2.info.length, 3.7, 1)
        self.failUnlessAlmostEqual(self.wma3.info.length, 3.7, 1)

    def test_bitrate(self):
        self.failUnlessEqual(self.wma1.info.bitrate / 1000, 64)
        self.failUnlessEqual(self.wma2.info.bitrate / 1000, 38)
        self.failUnlessEqual(self.wma3.info.bitrate / 1000, 58)

    def test_sample_rate(self):
        self.failUnlessEqual(self.wma1.info.sample_rate, 48000)
        self.failUnlessEqual(self.wma2.info.sample_rate, 44100)
        self.failUnlessEqual(self.wma3.info.sample_rate, 44100)

    def test_channels(self):
        self.failUnlessEqual(self.wma1.info.channels, 2)
        self.failUnlessEqual(self.wma2.info.channels, 2)
        self.failUnlessEqual(self.wma3.info.channels, 2)

add(TASFInfo)

class TASF(TestCase):

    def setUp(self):
        fd, self.filename = mkstemp(suffix='wma')
        os.close(fd)
        shutil.copy(self.original, self.filename)
        self.audio = ASF(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_pprint(self):
        self.failUnless(self.audio.pprint())

    def set_key(self, key, value, result=None, expected=True):
        self.audio[key] = value
        self.audio.save()
        self.audio = ASF(self.audio.filename)
        self.failUnless(key in self.audio)
        self.failUnless(key in self.audio.tags)
        self.failUnless(key in self.audio.tags.keys())
        self.failUnless(key in self.audio.tags.as_dict().keys())
        newvalue = self.audio[key]
        if isinstance(newvalue, list):
            for a, b in zip(sorted(newvalue), sorted(result or value)):
                self.failUnlessEqual(a, b)
        else:
            self.failUnlessEqual(audio[key], result or value)

    def test_auto_unicode(self):
        self.set_key(u"WM/AlbumTitle", u"foo",
                     [ASFValue(u"foo", UNICODE)])

    def test_auto_unicode_list(self):
        self.set_key(u"WM/AlbumTitle", [u"foo", u"bar"],
                     [ASFValue(u"foo", UNICODE), ASFValue(u"bar", UNICODE)])

    def test_auto_word(self):
        self.set_key(u"WM/Track", 12,
                     [ASFValue(12, DWORD)])

    def test_auto_word_list(self):
        self.set_key(u"WM/Track", [12, 13],
                     [ASFValue(12, WORD), ASFValue(13, WORD)])

    def test_auto_dword(self):
        self.set_key(u"WM/Track", 12,
                     [ASFValue(12, DWORD)])

    def test_auto_dword_list(self):
        self.set_key(u"WM/Track", [12, 13],
                     [ASFValue(12, DWORD), ASFValue(13, DWORD)])

    def test_auto_qword(self):
        self.set_key(u"WM/Track", 12L,
                     [ASFValue(12, QWORD)])

    def test_auto_qword_list(self):
        self.set_key(u"WM/Track", [12L, 13L],
                     [ASFValue(12, QWORD), ASFValue(13, QWORD)])

    def test_auto_bool(self):
        self.set_key(u"IsVBR", True,
                     [ASFValue(True, BOOL)])

    def test_auto_bool_list(self):
        self.set_key(u"IsVBR", [True, False],
                     [ASFValue(True, BOOL), ASFValue(False, BOOL)])

    def test_basic_tags(self):
        self.set_key("Title", "Wheeee", ["Wheeee"])
        self.set_key("Author", "Whoooo", ["Whoooo"])
        self.set_key("Copyright", "Whaaaa", ["Whaaaa"])
        self.set_key("Description", "Wii", ["Wii"])
        self.set_key("Rating", "5", ["5"])

    def test_stream(self):
        self.audio["QL/OneHasStream"] = [
            ASFValue("Whee", UNICODE, stream=2),
            ASFValue("Whee", UNICODE),
            ]
        self.audio["QL/AllHaveStream"] = [
            ASFValue("Whee", UNICODE, stream=1),
            ASFValue("Whee", UNICODE, stream=2),
            ]
        self.audio["QL/NoStream"] = ASFValue("Whee", UNICODE)
        self.audio.save()
        self.audio = ASF(self.audio.filename)
        self.failUnlessEqual(self.audio["QL/NoStream"][0].stream, None)
        self.failUnlessEqual(self.audio["QL/OneHasStream"][0].stream, 2)
        self.failUnlessEqual(self.audio["QL/OneHasStream"][1].stream, None)
        self.failUnlessEqual(self.audio["QL/AllHaveStream"][0].stream, 1)
        self.failUnlessEqual(self.audio["QL/AllHaveStream"][1].stream, 2)

    def test_language(self):
        self.failIf("QL/OneHasLang" in self.audio)
        self.failIf("QL/AllHaveLang" in self.audio)
        self.audio["QL/OneHasLang"] = [
            ASFValue("Whee", UNICODE, language=2),
            ASFValue("Whee", UNICODE),
            ]
        self.audio["QL/AllHaveLang"] = [
            ASFValue("Whee", UNICODE, language=1),
            ASFValue("Whee", UNICODE, language=2),
            ]
        self.audio["QL/NoLang"] = ASFValue("Whee", UNICODE)
        self.audio.save()
        self.audio = ASF(self.audio.filename)
        self.failUnlessEqual(self.audio["QL/NoLang"][0].language, None)
        self.failUnlessEqual(self.audio["QL/OneHasLang"][0].language, 2)
        self.failUnlessEqual(self.audio["QL/OneHasLang"][1].language, None)
        self.failUnlessEqual(self.audio["QL/AllHaveLang"][0].language, 1)
        self.failUnlessEqual(self.audio["QL/AllHaveLang"][1].language, 2)

    def test_lang_and_stream_mix(self):
        self.audio["QL/Mix"] = [
            ASFValue("Whee", UNICODE, stream=1),
            ASFValue("Whee", UNICODE, language=2),
            ASFValue("Whee", UNICODE, stream=3, language=4),
            ASFValue("Whee", UNICODE),
            ]
        self.audio.save()
        self.audio = ASF(self.audio.filename)
        self.failUnlessEqual(self.audio["QL/Mix"][0].language, None)
        self.failUnlessEqual(self.audio["QL/Mix"][0].stream, 1)
        self.failUnlessEqual(self.audio["QL/Mix"][1].language, 2)
        self.failUnlessEqual(self.audio["QL/Mix"][1].stream, 0)
        self.failUnlessEqual(self.audio["QL/Mix"][2].language, 4)
        self.failUnlessEqual(self.audio["QL/Mix"][2].stream, 3)
        self.failUnlessEqual(self.audio["QL/Mix"][3].language, None)
        self.failUnlessEqual(self.audio["QL/Mix"][3].stream, None)

class TASFTags1(TASF):
    original = os.path.join("tests", "data", "silence-1.wma")
add(TASFTags1)

class TASFTags2(TASF):
    original = os.path.join("tests", "data", "silence-2.wma")
add(TASFTags2)

class TASFTags3(TASF):
    original = os.path.join("tests", "data", "silence-3.wma")
add(TASFTags3)

class TASFIssue29(TestCase):
    original = os.path.join("tests", "data", "issue_29.wma")
    def setUp(self):
        fd, self.filename = mkstemp(suffix='wma')
        os.close(fd)
        shutil.copy(self.original, self.filename)
        self.audio = ASF(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_issue_29_description(self):
        self.audio["Description"] = "Hello"
        self.audio.save()
        audio = ASF(self.filename)
        self.failUnless("Description" in audio)
        self.failUnlessEqual(audio["Description"], ["Hello"])
        del(audio["Description"])
        self.failIf("Description" in audio)
        audio.save()
        audio = ASF(self.filename)
        self.failIf("Description" in audio)
add(TASFIssue29)

class TASFLargeValue(TestCase):

    original = os.path.join("tests", "data", "silence-1.wma")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='wma')
        os.close(fd)
        shutil.copy(self.original, self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_save_small_bytearray(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * 0xFFFF, BYTEARRAY)]
        audio.save()
        self.failIf("QL/LargeObject" not in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" in dict(audio.to_metadata_library))

    def test_save_large_bytearray(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * (0xFFFF + 1), BYTEARRAY)]
        audio.save()
        self.failIf("QL/LargeObject" in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" not in dict(audio.to_metadata_library))

    def test_save_small_string(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * (0x7FFF - 1), UNICODE)]
        audio.save()
        self.failIf("QL/LargeObject" not in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" in dict(audio.to_metadata_library))

    def test_save_large_string(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * 0x7FFF, UNICODE)]
        audio.save()
        self.failIf("QL/LargeObject" in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" not in dict(audio.to_metadata_library))

add(TASFLargeValue)

