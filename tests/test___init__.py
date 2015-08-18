# -*- coding: utf-8 -*-

import os
from tempfile import mkstemp
import shutil

from tests import TestCase, DATA_DIR
from mutagen._compat import cBytesIO, PY3
from mutagen import File, Metadata, FileType, MutagenError
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
            filename = os.path.join(DATA_DIR, "empty.ogg")
            self.failIf(File(filename, options=[]))

    def test_oggvorbis(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.ogg")), OggVorbis))

    def test_oggflac(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.oggflac")), OggFLAC))

    def test_oggspeex(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.spx")), OggSpeex))

    def test_oggtheora(self):
        self.failUnless(isinstance(File(
            os.path.join(DATA_DIR, "sample.oggtheora")), OggTheora))

    def test_oggopus(self):
        self.failUnless(isinstance(File(
            os.path.join(DATA_DIR, "example.opus")), OggOpus))

    def test_mp3(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "bad-xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-44-s.mp3")), MP3))

    def test_easy_mp3(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-44-s.mp3"), easy=True),
            EasyMP3))

    def test_flac(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-44-s.flac")), FLAC))

    def test_musepack(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "click.mpc")), Musepack))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "sv4_header.mpc")), Musepack))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "sv5_header.mpc")), Musepack))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "sv8_header.mpc")), Musepack))

    def test_monkeysaudio(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "mac-399.ape")), MonkeysAudio))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "mac-396.ape")), MonkeysAudio))

    def test_apev2(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "oldtag.apev2")), APEv2File))

    def test_tta(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.tta")), TrueAudio))

    def test_easy_tta(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.tta"), easy=True),
            EasyTrueAudio))

    def test_wavpack(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-44-s.wv")), WavPack))

    def test_mp4(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "has-tags.m4a")), MP4))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "no-tags.m4a")), MP4))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "no-tags.3g2")), MP4))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "truncated-64bit.mp4")), MP4))

    def test_optimfrog(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.ofr")), OptimFROG))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.ofs")), OptimFROG))

    def test_asf(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-1.wma")), ASF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-2.wma")), ASF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "silence-3.wma")), ASF))

    def test_aiff(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "with-id3.aif")), AIFF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "11k-1ch-2s-silence.aif")), AIFF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "48k-2ch-s16-silence.aif")), AIFF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "8k-1ch-1s-silence.aif")), AIFF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "8k-1ch-3.5s-silence.aif")), AIFF))
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "8k-4ch-1s-silence.aif")), AIFF))

    def test_adts(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "empty.aac")), AAC))

    def test_adif(self):
        self.failUnless(isinstance(
            File(os.path.join(DATA_DIR, "adif.aac")), AAC))

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

        if PY3 and 'm4a' in modules:
            modules.remove('m4a')

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
