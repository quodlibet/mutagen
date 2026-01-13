
import os

import mutagen.apev2
from mutagen import MutagenError
from mutagen.apev2 import APEBadItemError, APEv2, APEv2File, is_valid_apev2_key
from mutagen.apev2 import error as APEv2Error
from tests import DATA_DIR, TestCase, get_temp_copy, get_temp_empty

SAMPLE = os.path.join(DATA_DIR, "click.mpc")
OLD = os.path.join(DATA_DIR, "oldtag.apev2")
BROKEN = os.path.join(DATA_DIR, "brokentag.apev2")


class Tis_valid_apev2_key(TestCase):

    def test_yes(self):
        for key in ["foo", "Foo", "   f ~~~"]:
            self.assertTrue(is_valid_apev2_key(key))

    def test_no(self):
        for key in ["\x11hi", "ffoo\xFF", "\u1234", "a", "", "foo" * 100]:
            self.assertFalse(is_valid_apev2_key(key))

    def test_py3(self):
        self.assertRaises(TypeError, is_valid_apev2_key, b"abc")


class TAPEInvalidItemCount(TestCase):
    # https://github.com/quodlibet/mutagen/issues/145

    def test_load(self):
        x = mutagen.apev2.APEv2(
            os.path.join(DATA_DIR, "145-invalid-item-count.apev2"))
        self.assertEqual(len(x.keys()), 17)


class TAPEWriter(TestCase):
    offset = 0

    def setUp(self):
        self.sample_new = get_temp_copy(SAMPLE)
        self.broken_new = get_temp_copy(BROKEN)

        tag = mutagen.apev2.APEv2()
        self.values = {"artist": "Joe Wreschnig\0unittest",
                       "album": "Mutagen tests",
                       "title": "Not really a song"}
        for k, v in self.values.items():
            tag[k] = v
        tag.save(self.sample_new)
        self.just_tag = get_temp_empty()
        tag.save(self.just_tag)
        self.tag_at_start = get_temp_empty()
        tag.save(self.tag_at_start)
        with open(self.tag_at_start, "ab") as fileobj:
            fileobj.write(b"tag garbage" * 1000)

        self.tag = mutagen.apev2.APEv2(self.sample_new)

    def tearDown(self):
        os.unlink(self.sample_new)
        os.unlink(self.broken_new)
        os.unlink(self.just_tag)
        os.unlink(self.tag_at_start)

    def test_changed(self):
        size = os.path.getsize(self.sample_new)
        self.tag.save()
        self.assertEqual(
            os.path.getsize(self.sample_new), size - self.offset)

    def test_fix_broken(self):
        # Clean up garbage from a bug in pre-Mutagen APEv2.
        # This also tests removing ID3v1 tags on writes.
        self.assertNotEqual(os.path.getsize(OLD), os.path.getsize(BROKEN))
        tag = mutagen.apev2.APEv2(BROKEN)
        tag.save(self.broken_new)
        self.assertEqual(
            os.path.getsize(OLD), os.path.getsize(self.broken_new))

    def test_readback(self):
        for k, v in self.tag.items():
            self.assertEqual(str(v), self.values[k])

    def test_size(self):
        self.assertEqual(
            os.path.getsize(self.sample_new),
            os.path.getsize(SAMPLE) + os.path.getsize(self.just_tag))

    def test_delete(self):
        mutagen.apev2.delete(self.just_tag)
        tag = mutagen.apev2.APEv2(self.sample_new)
        tag.delete()
        self.assertEqual(os.path.getsize(self.just_tag), self.offset)
        self.assertEqual(os.path.getsize(SAMPLE) + self.offset,
                             os.path.getsize(self.sample_new))
        self.assertFalse(tag)

    def test_empty(self):
        self.assertRaises(
            APEv2Error, mutagen.apev2.APEv2,
            os.path.join(DATA_DIR, "emptyfile.mp3"))

    def test_tag_at_start(self):
        tag = mutagen.apev2.APEv2(self.tag_at_start)
        self.assertEqual(tag["album"], "Mutagen tests")

    def test_tag_at_start_write(self):
        filename = self.tag_at_start
        tag = mutagen.apev2.APEv2(filename)
        tag.save()
        tag = mutagen.apev2.APEv2(filename)
        self.assertEqual(tag["album"], "Mutagen tests")
        self.assertEqual(
            os.path.getsize(self.just_tag),
            os.path.getsize(filename) - (len("tag garbage") * 1000))

    def test_tag_at_start_delete(self):
        filename = self.tag_at_start
        tag = mutagen.apev2.APEv2(filename)
        tag.delete()
        self.assertRaises(APEv2Error, mutagen.apev2.APEv2, filename)
        self.assertEqual(
            os.path.getsize(filename), len("tag garbage") * 1000)

    def test_case_preservation(self):
        mutagen.apev2.delete(self.just_tag)
        tag = mutagen.apev2.APEv2(self.sample_new)
        tag["FoObaR"] = "Quux"
        tag.save()
        tag = mutagen.apev2.APEv2(self.sample_new)
        self.assertTrue("FoObaR" in tag)
        self.assertFalse("foobar" in tag)

    def test_unicode_key(self):
        # https://github.com/quodlibet/mutagen/issues/123
        tag = mutagen.apev2.APEv2(self.sample_new)
        tag["abc"] = '\xf6\xe4\xfc'
        tag["cba"] = "abc"
        tag.save()

    def test_save_sort_is_deterministic(self):
        tag = mutagen.apev2.APEv2(self.sample_new)
        tag["cba"] = "my cba value"
        tag["abc"] = "my abc value"
        tag.save()
        with open(self.sample_new, 'rb') as fobj:
            content = fobj.read()
            self.assertTrue(content.index(b"abc") < content.index(b"cba"))


