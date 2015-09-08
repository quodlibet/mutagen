# -*- coding: utf-8 -*-

import os
from tempfile import mkstemp
import shutil

from tests import TestCase, DATA_DIR
from mutagen._compat import cBytesIO, text_type
from mutagen import File, Metadata, FileType, MutagenError, PaddingInfo
from mutagen.oggvorbis import OggVorbis
from mutagen.oggflac import OggFLAC
from mutagen.oggspeex import OggSpeex
from mutagen.oggtheora import OggTheora
from mutagen.oggopus import OggOpus
from mutagen.mp3 import MP3, EasyMP3
from mutagen.apev2 import APEv2File
from mutagen.flac import FLAC
from mutagen.wavpack import WavPack
from mutagen.trueaudio import TrueAudio, EasyTrueAudio
from mutagen.mp4 import MP4
from mutagen.musepack import Musepack
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.optimfrog import OptimFROG
from mutagen.asf import ASF
from mutagen.aiff import AIFF
from mutagen.aac import AAC
from os import devnull


class TMetadata(TestCase):

    class FakeMeta(Metadata):
        def __init__(self):
            pass

    def test_virtual_constructor(self):
        self.failUnlessRaises(NotImplementedError, Metadata, "filename")

    def test_load(self):
        m = Metadata()
        self.failUnlessRaises(NotImplementedError, m.load, "filename")

    def test_virtual_save(self):
        self.failUnlessRaises(NotImplementedError, self.FakeMeta().save)
        self.failUnlessRaises(
            NotImplementedError, self.FakeMeta().save, "filename")

    def test_virtual_delete(self):
        self.failUnlessRaises(NotImplementedError, self.FakeMeta().delete)
        self.failUnlessRaises(
            NotImplementedError, self.FakeMeta().delete, "filename")


class TPaddingInfo(TestCase):

    def test_props(self):
        info = PaddingInfo(10, 100)
        self.assertEqual(info.size, 100)
        self.assertEqual(info.padding, 10)

        info = PaddingInfo(-10, 100)
        self.assertEqual(info.size, 100)
        self.assertEqual(info.padding, -10)

    def test_default_strategy(self):
        s = 100000
        self.assertEqual(PaddingInfo(10, s).get_default_padding(), 10)
        self.assertEqual(PaddingInfo(-10, s).get_default_padding(), 1524)
        self.assertEqual(PaddingInfo(0, s).get_default_padding(), 0)
        self.assertEqual(PaddingInfo(10000, s).get_default_padding(), 1524)

        self.assertEqual(PaddingInfo(10, 0).get_default_padding(), 10)
        self.assertEqual(PaddingInfo(-10, 0).get_default_padding(), 1024)
        self.assertEqual(PaddingInfo(1050, 0).get_default_padding(), 1050)
        self.assertEqual(PaddingInfo(10000, 0).get_default_padding(), 1024)

    def test_repr(self):
        info = PaddingInfo(10, 100)
        self.assertEqual(repr(info), "<PaddingInfo size=100 padding=10>")


class TFileType(TestCase):

    def setUp(self):
        self.vorbis = File(os.path.join(DATA_DIR, "empty.ogg"))

        fd, filename = mkstemp(".mp3")
        os.close(fd)
        shutil.copy(os.path.join(DATA_DIR, "xing.mp3"), filename)
        self.mp3_notags = File(filename)
        self.mp3_filename = filename

    def tearDown(self):
        os.remove(self.mp3_filename)

    def test_delitem_not_there(self):
        self.failUnlessRaises(KeyError, self.vorbis.__delitem__, "foobar")

    def test_add_tags(self):
        self.failUnlessRaises(NotImplementedError, FileType().add_tags)

    def test_delitem(self):
        self.vorbis["foobar"] = "quux"
        del(self.vorbis["foobar"])
        self.failIf("quux" in self.vorbis)

    def test_save_no_tags(self):
        self.assertTrue(self.mp3_notags.tags is None)
        self.mp3_notags.save()
        self.assertTrue(self.mp3_notags.tags is None)


