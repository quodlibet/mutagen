import os
import shutil
from tempfile import mkstemp
from tests import TestCase, add

from mutagen._compat import PY3, text_type
from mutagen.asf import ASF, ASFHeaderError, ASFValue, UNICODE, DWORD, QWORD
from mutagen.asf import BOOL, WORD, BYTEARRAY, GUID
from mutagen.asf import ASFUnicodeAttribute, ASFError, ASFByteArrayAttribute, \
    ASFBoolAttribute, ASFDWordAttribute, ASFQWordAttribute, ASFWordAttribute, \
    ASFGUIDAttribute


class TASFFile(TestCase):

    def test_not_my_file(self):
        self.failUnlessRaises(
            ASFHeaderError, ASF,
            os.path.join("tests", "data", "empty.ogg"))
        self.failUnlessRaises(
            ASFHeaderError, ASF,
            os.path.join("tests", "data", "click.mpc"))

add(TASFFile)


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
        self.failUnlessEqual(self.wma1.info.bitrate // 1000, 64)
        self.failUnlessEqual(self.wma2.info.bitrate // 1000, 38)
        self.failUnlessEqual(self.wma3.info.bitrate // 1000, 58)

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
            self.failUnlessEqual(self.audio[key], result or value)

    def test_contains(self):
        self.failUnlessEqual("notatag" in self.audio.tags, False)

    def test_inval_type(self):
        self.failUnlessRaises(ValueError, ASFValue, "", 4242)

    def test_repr(self):
        repr(ASFValue(u"foo", UNICODE, stream=1, language=2))

    def test_auto_guuid(self):
        value = ASFValue(b'\x9eZl}\x89\xa2\xb5D\xb8\xa30\xfe', GUID)
        self.set_key(u"WM/WMCollectionGroupID", value, [value])

    def test_auto_unicode(self):
        self.set_key(u"WM/AlbumTitle", u"foo",
                     [ASFValue(u"foo", UNICODE)])

    def test_auto_unicode_list(self):
        self.set_key(u"WM/AlbumTitle", [u"foo", u"bar"],
                     [ASFValue(u"foo", UNICODE), ASFValue(u"bar", UNICODE)])

    def test_word(self):
        self.set_key(u"WM/Track", ASFValue(24, WORD), [ASFValue(24, WORD)])

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
        self.set_key(u"WM/Track", 12,
                     [ASFValue(12, QWORD)])

    def test_auto_qword_list(self):
        self.set_key(u"WM/Track", [12, 13],
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

    def test_data_size(self):
        v = ASFValue("", UNICODE, data=b'4\xd8\x1e\xdd\x00\x00')
        self.failUnlessEqual(v.data_size(), len(v._render()))


class TASFAttributes(TestCase):

    def test_ASFUnicodeAttribute(self):
        if PY3:
            self.assertRaises(TypeError, ASFUnicodeAttribute, b"\xff")
        else:
            self.assertRaises(ValueError, ASFUnicodeAttribute, b"\xff")
            val = u'\xf6\xe4\xfc'
            self.assertEqual(ASFUnicodeAttribute(val.encode("utf-8")), val)

        self.assertRaises(ASFError, ASFUnicodeAttribute, data=b"\x00")
        self.assertEqual(ASFUnicodeAttribute(u"foo").value, u"foo")
        self.assertEqual(
            bytes(ASFUnicodeAttribute(u"foo")), b"f\x00o\x00o\x00")
        self.assertEqual(
            text_type(ASFUnicodeAttribute(u"foo")), u"foo")

    def test_ASFByteArrayAttribute(self):
        self.assertEqual(ASFByteArrayAttribute(data=b"\xff").value, b"\xff")
        self.assertRaises(TypeError, ASFByteArrayAttribute, u"foo")

    def test_compat(self):
        ba = ASFByteArrayAttribute()
        ba.value = b"\xff"
        self.assertEqual(ba._render(), b"\xff")

    def test_ASFGUIDAttribute(self):
        self.assertEqual(ASFGUIDAttribute(data=b"\xff").value, b"\xff")
        self.assertRaises(TypeError, ASFGUIDAttribute, u"foo")

    def test_ASFBoolAttribute(self):
        self.assertEqual(
            ASFBoolAttribute(data=b"\x01\x00\x00\x00").value, True)
        self.assertEqual(
            ASFBoolAttribute(data=b"\x00\x00\x00\x00").value, False)
        self.assertEqual(ASFBoolAttribute(False).value, False)

    def test_ASFWordAttribute(self):
        self.assertEqual(
            ASFWordAttribute(data=b"\x00" * 2).value, 0)
        self.assertEqual(
            ASFWordAttribute(data=b"\xff" * 2).value, 2 ** 16 - 1)
        self.assertRaises(ValueError, ASFWordAttribute, -1)
        self.assertRaises(ValueError, ASFWordAttribute, 2 ** 16)

    def test_ASFDWordAttribute(self):
        self.assertEqual(
            ASFDWordAttribute(data=b"\x00" * 4).value, 0)
        self.assertEqual(
            ASFDWordAttribute(data=b"\xff" * 4).value, 2 ** 32 - 1)
        self.assertRaises(ValueError, ASFDWordAttribute, -1)
        self.assertRaises(ValueError, ASFDWordAttribute, 2 ** 32)

    def test_ASFQWordAttribute(self):
        self.assertEqual(
            ASFQWordAttribute(data=b"\x00" * 8).value, 0)
        self.assertEqual(
            ASFQWordAttribute(data=b"\xff" * 8).value, 2 ** 64 - 1)
        self.assertRaises(ValueError, ASFQWordAttribute, -1)
        self.assertRaises(ValueError, ASFQWordAttribute, 2 ** 64)


add(TASFAttributes)


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
        audio["QL/LargeObject"] = [ASFValue(b"." * 0xFFFF, BYTEARRAY)]
        audio.save()
        self.failIf(
            "QL/LargeObject" not in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" in dict(audio.to_metadata_library))

    def test_save_large_bytearray(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue(b"." * (0xFFFF + 1), BYTEARRAY)]
        audio.save()
        self.failIf("QL/LargeObject" in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" not in dict(audio.to_metadata_library))

    def test_save_small_string(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * (0x7FFF - 1), UNICODE)]
        audio.save()
        self.failIf(
            "QL/LargeObject" not in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" in dict(audio.to_metadata_library))

    def test_save_large_string(self):
        audio = ASF(self.filename)
        audio["QL/LargeObject"] = [ASFValue("." * 0x7FFF, UNICODE)]
        audio.save()
        self.failIf("QL/LargeObject" in audio.to_extended_content_description)
        self.failIf("QL/LargeObject" in audio.to_metadata)
        self.failIf("QL/LargeObject" not in dict(audio.to_metadata_library))

    def test_save_guid(self):
        # http://code.google.com/p/mutagen/issues/detail?id=81
        audio = ASF(self.filename)
        audio["QL/GuidObject"] = [ASFValue(b" " * 16, GUID)]
        audio.save()
        self.failIf("QL/GuidObject" in audio.to_extended_content_description)
        self.failIf("QL/GuidObject" in audio.to_metadata)
        self.failIf("QL/GuidObject" not in dict(audio.to_metadata_library))

add(TASFLargeValue)


class TASFUpdateSize(TestCase):
    # http://code.google.com/p/mutagen/issues/detail?id=81#c4

    original = os.path.join("tests", "data", "silence-1.wma")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='wma')
        os.close(fd)
        shutil.copy(self.original, self.filename)
        audio = ASF(self.filename)
        audio["large_value1"] = "#" * 50000
        audio.save()

    def tearDown(self):
        os.unlink(self.filename)

    def test_multiple_delete(self):
        audio = ASF(self.filename)
        for tag in audio.keys():
            del(audio[tag])
            audio.save()

add(TASFUpdateSize)
