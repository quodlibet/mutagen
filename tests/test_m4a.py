import os
import shutil

from cStringIO import StringIO
from tempfile import mkstemp
from tests import TestCase, add

import warnings
warnings.simplefilter("ignore", DeprecationWarning)
from mutagen.m4a import M4A, Atom, Atoms, M4ATags, M4AInfo, \
     delete, M4ACover, M4AMetadataError

try: from os.path import devnull
except ImportError: devnull = "/dev/null"

class TAtom(TestCase):
    uses_mmap = False

    def test_no_children(self):
        fileobj = StringIO("\x00\x00\x00\x08atom")
        atom = Atom(fileobj)
        self.failUnlessRaises(KeyError, atom.__getitem__, "test")

    def test_length_1(self):
        fileobj = StringIO("\x00\x00\x00\x01atom" + "\x00" * 8)
        self.failUnlessRaises(IOError, Atom, fileobj)

    def test_render_too_big(self):
        class TooBig(str):
            def __len__(self):
                return 1L << 32
        data = TooBig("test")
        try: len(data)
        except OverflowError:
            # Py_ssize_t is still only 32 bits on this system.
            self.failUnlessRaises(OverflowError, Atom.render, "data", data)
        else:
            data = Atom.render("data", data)
            self.failUnlessEqual(len(data), 4 + 4 + 8 + 4)

    def test_length_0(self):
        fileobj = StringIO("\x00\x00\x00\x00atom")
        Atom(fileobj)
        self.failUnlessEqual(fileobj.tell(), 8)
add(TAtom)

class TAtoms(TestCase):
    uses_mmap = False
    filename = os.path.join("tests", "data", "has-tags.m4a")

    def setUp(self):
        self.atoms = Atoms(file(self.filename, "rb"))

    def test___contains__(self):
        self.failUnless(self.atoms["moov"])
        self.failUnless(self.atoms["moov.udta"])
        self.failUnlessRaises(KeyError, self.atoms.__getitem__, "whee")

    def test_name(self):
        self.failUnlessEqual(self.atoms.atoms[0].name, "ftyp")

    def test_children(self):
        self.failUnless(self.atoms.atoms[2].children)

    def test_no_children(self):
        self.failUnless(self.atoms.atoms[0].children is None)

    def test_repr(self):
        repr(self.atoms)
add(TAtoms)

class TM4AInfo(TestCase):
    uses_mmap = False

    def test_no_soun(self):
        self.failUnlessRaises(
            IOError, self.test_mdhd_version_1, "no so und data here")

    def test_mdhd_version_1(self, soun="soun"):
        mdhd = Atom.render("mdhd", ("\x01\x00\x00\x00" + "\x00" * 16 +
                                    "\x00\x00\x00\x02" + # 2 Hz
                                    "\x00\x00\x00\x00\x00\x00\x00\x10"))
        hdlr = Atom.render("hdlr", soun)
        mdia = Atom.render("mdia", mdhd + hdlr)
        trak = Atom.render("trak", mdia)
        moov = Atom.render("moov", trak)
        fileobj = StringIO(moov)
        atoms = Atoms(fileobj)
        info = M4AInfo(atoms, fileobj)
        self.failUnlessEqual(info.length, 8)
add(TM4AInfo)

class TM4ATags(TestCase):
    uses_mmap = False

    def wrap_ilst(self, data):
        ilst = Atom.render("ilst", data)
        meta = Atom.render("meta", "\x00" * 4 + ilst)
        data = Atom.render("moov", Atom.render("udta", meta))
        fileobj = StringIO(data)
        return M4ATags(Atoms(fileobj), fileobj)
        
    def test_bad_freeform(self):
        mean = Atom.render("mean", "net.sacredchao.Mutagen")
        name = Atom.render("name", "empty test key")
        bad_freeform = Atom.render("----", "\x00" * 4 + mean + name)
        self.failIf(self.wrap_ilst(bad_freeform))

    def test_genre(self):
        data = Atom.render("data", "\x00" * 8 + "\x00\x01")
        genre = Atom.render("gnre", data)
        tags = self.wrap_ilst(genre)
        self.failIf("gnre" in tags)
        self.failUnlessEqual(tags.get("\xa9gen"), "Blues")

    def test_empty_cpil(self):
        cpil = Atom.render("cpil", Atom.render("data", "\x00" * 8))
        tags = self.wrap_ilst(cpil)
        self.failUnless("cpil" in tags)
        self.failIf(tags["cpil"])

    def test_genre_too_big(self):
        data = Atom.render("data", "\x00" * 8 + "\x01\x00")
        genre = Atom.render("gnre", data)
        tags = self.wrap_ilst(genre)
        self.failIf("gnre" in tags)
        self.failIf("\xa9gen" in tags)

    def test_strips_unknown_types(self):
        data = Atom.render("data", "\x00" * 8 + "whee")
        foob = Atom.render("foob", data)
        tags = self.wrap_ilst(foob)
        self.failIf(tags)

    def test_bad_covr(self):
        data = Atom.render("foob", "\x00\x00\x00\x0E" + "\x00" * 4 + "whee")
        covr = Atom.render("covr", data)
        self.failUnlessRaises(M4AMetadataError, self.wrap_ilst, covr)

