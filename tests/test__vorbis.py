
from mutagen._vorbis import VComment, VCommentDict, error, istag
from tests import TestCase


class Tistag(TestCase):

    def test_empty(self):
        self.assertFalse(istag(""))

    def test_tilde(self):
        self.assertFalse(istag("ti~tle"))

    def test_equals(self):
        self.assertFalse(istag("ti=tle"))

    def test_less(self):
        self.assertFalse(istag("ti\x19tle"))

    def test_greater(self):
        self.assertFalse(istag("ti\xa0tle"))

    def test_simple(self):
        self.assertTrue(istag("title"))

    def test_space(self):
        self.assertTrue(istag("ti tle"))

    def test_ugly(self):
        self.assertTrue(istag("!{}[]-_()*&"))

    def test_unicode(self):
        self.assertTrue(istag("ti tle"))

    def test_py3(self):
        self.assertRaises(TypeError, istag, b"abc")


class TVComment(TestCase):

    def setUp(self):
        self.c = VComment()
        self.c.append(("artist", "piman"))
        self.c.append(("artist", "mu"))
        self.c.append(("title", "more fakes"))

    def test_invalid_init(self):
        self.assertRaises(TypeError, VComment, [])

    def test_equal(self):
        self.assertEqual(self.c, self.c)

    def test_not_header(self):
        self.assertRaises(error, VComment, b"foo")

    def test_unset_framing_bit(self):
        self.assertRaises(
            error, VComment, b"\x00\x00\x00\x00" * 2 + b"\x00")

    def test_empty_valid(self):
        self.assertFalse(VComment(b"\x00\x00\x00\x00" * 2 + b"\x01"))

    def test_validate(self):
        self.assertTrue(self.c.validate())

    def test_validate_broken_key(self):
        self.c.append((1, "valid"))
        self.assertRaises(ValueError, self.c.validate)
        self.assertRaises(ValueError, self.c.write)

    def test_validate_broken_value(self):
        self.c.append(("valid", 1))
        self.assertRaises(ValueError, self.c.validate)
        self.assertRaises(ValueError, self.c.write)

    def test_validate_nonunicode_value(self):
        self.c.append(("valid", b"wt\xff"))
        self.assertRaises(ValueError, self.c.validate)
        self.assertRaises(ValueError, self.c.write)

    def test_vendor_default(self):
        self.assertTrue(self.c.vendor.startswith("Mutagen"))

    def test_vendor_set(self):
        self.c.vendor = "Not Mutagen"
        self.assertTrue(self.c.write()[4:].startswith(b"Not Mutagen"))

    def test_vendor_invalid(self):
        self.c.vendor = b"\xffNot Mutagen"
        self.assertRaises(ValueError, self.c.validate)
        self.assertRaises(ValueError, self.c.write)

    def test_validate_utf8_value(self):
        self.c.append(("valid", b"\xc3\xbc\xc3\xb6\xc3\xa4"))
        self.assertRaises(ValueError, self.c.validate)

    def test_invalid_format_strict(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                b'\x00abc\x01')
        self.assertRaises(error, VComment, data, errors='strict')

    def test_invalid_format_replace(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                b'\x00abc\x01')
        comment = VComment(data)
        self.assertEqual("abc", comment[0][1])

    def test_python_key_value_type(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                b'\x00abc\x01')
        comment = VComment(data)
        self.assertTrue(isinstance(comment[0][0], str))
        self.assertTrue(isinstance(comment[0][1], str))

    def test_python3_strict_str(self):
        comment = VComment()
        comment.append(("abc", "test"))
        comment.validate()
        comment[0] = ("abc", b"test")
        self.assertRaises(ValueError, comment.validate)
        comment[0] = (b"abc", "test")
        self.assertRaises(ValueError, comment.validate)

    def test_invalid_format_ignore(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                b'\x00abc\x01')
        comment = VComment(data, errors='ignore')
        self.assertFalse(len(comment))

    # Slightly different test data than above, we want the tag name
    # to be valid UTF-8 but not valid ASCII.
    def test_invalid_tag_strict(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                b'\x00\xc2\xaa=c\x01')
        self.assertRaises(error, VComment, data, errors='strict')

    def test_invalid_tag_replace(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                b'\x00\xc2\xaa=c\x01')
        comment = VComment(data)
        self.assertEqual("?=c", comment.pprint())

    def test_invalid_tag_ignore(self):
        data = (b'\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                b'\x00\xc2\xaa=c\x01')
        comment = VComment(data, errors='ignore')
        self.assertFalse(len(comment))

    def test_roundtrip(self):
        self.assertReallyEqual(self.c, VComment(self.c.write()))


class TVCommentDict(TestCase):

    Kind = VCommentDict

    def setUp(self):
        self.c = self.Kind()
        self.c["artist"] = ["mu", "piman"]
        self.c["title"] = "more fakes"

    def test_correct_len(self):
        self.assertEqual(len(self.c), 3)

    def test_keys(self):
        self.assertTrue("artist" in self.c)
        self.assertTrue("title" in self.c)

    def test_values(self):
        self.assertTrue(["mu", "piman"] in self.c.values())
        self.assertTrue(["more fakes"] in self.c.values())

    def test_items(self):
        self.assertTrue(("artist", ["mu", "piman"]) in self.c.items())
        self.assertTrue(("title", ["more fakes"]) in self.c.items())

    def test_equal(self):
        self.assertEqual(self.c, self.c)

    def test_get(self):
        self.assertEqual(self.c["artist"], ["mu", "piman"])
        self.assertEqual(self.c["title"], ["more fakes"])

    def test_set(self):
        self.c["woo"] = "bar"
        self.assertEqual(self.c["woo"], ["bar"])

    def test_slice(self):
        l = [("foo", "bar"), ("foo", "bar2")]
        self.c[:] = l
        self.assertEqual(self.c[:], l)
        self.assertEqual(self.c["foo"], ["bar", "bar2"])
        del self.c[:]
        self.assertEqual(self.c[:], [])

    def test_iter(self):
        self.assertEqual(next(iter(self.c)), ("artist", "mu"))
        self.assertEqual(list(self.c)[0], ("artist", "mu"))

    def test_del(self):
        del self.c["title"]
        self.assertRaises(KeyError, self.c.__getitem__, "title")

    def test_contains(self):
        self.assertFalse("foo" in self.c)
        self.assertTrue("title" in self.c)

    def test_get_case(self):
        self.assertEqual(self.c["ARTIST"], ["mu", "piman"])

    def test_set_case(self):
        self.c["TITLE"] = "another fake"
        self.assertEqual(self.c["title"], ["another fake"])

    def test_set_preserve_case(self):
        del self.c["title"]
        self.c["TiTlE"] = "blah"
        self.assertTrue(("TiTlE", "blah") in list(self.c))
        self.assertTrue("title" in self.c)

    def test_contains_case(self):
        self.assertTrue("TITLE" in self.c)

    def test_del_case(self):
        del self.c["TITLE"]
        self.assertRaises(KeyError, self.c.__getitem__, "title")

    def test_get_failure(self):
        self.assertRaises(KeyError, self.c.__getitem__, "woo")

    def test_del_failure(self):
        self.assertRaises(KeyError, self.c.__delitem__, "woo")

    def test_roundtrip(self):
        self.assertEqual(self.c, self.Kind(self.c.write()))

    def test_roundtrip_vc(self):
        self.assertEqual(self.c, VComment(self.c.write()))

    def test_case_items_426(self):
        self.c.append(("WOO", "bar"))
        self.assertTrue(("woo", ["bar"]) in self.c.items())

    def test_empty(self):
        self.c = VCommentDict()
        self.assertFalse(list(self.c.keys()))
        self.assertFalse(list(self.c.values()))
        self.assertFalse(list(self.c.items()))

    def test_as_dict(self):
        d = self.c.as_dict()
        self.assertTrue("artist" in d)
        self.assertTrue("title" in d)
        self.assertEqual(d["artist"], self.c["artist"])
        self.assertEqual(d["title"], self.c["title"])

    def test_bad_key(self):
        self.assertRaises(ValueError, self.c.get, "\u1234")
        self.assertRaises(
            ValueError, self.c.__setitem__, "\u1234", "foo")
        self.assertRaises(
            ValueError, self.c.__delitem__, "\u1234")

    def test_py3_bad_key(self):
        self.assertRaises(TypeError, self.c.get, b"a")
        self.assertRaises(
            TypeError, self.c.__setitem__, b"a", "foo")
        self.assertRaises(
            TypeError, self.c.__delitem__, b"a")

    def test_duplicate_keys(self):
        self.c = VCommentDict()
        keys = ("key", "Key", "KEY")
        for key in keys:
            self.c.append((key, "value"))
        self.assertEqual(len(self.c.keys()), 1)
        self.assertEqual(len(self.c.as_dict()), 1)
