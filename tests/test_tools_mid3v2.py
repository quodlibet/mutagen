import os
import sys
import StringIO
from tempfile import mkstemp
import shutil

import mutagen
from mutagen.id3 import ID3

from tests import TestCase, add


def get_main(tool_name, entry="main"):
    tool_path = os.path.join("tools", tool_name)
    env = {}
    execfile(tool_path, env)
    return env[entry]


class _TTools(TestCase):
    TOOL_NAME = None

    def setUp(self):
        self._main = get_main(self.TOOL_NAME)

    def call(self, *args):
        for arg in args:
            assert isinstance(arg, str)
        old_stdout = sys.stdout
        try:
            out = StringIO.StringIO()
            sys.stdout = out
            try:
                ret = self._main([self.TOOL_NAME] + list(args))
            except SystemExit, e:
                ret = e.code
            ret = ret or 0
            return (ret,  out.getvalue())
        finally:
            sys.stdout = old_stdout

    def tearDown(self):
        del self._main


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

add(TMid3v2)