add(TM4ATags)

class TM4A(TestCase):
    def setUp(self):
        fd, self.filename = mkstemp(suffix='m4a')
        os.close(fd)
        shutil.copy(self.original, self.filename)
        self.audio = M4A(self.filename)

    def faad(self):
        if not have_faad: return
        value = os.system(
            "faad %s -o %s > %s 2> %s" % (
                self.filename, devnull, devnull, devnull))
        self.failIf(value and value != NOTFOUND)

    def test_bitrate(self):
        self.failUnlessEqual(self.audio.info.bitrate, 2914)

    def test_length(self):
        self.failUnlessAlmostEqual(3.7, self.audio.info.length, 1)

    def set_key(self, key, value):
        self.audio[key] = value
        self.audio.save()
        audio = M4A(self.audio.filename)
        self.failUnless(key in audio)
        self.failUnlessEqual(audio[key], value)
        self.faad()

    def test_save_text(self):
        self.set_key('\xa9nam', u"Some test name")

    def test_freeform(self):
        self.set_key('----:net.sacredchao.Mutagen:test key', "whee")

    def test_tracknumber(self):
        self.set_key('trkn', (1, 10))

    def test_disk(self):
        self.set_key('disk', (18, 0))

    def test_tracknumber_too_small(self):
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (-1, 0))
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (2**18, 1))

    def test_disk_too_small(self):
        self.failUnlessRaises(ValueError, self.set_key, 'disk', (-1, 0))
        self.failUnlessRaises(ValueError, self.set_key, 'disk', (2**18, 1))

    def test_tracknumber_wrong_size(self):
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (1,))
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (1, 2, 3,))

    def test_disk_wrong_size(self):
        self.failUnlessRaises(ValueError, self.set_key, 'disk', (1,))
        self.failUnlessRaises(ValueError, self.set_key, 'disk', (1, 2, 3,))

    def test_tempo(self):
        self.set_key('tmpo', 150)

    def test_tempo_invalid(self):
        self.failUnlessRaises(ValueError, self.set_key, 'tmpo', 100000)

    def test_compilation(self):
        self.set_key('cpil', True)

    def test_compilation_false(self):
        self.set_key('cpil', False)

    def test_cover(self):
        self.set_key('covr', 'woooo')

    def test_cover_png(self):
        self.set_key('covr', M4ACover('woooo', M4ACover.FORMAT_PNG))

    def test_cover_jpeg(self):
        self.set_key('covr', M4ACover('hoooo', M4ACover.FORMAT_JPEG))

    def test_pprint(self):
        self.audio.pprint()

    def test_pprint_binary(self):
        self.audio["covr"] = "\x00\xa9\garbage"
        self.audio.pprint()

    def test_delete(self):
        self.audio.delete()
        audio = M4A(self.audio.filename)
        self.failIf(audio.tags)
        self.faad()

    def test_module_delete(self):
        delete(self.filename)
        audio = M4A(self.audio.filename)
        self.failIf(audio.tags)
        self.faad()

    def test_reads_unknown_text(self):
        self.set_key("foob", u"A test")

    def test_mime(self):
        self.failUnless("audio/mp4" in self.audio.mime)

    def tearDown(self):
        os.unlink(self.filename)

class TM4AHasTags(TM4A):
    original = os.path.join("tests", "data", "has-tags.m4a")

    def test_save_simple(self):
        self.audio.save()
        self.faad()

    def test_shrink(self):
        map(self.audio.__delitem__, self.audio.keys())
        self.audio.save()
        audio = M4A(self.audio.filename)
        self.failIf(self.audio.tags)

    def test_has_tags(self):
        self.failUnless(self.audio.tags)

    def test_has_covr(self):
        self.failUnless('covr' in self.audio.tags)
        covr = self.audio.tags['covr']
        self.failUnlessEqual(covr.imageformat, M4ACover.FORMAT_PNG)

    def test_not_my_file(self):
        self.failUnlessRaises(
            IOError, M4A, os.path.join("tests", "data", "empty.ogg"))

add(TM4AHasTags)

class TM4ANoTags(TM4A):
    original = os.path.join("tests", "data", "no-tags.m4a")

    def test_no_tags(self):
        self.failUnless(self.audio.tags is None)

add(TM4ANoTags)

NOTFOUND = os.system("tools/notarealprogram 2> %s" % devnull)

have_faad = True
if os.system("faad 2> %s > %s" % (devnull, devnull)) == NOTFOUND:
    have_faad = False
    print "WARNING: Skipping FAAD reference tests."
