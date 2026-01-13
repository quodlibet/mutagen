
import os
import pickle

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.easyid3 import error as ID3Error
from mutagen.id3 import CHAP, CTOC, ID3, RVA2, TDRC, ID3FileType
from tests import DATA_DIR, TestCase, get_temp_copy


class TEasyID3(TestCase):

    def setUp(self):
        self.filename = get_temp_copy(os.path.join(DATA_DIR, 'emptyfile.mp3'))
        self.id3 = EasyID3()
        self.realid3 = self.id3._EasyID3__id3

    def tearDown(self):
        os.unlink(self.filename)

    def test_size_attr(self):
        assert self.id3.size == self.realid3.size

    def test_load_filename(self):
        self.id3.save(self.filename)
        self.id3.load(self.filename)
        assert self.id3.filename == self.filename

        path = os.path.join(DATA_DIR, 'silence-44-s.mp3')
        new = EasyID3(path)
        assert new.filename == path

    def test_txxx_latin_first_then_non_latin(self):
        self.id3["performer"] = ["foo"]
        self.id3["performer"] = ["\u0243"]
        self.id3.save(self.filename)
        new = EasyID3(self.filename)
        self.assertEqual(new["performer"], ["\u0243"])

    def test_remember_ctr(self):
        empty = os.path.join(DATA_DIR, 'emptyfile.mp3')
        mp3 = ID3FileType(empty, ID3=EasyID3)
        self.assertFalse(mp3.tags)
        mp3["artist"] = ["testing"]
        self.assertTrue(mp3.tags)
        mp3.pprint()
        self.assertTrue(isinstance(mp3.tags, EasyID3))

    def test_save_23(self):
        self.id3.save(self.filename, v2_version=3)
        self.assertEqual(ID3(self.filename).version, (2, 3, 0))
        self.id3.save(self.filename, v2_version=4)
        self.assertEqual(ID3(self.filename).version, (2, 4, 0))

    def test_save_date_v23(self):
        self.id3["date"] = "2004"
        assert self.realid3.getall("TDRC")[0] == "2004"
        self.id3.save(self.filename, v2_version=3)
        assert self.realid3.getall("TDRC")[0] == "2004"
        assert not self.realid3.getall("TYER")
        new = ID3(self.filename, translate=False)
        assert new.version == (2, 3, 0)
        assert new.getall("TYER")[0] == "2004"

    def test_save_v23_error_restore(self):
        self.id3["date"] = "2004"
        with self.assertRaises(MutagenError):
            self.id3.save("", v2_version=3)
        assert self.id3["date"] == ["2004"]

    def test_save_v23_recurse_restore(self):
        self.realid3.add(CHAP(sub_frames=[TDRC(text="2006")]))
        self.realid3.add(CTOC(sub_frames=[TDRC(text="2006")]))
        self.id3.save(self.filename, v2_version=3)

        for frame_id in ["CHAP", "CTOC"]:
            chap = self.realid3.getall(frame_id)[0]
            assert chap.sub_frames.getall("TDRC")[0] == "2006"
            new = ID3(self.filename, translate=False)
            assert new.version == (2, 3, 0)
            chap = new.getall(frame_id)[0]
            assert not chap.sub_frames.getall("TDRC")
            assert chap.sub_frames.getall("TYER")[0] == "2006"

    def test_delete(self):
        self.id3["artist"] = "foobar"
        self.id3.save(self.filename)
        self.assertTrue(os.path.getsize(self.filename))
        self.id3.delete(self.filename)
        self.assertFalse(os.path.getsize(self.filename))
        self.assertFalse(self.id3)

    def test_pprint(self):
        self.id3["artist"] = "baz"
        self.id3.pprint()

    def test_in(self):
        self.assertFalse("foo" in self.id3)

    def test_empty_file(self):
        empty = os.path.join(DATA_DIR, 'emptyfile.mp3')
        self.assertRaises(ID3Error, EasyID3, filename=empty)

    def test_nonexistent_file(self):
        empty = os.path.join(DATA_DIR, 'does', 'not', 'exist')
        self.assertRaises(MutagenError, EasyID3, filename=empty)

    def test_write_single(self):
        for key in EasyID3.valid_keys:
            if (key == "date") or (key == "originaldate") or key.startswith("replaygain_"):
                continue

            # Test creation
            self.id3[key] = "a test value"
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.assertEqual(id3[key], ["a test value"])
            self.assertEqual(id3.keys(), [key])

            # And non-creation setting.
            self.id3[key] = "a test value"
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.assertEqual(id3[key], ["a test value"])
            self.assertEqual(id3.keys(), [key])

            del self.id3[key]

    def test_write_double(self):
        for key in EasyID3.valid_keys:
            if (key == "date") or (key == "originaldate") or key.startswith("replaygain_") or key == "musicbrainz_trackid":
                continue

            self.id3[key] = ["a test", "value"]
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            # some keys end up in multiple frames and ID3.getall returns
            # them in undefined order
            self.assertEqual(sorted(id3.get(key)), ["a test", "value"])
            self.assertEqual(id3.keys(), [key])

            self.id3[key] = ["a test", "value"]
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.assertEqual(sorted(id3.get(key)), ["a test", "value"])
            self.assertEqual(id3.keys(), [key])

            del self.id3[key]

    def test_write_date(self):
        self.id3["date"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["date"], ["2004"])

        self.id3["date"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["date"], ["2004"])

    def test_date_delete(self):
        self.id3["date"] = "2004"
        self.assertEqual(self.id3["date"], ["2004"])
        del self.id3["date"]
        self.assertFalse("date" in self.id3)

    def test_write_date_double(self):
        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["date"], ["2004", "2005"])

        self.id3["date"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["date"], ["2004", "2005"])

    def test_write_original_date(self):
        self.id3["originaldate"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["originaldate"], ["2004"])

        self.id3["originaldate"] = "2004"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["originaldate"], ["2004"])

    def test_original_date_delete(self):
        self.id3["originaldate"] = "2004"
        self.assertEqual(self.id3["originaldate"], ["2004"])
        del self.id3["originaldate"]
        self.assertFalse("originaldate" in self.id3)

    def test_write_original_date_double(self):
        self.id3["originaldate"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["originaldate"], ["2004", "2005"])

        self.id3["originaldate"] = ["2004", "2005"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["originaldate"], ["2004", "2005"])

    def test_write_invalid(self):
        self.assertRaises(ValueError, self.id3.__getitem__, "notvalid")
        self.assertRaises(ValueError, self.id3.__delitem__, "notvalid")
        self.assertRaises(
            ValueError, self.id3.__setitem__, "notvalid", "tests")

    def test_perfomer(self):
        self.id3["performer:coder"] = ["piman", "mu"]
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["performer:coder"], ["piman", "mu"])

    def test_no_performer(self):
        self.assertFalse("performer:foo" in self.id3)

    def test_performer_delete(self):
        self.id3["performer:foo"] = "Joe"
        self.id3["performer:bar"] = "Joe"
        self.assertTrue("performer:foo" in self.id3)
        self.assertTrue("performer:bar" in self.id3)
        del self.id3["performer:foo"]
        self.assertFalse("performer:foo" in self.id3)
        self.assertTrue("performer:bar" in self.id3)
        del self.id3["performer:bar"]
        self.assertFalse("performer:bar" in self.id3)
        self.assertFalse("TMCL" in self.realid3)

    def test_performer_delete_dne(self):
        self.assertRaises(KeyError, self.id3.__delitem__, "performer:bar")
        self.id3["performer:foo"] = "Joe"
        self.assertRaises(KeyError, self.id3.__delitem__, "performer:bar")

    def test_txxx_empty(self):
        # https://github.com/quodlibet/mutagen/issues/135
        self.id3["asin"] = ""

    def test_txxx_set_get(self):
        self.assertFalse("asin" in self.id3)
        self.id3["asin"] = "Hello"
        self.assertTrue("asin" in self.id3)
        self.assertEqual(self.id3["asin"], ["Hello"])
        self.assertTrue("TXXX:ASIN" in self.realid3)

    def test_txxx_del_set_del(self):
        self.assertFalse("asin" in self.id3)
        self.assertRaises(KeyError, self.id3.__delitem__, "asin")
        self.id3["asin"] = "Hello"
        self.assertTrue("asin" in self.id3)
        self.assertEqual(self.id3["asin"], ["Hello"])
        del self.id3["asin"]
        self.assertFalse("asin" in self.id3)
        self.assertRaises(KeyError, self.id3.__delitem__, "asin")

    def test_txxx_save(self):
        self.id3["asin"] = "Hello"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["asin"], ["Hello"])

    def test_txxx_unicode(self):
        self.id3["asin"] = "He\u1234llo"
        self.assertEqual(self.id3["asin"], ["He\u1234llo"])

    def test_bad_trackid(self):
        self.assertRaises(ValueError, self.id3.__setitem__,
                              "musicbrainz_trackid", ["a", "b"])
        self.assertFalse(self.realid3.getall("RVA2"))

    def test_gain_bad_key(self):
        self.assertFalse("replaygain_foo_gain" in self.id3)
        self.assertFalse(self.realid3.getall("RVA2"))

    def test_gain_bad_value(self):
        self.assertRaises(
            ValueError, self.id3.__setitem__, "replaygain_foo_gain", [])
        self.assertRaises(
            ValueError, self.id3.__setitem__, "replaygain_foo_gain", ["foo"])
        self.assertRaises(
            ValueError,
            self.id3.__setitem__, "replaygain_foo_gain", ["1", "2"])
        self.assertFalse(self.realid3.getall("RVA2"))

    def test_peak_bad_key(self):
        self.assertFalse("replaygain_foo_peak" in self.id3)
        self.assertFalse(self.realid3.getall("RVA2"))

    def test_peak_bad_value(self):
        self.assertRaises(
            ValueError, self.id3.__setitem__, "replaygain_foo_peak", [])
        self.assertRaises(
            ValueError, self.id3.__setitem__, "replaygain_foo_peak", ["foo"])
        self.assertRaises(
            ValueError,
            self.id3.__setitem__, "replaygain_foo_peak", ["1", "1"])
        self.assertRaises(
            ValueError, self.id3.__setitem__, "replaygain_foo_peak", ["3"])
        self.assertFalse(self.realid3.getall("RVA2"))

    def test_gain_peak_get(self):
        self.id3["replaygain_foo_gain"] = "+3.5 dB"
        self.id3["replaygain_bar_peak"] = "0.5"
        self.assertEqual(
            self.id3["replaygain_foo_gain"], ["+3.500000 dB"])
        self.assertEqual(self.id3["replaygain_foo_peak"], ["0.000000"])
        self.assertEqual(
            self.id3["replaygain_bar_gain"], ["+0.000000 dB"])
        self.assertEqual(self.id3["replaygain_bar_peak"], ["0.500000"])

    def test_gain_peak_set(self):
        self.id3["replaygain_foo_gain"] = "+3.5 dB"
        self.id3["replaygain_bar_peak"] = "0.5"
        self.id3.save(self.filename)
        id3 = EasyID3(self.filename)
        self.assertEqual(id3["replaygain_foo_gain"], ["+3.500000 dB"])
        self.assertEqual(id3["replaygain_foo_peak"], ["0.000000"])
        self.assertEqual(id3["replaygain_bar_gain"], ["+0.000000 dB"])
        self.assertEqual(id3["replaygain_bar_peak"], ["0.500000"])

    def test_gain_peak_delete(self):
        self.id3["replaygain_foo_gain"] = "+3.5 dB"
        self.id3["replaygain_bar_peak"] = "0.5"
        del self.id3["replaygain_bar_gain"]
        del self.id3["replaygain_foo_peak"]
        self.assertTrue("replaygain_foo_gain" in self.id3)
        self.assertTrue("replaygain_bar_gain" in self.id3)

        del self.id3["replaygain_foo_gain"]
        del self.id3["replaygain_bar_peak"]
        self.assertFalse("replaygain_foo_gain" in self.id3)
        self.assertFalse("replaygain_bar_gain" in self.id3)

        del self.id3["replaygain_foo_gain"]
        del self.id3["replaygain_bar_peak"]
        self.assertFalse("replaygain_foo_gain" in self.id3)
        self.assertFalse("replaygain_bar_gain" in self.id3)

    def test_gain_peak_capitalization(self):
        frame = RVA2(desc="Foo", gain=1.0, peak=1.0, channel=0)
        self.assertFalse(len(self.realid3))
        self.realid3.add(frame)
        self.assertTrue("replaygain_Foo_peak" in self.id3)
        self.assertTrue("replaygain_Foo_peak" in self.id3)
        self.assertTrue("replaygain_Foo_gain" in self.id3)
        self.assertTrue("replaygain_Foo_gain" in self.id3)

        self.id3["replaygain_Foo_gain"] = ["0.5"]
        self.id3["replaygain_Foo_peak"] = ["0.25"]

        frames = self.realid3.getall("RVA2")
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].desc, "Foo")
        self.assertEqual(frames[0].gain, 0.5)
        self.assertEqual(frames[0].peak, 0.25)

    def test_case_insensitive(self):
        self.id3["date"] = ["2004"]
        self.assertEqual(self.id3["DATE"], ["2004"])
        del self.id3["DaTe"]
        self.assertEqual(len(self.id3), 0)

        self.id3["asin"] = ["foo"]
        self.assertEqual(self.id3["Asin"], ["foo"])
        del self.id3["AsIn"]
        self.assertEqual(len(self.id3), 0)

    def test_pickle(self):
        # https://github.com/quodlibet/mutagen/issues/102
        pickle.dumps(self.id3)

    def test_get_fallback(self):
        called = []

        def get_func(id3, key):
            id3.getall("")
            self.assertEqual(key, "nope")
            called.append(1)
        self.id3.GetFallback = get_func
        self.id3["nope"]
        self.assertTrue(called)

    def test_set_fallback(self):
        called = []

        def set_func(id3, key, value):
            id3.getall("")
            self.assertEqual(key, "nope")
            self.assertEqual(value, ["foo"])
            called.append(1)
        self.id3.SetFallback = set_func
        self.id3["nope"] = "foo"
        self.assertTrue(called)

    def test_del_fallback(self):
        called = []

        def del_func(id3, key):
            id3.getall("")
            self.assertEqual(key, "nope")
            called.append(1)
        self.id3.DeleteFallback = del_func
        del self.id3["nope"]
        self.assertTrue(called)

    def test_list_fallback(self):
        def list_func(id3, key):
            id3.getall("")
            self.assertFalse(key)
            return ["somekey"]

        self.id3.ListFallback = list_func
        self.assertEqual(self.id3.keys(), ["somekey"])

    def test_text_tags(self):
        for tag in ["albumartist", "performer"]:
            self.id3[tag] = "foo"
            self.id3.save(self.filename)
            id3 = EasyID3(self.filename)
            self.assertEqual(id3[tag], ["foo"])