class TAPEv2ThenID3v1Writer(TAPEWriter):
    offset = 128

    def setUp(self):
        super().setUp()
        with open(self.sample_new, "ab+") as f:
            f.write(b"TAG" + b"\x00" * 125)
        with open(self.broken_new, "ab+") as f:
            f.write(b"TAG" + b"\x00" * 125)
        with open(self.just_tag, "ab+") as f:
            f.write(b"TAG" + b"\x00" * 125)

    def test_tag_at_start_write(self):
        pass


class TAPEv2(TestCase):

    def setUp(self):
        self.filename = get_temp_copy(OLD)
        self.audio = APEv2(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_invalid_key(self):
        self.assertRaises(
            KeyError, self.audio.__setitem__, "\u1234", "foo")

    def test_guess_text(self):
        from mutagen.apev2 import APETextValue
        self.audio["test"] = "foobar"
        self.assertEqual(self.audio["test"], "foobar")
        self.assertTrue(isinstance(self.audio["test"], APETextValue))

    def test_guess_text_list(self):
        from mutagen.apev2 import APETextValue
        self.audio["test"] = ["foobar", "quuxbarz"]
        self.assertEqual(self.audio["test"], "foobar\x00quuxbarz")
        self.assertTrue(isinstance(self.audio["test"], APETextValue))

    def test_guess_utf8(self):
        from mutagen.apev2 import APETextValue
        self.audio["test"] = "foobar"
        self.assertEqual(self.audio["test"], "foobar")
        self.assertTrue(isinstance(self.audio["test"], APETextValue))

    def test_guess_not_utf8(self):
        from mutagen.apev2 import APEBinaryValue
        self.audio["test"] = b"\xa4woo"
        self.assertTrue(isinstance(self.audio["test"], APEBinaryValue))
        self.assertEqual(4, len(self.audio["test"]))

    def test_bad_value_type(self):
        from mutagen.apev2 import APEValue
        self.assertRaises(ValueError, APEValue, "foo", 99)

    def test_module_delete_empty(self):
        from mutagen.apev2 import delete
        delete(os.path.join(DATA_DIR, "emptyfile.mp3"))

    def test_invalid(self):
        self.assertRaises(MutagenError, mutagen.apev2.APEv2, "dne")

    def test_no_tag(self):
        self.assertRaises(MutagenError, mutagen.apev2.APEv2,
                              os.path.join(DATA_DIR, "empty.mp3"))

    def test_cases(self):
        self.assertEqual(self.audio["artist"], self.audio["ARTIST"])
        self.assertTrue("artist" in self.audio)
        self.assertTrue("artisT" in self.audio)

    def test_keys(self):
        self.assertTrue("Track" in self.audio)
        self.assertTrue("AnArtist" in self.audio.values())

        self.assertEqual(
            self.audio.items(),
            list(zip(self.audio.keys(), self.audio.values(), strict=False)))

    def test_key_type(self):
        key = self.audio.keys()[0]
        self.assertTrue(isinstance(key, str))

    def test_invalid_keys(self):
        self.assertRaises(KeyError, self.audio.__getitem__, "\x00")
        self.assertRaises(KeyError, self.audio.__setitem__, "\x00", "")
        self.assertRaises(KeyError, self.audio.__delitem__, "\x00")

    def test_dictlike(self):
        self.assertTrue(self.audio.get("track"))
        self.assertTrue(self.audio.get("Track"))

    def test_del(self):
        s = self.audio["artist"]
        del self.audio["artist"]
        self.assertFalse("artist" in self.audio)
        self.assertRaises(KeyError, self.audio.__getitem__, "artist")
        self.audio["Artist"] = s
        self.assertEqual(self.audio["artist"], "AnArtist")

    def test_values(self):
        self.assertEqual(self.audio["artist"], self.audio["artist"])
        self.assertTrue(self.audio["artist"] < self.audio["title"])
        self.assertEqual(self.audio["artist"], "AnArtist")
        self.assertEqual(self.audio["title"], "Some Music")
        self.assertEqual(self.audio["album"], "A test case")
        self.assertEqual("07", self.audio["track"])

        self.assertNotEqual(self.audio["album"], "A test Case")

    def test_pprint(self):
        self.assertTrue(self.audio.pprint())


class TAPEv2ThenID3v1(TAPEv2):

    def setUp(self):
        super().setUp()
        f = open(self.filename, "ab+")
        f.write(b"TAG" + b"\x00" * 125)
        f.close()
        self.audio = APEv2(self.filename)


class TAPEv2WithLyrics2(TestCase):

    def setUp(self):
        self.tag = mutagen.apev2.APEv2(
            os.path.join(DATA_DIR, "apev2-lyricsv2.mp3"))

    def test_values(self):
        self.assertEqual(self.tag["MP3GAIN_MINMAX"], "000,179")
        self.assertEqual(self.tag["REPLAYGAIN_TRACK_GAIN"], "-4.080000 dB")
        self.assertEqual(self.tag["REPLAYGAIN_TRACK_PEAK"], "1.008101")


class TAPEBinaryValue(TestCase):

    from mutagen.apev2 import APEBinaryValue as BV
    BV = BV

    def setUp(self):
        self.sample = b"\x12\x45\xde"
        self.value = mutagen.apev2.APEValue(self.sample, mutagen.apev2.BINARY)

    def test_type(self):
        self.assertTrue(isinstance(self.value, self.BV))

    def test_const(self):
        self.assertEqual(self.sample, bytes(self.value))

    def test_repr(self):
        repr(self.value)

    def test_pprint(self):
        self.assertEqual(self.value.pprint(), "[3 bytes]")

    def test_type2(self):
        self.assertRaises(TypeError,
                          mutagen.apev2.APEValue, "abc", mutagen.apev2.BINARY)


class TAPETextValue(TestCase):

    from mutagen.apev2 import APETextValue as TV
    TV = TV

    def setUp(self):
        self.sample = ["foo", "bar", "baz"]
        self.value = mutagen.apev2.APEValue(
            "\0".join(self.sample), mutagen.apev2.TEXT)

    def test_parse(self):
        self.assertRaises(APEBadItemError, self.TV._new, b"\xff")

    def test_type(self):
        self.assertTrue(isinstance(self.value, self.TV))

    def test_construct(self):
        self.assertEqual(str(self.TV("foo")), "foo")

    def test_list(self):
        self.assertEqual(self.sample, list(self.value))

    def test_setitem_list(self):
        self.value[2] = self.sample[2] = 'quux'
        self.test_list()
        self.test_getitem()
        self.value[2] = self.sample[2] = 'baz'

    def test_getitem(self):
        for i in range(len(self.value)):
            self.assertEqual(self.sample[i], self.value[i])

    def test_delitem(self):
        del self.sample[1]
        self.assertEqual(list(self.sample), ["foo", "baz"])
        del self.sample[1:]
        self.assertEqual(list(self.sample), ["foo"])

    def test_insert(self):
        self.sample.insert(0, "a")
        self.assertEqual(len(self.sample), 4)
        self.assertEqual(self.sample[0], "a")
        self.assertRaises(TypeError, self.value.insert, 2, b"abc")

    def test_types(self):
        self.assertRaises(TypeError, self.value.__setitem__, 2, b"abc")
        self.assertRaises(
            TypeError, mutagen.apev2.APEValue, b"abc", mutagen.apev2.TEXT)

    def test_repr(self):
        repr(self.value)

    def test_str(self):
        self.assertEqual(str(self.value), "foo\x00bar\x00baz")

    def test_pprint(self):
        self.assertEqual(self.value.pprint(), "foo / bar / baz")


class TAPEExtValue(TestCase):

    from mutagen.apev2 import APEExtValue as EV
    EV = EV

    def setUp(self):
        self.sample = "http://foo"
        self.value = mutagen.apev2.APEValue(
            self.sample, mutagen.apev2.EXTERNAL)

    def test_type(self):
        self.assertTrue(isinstance(self.value, self.EV))

    def test_const(self):
        self.assertEqual(self.sample, self.value)

    def test_repr(self):
        repr(self.value)

    def test_py3(self):
        self.assertRaises(
            TypeError, mutagen.apev2.APEValue, b"abc",
            mutagen.apev2.EXTERNAL)

    def test_pprint(self):
        self.assertEqual(self.value.pprint(), "[External] http://foo")


class TAPEv2File(TestCase):

    def setUp(self):
        self.audio = APEv2File(os.path.join(DATA_DIR, "click.mpc"))

    def test_empty(self):
        f = APEv2File(os.path.join(DATA_DIR, "xing.mp3"))
        self.assertFalse(f.items())

    def test_add_tags(self):
        self.assertTrue(self.audio.tags is None)
        self.audio.add_tags()
        self.assertTrue(self.audio.tags is not None)
        self.assertRaises(APEv2Error, self.audio.add_tags)

    def test_unknown_info(self):
        info = self.audio.info
        info.pprint()
