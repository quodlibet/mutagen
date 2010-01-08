from tests import add, TestCase
from mutagen._vorbis import VComment, VCommentDict, istag

class Tistag(TestCase):
    uses_mmap = False

    def test_empty(self): self.failIf(istag(""))
    def test_tilde(self): self.failIf(istag("ti~tle"))
    def test_equals(self): self.failIf(istag("ti=tle"))
    def test_less(self): self.failIf(istag("ti\x19tle"))
    def test_greater(self): self.failIf(istag("ti\xa0tle"))

    def test_simple(self): self.failUnless(istag("title"))
    def test_space(self): self.failUnless(istag("ti tle"))
    def test_ugly(self): self.failUnless(istag("!{}[]-_()*&"))
add(Tistag)

class TVComment(TestCase):
    uses_mmap = False

    def setUp(self):
        self.c = VComment()
        self.c.append(("artist", u"piman"))
        self.c.append(("artist", u"mu"))
        self.c.append(("title", u"more fakes"))

    def test_invalid_init(self):
        self.failUnlessRaises(TypeError, VComment, [])

    def test_equal(self):
        self.failUnlessEqual(self.c, self.c)

    def test_not_header(self):
        self.failUnlessRaises(IOError, VComment, "foo")

    def test_unset_framing_bit(self):
        self.failUnlessRaises(
            IOError, VComment, "\x00\x00\x00\x00" * 2 + "\x00")

    def test_empty_valid(self):
        self.failIf(VComment("\x00\x00\x00\x00" * 2 + "\x01"))

    def test_validate(self):
        self.failUnless(self.c.validate())

    def test_validate_broken_key(self):
        self.c.append((1, u"valid"))
        self.failUnlessRaises(ValueError, self.c.validate)
        self.failUnlessRaises(ValueError, self.c.write)

    def test_validate_broken_value(self):
        self.c.append(("valid", 1))
        self.failUnlessRaises(ValueError, self.c.validate)
        self.failUnlessRaises(ValueError, self.c.write)

    def test_validate_nonunicode_value(self):
        self.c.append(("valid", "wt\xff"))
        self.failUnlessRaises(ValueError, self.c.validate)
        self.failUnlessRaises(ValueError, self.c.write)

    def test_vendor_default(self):
        self.failUnless(self.c.vendor.startswith("Mutagen"))

    def test_vendor_set(self):
        self.c.vendor = "Not Mutagen"
        self.failUnless(self.c.write()[4:].startswith("Not Mutagen"))

    def test_vendor_invalid(self):
        self.c.vendor = "\xffNot Mutagen"
        self.failUnlessRaises(ValueError, self.c.validate)
        self.failUnlessRaises(ValueError, self.c.write)

    def test_invalid_format_strict(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                '\x00abc\x01')
        self.failUnlessRaises(IOError, VComment, data, errors='strict')

    def test_invalid_format_replace(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                '\x00abc\x01')
        comment = VComment(data)
        self.failUnlessEqual("abc", comment[0][1])

    def test_invalid_format_ignore(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x03\x00\x00'
                '\x00abc\x01')
        comment = VComment(data, errors='ignore')
        self.failIf(len(comment))

    # Slightly different test data than above, we want the tag name
    # to be valid UTF-8 but not valid ASCII.
    def test_invalid_tag_strict(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                '\x00\xc2\xaa=c\x01')
        self.failUnlessRaises(IOError, VComment, data, errors='strict')

    def test_invalid_tag_replace(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                '\x00\xc2\xaa=c\x01')
        comment = VComment(data)
        self.failUnlessEqual("?=c", comment.pprint())

    def test_invalid_tag_ignore(self):
        data = ('\x07\x00\x00\x00Mutagen\x01\x00\x00\x00\x04\x00\x00'
                '\x00\xc2\xaa=c\x01')
        comment = VComment(data, errors='ignore')
        self.failIf(len(comment))

    def test_roundtrip(self):
        self.failUnlessEqual(self.c, VComment(self.c.write()))
add(TVComment)

class TVCommentDict(TestCase):
    uses_mmap = False

    Kind = VCommentDict

    def setUp(self):
        self.c = self.Kind()
        self.c["artist"] = ["mu", "piman"]
        self.c["title"] = u"more fakes"

    def test_correct_len(self):
        self.failUnlessEqual(len(self.c), 3)

    def test_keys(self):
        self.failUnless("artist" in self.c.keys())
        self.failUnless("title" in self.c.keys())

    def test_values(self):
        self.failUnless(["mu", "piman"] in self.c.values())
        self.failUnless(["more fakes"] in self.c.values())

    def test_items(self):
        self.failUnless(("artist", ["mu", "piman"]) in self.c.items())
        self.failUnless(("title", ["more fakes"]) in self.c.items())

    def test_equal(self):
        self.failUnlessEqual(self.c, self.c)

    def test_get(self):
        self.failUnlessEqual(self.c["artist"], ["mu", "piman"])
        self.failUnlessEqual(self.c["title"], ["more fakes"])

    def test_set(self):
        self.c["woo"] = "bar"
        self.failUnlessEqual(self.c["woo"], ["bar"])

    def test_del(self):
        del(self.c["title"])
        self.failUnlessRaises(KeyError, self.c.__getitem__, "title")

    def test_contains(self):
        self.failIf("foo" in self.c)
        self.failUnless("title" in self.c)

    def test_get_case(self):
        self.failUnlessEqual(self.c["ARTIST"], ["mu", "piman"])

    def test_set_case(self):
        self.c["TITLE"] = "another fake"
        self.failUnlessEqual(self.c["title"], ["another fake"])

    def test_contains_case(self):
        self.failUnless("TITLE" in self.c)

    def test_del_case(self):
        del(self.c["TITLE"])
        self.failUnlessRaises(KeyError, self.c.__getitem__, "title")

    def test_get_failure(self):
        self.failUnlessRaises(KeyError, self.c.__getitem__, "woo")

    def test_del_failure(self):
        self.failUnlessRaises(KeyError, self.c.__delitem__, "woo")

    def test_roundtrip(self):
        self.failUnlessEqual(self.c, self.Kind(self.c.write()))

    def test_roundtrip_vc(self):
        self.failUnlessEqual(self.c, VComment(self.c.write()))

    def test_case_items_426(self):
        self.c.append(("WOO", "bar"))
        self.failUnless(("woo", ["bar"]) in self.c.items())

    def test_empty(self):
        self.c = VCommentDict()
        self.failIf(self.c.keys())
        self.failIf(self.c.values())
        self.failIf(self.c.items())

    def test_as_dict(self):
        d = self.c.as_dict()
        self.failUnless("artist" in d)
        self.failUnless("title" in d)
        self.failUnlessEqual(d["artist"], self.c["artist"])
        self.failUnlessEqual(d["title"], self.c["title"])

    def test_bad_key(self):
        self.failUnlessRaises(UnicodeError, self.c.get, u"\u1234")
        self.failUnlessRaises(
            UnicodeError, self.c.__setitem__, u"\u1234", "foo")
        self.failUnlessRaises(
            UnicodeError, self.c.__delitem__, u"\u1234")

    def test_duplicate_keys(self):
        self.c = VCommentDict()
        keys = ("key", "Key", "KEY")
        for key in keys:
            self.c.append((key, "value"))
        self.failUnlessEqual(len(self.c.keys()), 1)
        self.failUnlessEqual(len(self.c.as_dict()), 1)

add(TVCommentDict)
