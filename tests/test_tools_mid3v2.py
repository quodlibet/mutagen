import os
from tempfile import mkstemp
import shutil

import mutagen
from mutagen.id3 import ID3
from mutagen._compat import PY2

from tests import add
from tests.test_tools import _TTools


class TMid3v2(_TTools):

    TOOL_NAME = "mid3v2"

    def setUp(self):
        super(TMid3v2, self).setUp()
        original = os.path.join('tests', 'data', 'silence-44-s.mp3')
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(original, self.filename)

    def tearDown(self):
        super(TMid3v2, self).tearDown()
        os.unlink(self.filename)

    def test_list_genres(self):
        for arg in ["-L", "--list-genres"]:
            res, out = self.call(arg)
            self.failUnlessEqual(res, 0)
            self.failUnless("Acid Punk" in out)

    def test_list_frames(self):
        for arg in ["-f", "--list-frames"]:
            res, out = self.call(arg)
            self.failUnlessEqual(res, 0)
            self.failUnless("--APIC" in out)
            self.failUnless("--TIT2" in out)

    def test_list(self):
        f = ID3(self.filename)
        album = f["TALB"].text[0]
        for arg in ["-l", "--list"]:
            res, out = self.call(arg, self.filename)
            self.failUnlessEqual(res, 0)
            self.failUnless("TALB=" + album in out)

    def test_list_raw(self):
        f = ID3(self.filename)
        res, out = self.call("--list-raw", self.filename)
        self.failUnlessEqual(res, 0)
        self.failUnless(repr(f["TALB"]) in out)

    def _test_text_frame(self, short, longer, frame):
        new_value = "TEST"
        for arg in [short, longer]:
            orig = ID3(self.filename)
            frame_class = mutagen.id3.Frames[frame]
            orig[frame] = frame_class(text=[u"BLAH"], encoding=3)
            orig.save()

            res, out = self.call(arg, new_value, self.filename)
            self.failUnlessEqual(res, 0)
            self.failIf(out)
            self.failUnlessEqual(ID3(self.filename)[frame].text, [new_value])

    def test_artist(self):
        self._test_text_frame("-a", "--artist", "TPE1")

    def test_album(self):
        self._test_text_frame("-A", "--album", "TALB")

    def test_title(self):
        self._test_text_frame("-t", "--song", "TIT2")

    def test_genre(self):
        self._test_text_frame("-g", "--genre", "TCON")

    def test_convert(self):
        res, out = self.call("--convert", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

    def test_split_escape(self):
        split_escape = self.get_var("split_escape")

        inout = [
            (("", ":"), [""]),
            ((":", ":"), ["", ""]),
            ((":", ":", 0), [":"]),
            ((":b:c:", ":", 0), [":b:c:"]),
            ((":b:c:", ":", 1), ["", "b:c:"]),
            ((":b:c:", ":", 2), ["", "b", "c:"]),
            ((":b:c:", ":", 3), ["", "b", "c", ""]),
            (("a\\:b:c", ":"), ["a:b", "c"]),
            (("a\\\\:b:c", ":"), ["a\\", "b", "c"]),
            (("a\\\\\\:b:c\\:", ":"), ["a\\:b", "c:"]),
            (("\\", ":"), [""]),
            (("\\\\", ":"), ["\\"]),
            (("\\\\a\\b", ":"), ["\\a\\b"]),
        ]

        for inargs, out in inout:
            self.assertEqual(split_escape(*inargs), out)

    def test_unescape(self):
        unescape_string = self.get_var("unescape_string")
        self.assertEqual(unescape_string("\\n"), "\n")

    def test_artist_escape(self):
        res, out = self.call("-e", "-a", "foo\\nbar", self.filename)
        self.failUnlessEqual(res, 0)
        self.failIf(out)
        f = ID3(self.filename)
        self.failUnlessEqual(f["TPE1"][0], "foo\nbar")

    def test_txxx_escape(self):
        res, out = self.call(
            "-e", "--TXXX", "EscapeTest\\:\\:albumartist:Ex\\:ample",
            self.filename)
        self.failUnlessEqual(res, 0)
        self.failIf(out)

        f = ID3(self.filename)
        frame = f.getall("TXXX")[0]
        self.failUnlessEqual(frame.desc, "EscapeTest::albumartist")
        self.failUnlessEqual(frame.text, ["Ex:ample"])

    def test_txxx(self):
        res, out = self.call("--TXXX", "A\\:B:C", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

        f = ID3(self.filename)
        frame = f.getall("TXXX")[0]
        self.failUnlessEqual(frame.desc, "A\\")
        self.failUnlessEqual(frame.text, ["B:C"])

    def test_comm1(self):
        res, out = self.call("--COMM", "A", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

        f = ID3(self.filename)
        frame = f.getall("COMM:")[0]
        self.failUnlessEqual(frame.desc, "")
        self.failUnlessEqual(frame.text, ["A"])

    def test_comm2(self):
        res, out = self.call("--COMM", "Y:B", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

        f = ID3(self.filename)
        frame = f.getall("COMM:Y")[0]
        self.failUnlessEqual(frame.desc, "Y")
        self.failUnlessEqual(frame.text, ["B"])

    def test_comm2_escape(self):
        res, out = self.call("-e", "--COMM", "Y\\:B\\nG", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

        f = ID3(self.filename)
        frame = f.getall("COMM:")[0]
        self.failUnlessEqual(frame.desc, "")
        self.failUnlessEqual(frame.text, ["Y:B\nG"])

    def test_comm3(self):
        res, out = self.call("--COMM", "Z:B:C:D:ger", self.filename)
        self.failUnlessEqual((res, out), (0, ""))

        f = ID3(self.filename)
        frame = f.getall("COMM:Z")[0]
        self.failUnlessEqual(frame.desc, "Z")
        self.failUnlessEqual(frame.text, ["B:C:D"])
        self.failUnlessEqual(frame.lang, "ger")

    def test_encoding_with_escape(self):
        import locale
        text = u'\xe4\xf6\xfc'
        enc = locale.getpreferredencoding()
        # don't fail in case getpreferredencoding doesn't give us a unicode
        # encoding.
        text = text.encode(enc, errors="replace")
        res, out = self.call("-e", "-a", text, self.filename)
        self.failUnlessEqual((res, out), (0, ""))
        f = ID3(self.filename)
        self.assertEqual(f.getall("TPE1")[0], text.decode(enc))

    def test_invalid_encoding(self):
        res, out = self.call("--TALB", '\\xff', '-e', self.filename)
        self.failIfEqual(res, 0)
        self.failUnless("TALB" in out)

    def test_invalid_escape(self):
        res, out = self.call("--TALB", '\\xaz', '-e', self.filename)
        self.failIfEqual(res, 0)
        self.failUnless("TALB" in out)

        res, out = self.call("--TALB", '\\', '-e', self.filename)
        self.failIfEqual(res, 0)
        self.failUnless("TALB" in out)

add(TMid3v2)