class TAbstractFileType(object):

    PATH = None
    KIND = None

    def setUp(self):
        fd, self.filename = mkstemp("." + self.PATH.rsplit(".", 1)[-1])
        os.close(fd)
        shutil.copy(self.PATH, self.filename)
        self.audio = self.KIND(self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_file(self):
        self.assertTrue(isinstance(File(self.PATH), self.KIND))

    def test_pprint(self):
        res = self.audio.pprint()
        self.assertTrue(res)
        self.assertTrue(isinstance(res, text_type))

    def test_info(self):
        self.assertTrue(self.audio.info)

    def test_info_pprint(self):
        res = self.audio.info.pprint()
        self.assertTrue(res)
        self.assertTrue(isinstance(res, text_type))

    def test_mime(self):
        self.assertTrue(self.audio.mime)
        self.assertTrue(isinstance(self.audio.mime, list))


_FILETYPES = {
    OggVorbis: [os.path.join(DATA_DIR, "empty.ogg")],
    OggFLAC: [os.path.join(DATA_DIR, "empty.oggflac")],
    OggSpeex: [os.path.join(DATA_DIR, "empty.spx")],
    OggTheora: [os.path.join(DATA_DIR, "sample.oggtheora")],
    OggOpus: [os.path.join(DATA_DIR, "example.opus")],
    FLAC: [os.path.join(DATA_DIR, "silence-44-s.flac")],
    TrueAudio: [os.path.join(DATA_DIR, "empty.tta")],
    WavPack: [os.path.join(DATA_DIR, "silence-44-s.wv")],
    MP3: [
        os.path.join(DATA_DIR, "bad-xing.mp3"),
        os.path.join(DATA_DIR, "xing.mp3"),
        os.path.join(DATA_DIR, "silence-44-s.mp3"),
    ],
    Musepack: [
        os.path.join(DATA_DIR, "click.mpc"),
        os.path.join(DATA_DIR, "sv4_header.mpc"),
        os.path.join(DATA_DIR, "sv5_header.mpc"),
        os.path.join(DATA_DIR, "sv8_header.mpc"),
    ],
    OptimFROG: [
        os.path.join(DATA_DIR, "empty.ofr"),
        os.path.join(DATA_DIR, "empty.ofs"),
    ],
    AAC: [
        os.path.join(DATA_DIR, "empty.aac"),
        os.path.join(DATA_DIR, "adif.aac"),
    ],
    ASF: [
        os.path.join(DATA_DIR, "silence-1.wma"),
        os.path.join(DATA_DIR, "silence-2.wma"),
        os.path.join(DATA_DIR, "silence-3.wma"),
    ],
    AIFF: [
        os.path.join(DATA_DIR, "with-id3.aif"),
        os.path.join(DATA_DIR, "11k-1ch-2s-silence.aif"),
        os.path.join(DATA_DIR, "48k-2ch-s16-silence.aif"),
        os.path.join(DATA_DIR, "8k-1ch-1s-silence.aif"),
        os.path.join(DATA_DIR, "8k-1ch-3.5s-silence.aif"),
        os.path.join(DATA_DIR, "8k-4ch-1s-silence.aif")
    ],
    MonkeysAudio: [
        os.path.join(DATA_DIR, "mac-399.ape"),
        os.path.join(DATA_DIR, "mac-396.ape"),
    ],
    MP4: [
        os.path.join(DATA_DIR, "has-tags.m4a"),
        os.path.join(DATA_DIR, "no-tags.m4a"),
        os.path.join(DATA_DIR, "no-tags.3g2"),
        os.path.join(DATA_DIR, "truncated-64bit.mp4"),
    ],
}


def create_filetype_tests():
    for kind, paths in _FILETYPES.items():
        for i, path in enumerate(paths):
            suffix = "_" + str(i + 1) if i else ""
            new_type = type("TFileType" + kind.__name__ + suffix,
                            (TAbstractFileType, TestCase),
                            {"PATH": path, "KIND": kind})
            globals()[new_type.__name__] = new_type

create_filetype_tests()


class TFile(TestCase):

    def test_bad(self):
        try:
            self.failUnless(File(devnull) is None)
        except (OSError, IOError):
            print("WARNING: Unable to open %s." % devnull)
        self.failUnless(File(__file__) is None)

    def test_empty(self):
        filename = os.path.join(DATA_DIR, "empty")
        open(filename, "wb").close()
        try:
            self.failUnless(File(filename) is None)
        finally:
            os.unlink(filename)

    def test_not_file(self):
        self.failUnlessRaises(EnvironmentError, File, "/dev/doesnotexist")

    def test_no_options(self):
        for filename in ["empty.ogg", "empty.oggflac", "silence-44-s.mp3"]:
            filename = os.path.join(DATA_DIR, filename)
            self.failIf(File(filename, options=[]))

    def test_easy_mp3(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-44-s.mp3"), easy=True),
            EasyMP3))

    def test_apev2(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "oldtag.apev2")), APEv2File))

    def test_easy_tta(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.tta"), easy=True),
            EasyTrueAudio))

    def test_id3_indicates_mp3_not_tta(self):
        header = b"ID3 the rest of this is garbage"
        fileobj = cBytesIO(header)
        filename = "not-identifiable.ext"
        self.failUnless(TrueAudio.score(filename, fileobj, header) <
                        MP3.score(filename, fileobj, header))

    def test_prefer_theora_over_vorbis(self):
        header = (
            b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\xe1x\x06\x0f"
            b"\x00\x00\x00\x00)S'\xf4\x01*\x80theora\x03\x02\x01\x006\x00\x1e"
            b"\x00\x03V\x00\x01\xe0\x00\x00\x00\x00\x00\x18\x00\x00\x00\x01"
            b"\x00\x00\x00\x00\x00\x00\x00&%\xa0\x00\xc0OggS\x00\x02\x00\x00"
            b"\x00\x00\x00\x00\x00\x00d#\xa8\x1f\x00\x00\x00\x00]Y\xc0\xc0"
            b"\x01\x1e\x01vorbis\x00\x00\x00\x00\x02\x80\xbb\x00\x00\x00\x00"
            b"\x00\x00\x00\xee\x02\x00\x00\x00\x00\x00\xb8\x01")
        fileobj = cBytesIO(header)
        filename = "not-identifiable.ext"
        self.failUnless(OggVorbis.score(filename, fileobj, header) <
                        OggTheora.score(filename, fileobj, header))


class TFileUpperExt(TestCase):
    FILES = [
        (os.path.join(DATA_DIR, "empty.ofr"), OptimFROG),
        (os.path.join(DATA_DIR, "sv5_header.mpc"), Musepack),
        (os.path.join(DATA_DIR, "silence-3.wma"), ASF),
        (os.path.join(DATA_DIR, "truncated-64bit.mp4"), MP4),
        (os.path.join(DATA_DIR, "silence-44-s.flac"), FLAC),
    ]

    def setUp(self):
        checks = []
        for (original, instance) in self.FILES:
            ext = os.path.splitext(original)[1]
            fd, filename = mkstemp(suffix=ext.upper())
            os.close(fd)
            shutil.copy(original, filename)
            checks.append((filename, instance))
        self.checks = checks

    def test_case_insensitive_ext(self):
        for (path, instance) in self.checks:
            if isinstance(path, bytes):
                path = path.decode("ascii")
            self.failUnless(
                isinstance(File(path, options=[instance]), instance))
            path = path.encode("ascii")
            self.failUnless(
                isinstance(File(path, options=[instance]), instance))

    def tearDown(self):
        for (path, instance) in self.checks:
            os.unlink(path)


class TModuleImportAll(TestCase):

    def setUp(self):
        import mutagen
        files = os.listdir(mutagen.__path__[0])
        modules = set(os.path.splitext(f)[0] for f in files)
        modules = [f for f in modules if not f.startswith("_")]

        self.modules = []
        for module in modules:
            mod = getattr(__import__("mutagen." + module), module)
            self.modules.append(mod)

    def tearDown(self):
        del self.modules[:]

    def test_all(self):
        for mod in self.modules:
            for attr in getattr(mod, "__all__", []):
                getattr(mod, attr)

    def test_errors(self):
        for mod in self.modules:
            self.assertTrue(issubclass(mod.error, MutagenError), msg=mod.error)
