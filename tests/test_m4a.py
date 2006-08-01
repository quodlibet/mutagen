import os
import shutil

from tempfile import mkstemp
from tests import TestCase, add
from mutagen.m4a import M4A, Atom, Atoms

class TAtoms(TestCase):
    uses_mmap = False
    filename = os.path.join("tests", "data", "has-tags.m4a")

    def setUp(self):
        self.atoms = Atoms(file(self.filename, "rb"))

    def test___contains__(self):
        self.failUnless("moov" in self.atoms)
        self.failUnless("moov.udta" in self.atoms)
        self.failUnlessRaises(KeyError, self.atoms.__getitem__, "whee")

    def test_keys(self):
        self.atoms.keys()

    def test_name(self):
        self.failUnlessEqual(self.atoms.atoms[0].name, "ftyp")

    def test_children(self):
        self.failUnless(self.atoms.atoms[2].children)

    def test_no_children(self):
        self.failUnless(self.atoms.atoms[0].children is None)

    def test_repr(self):
        repr(self.atoms)
add(TAtoms)

class TM4A(TestCase):
    def setUp(self):
        fd, self.filename = mkstemp(suffix='mp3')
        os.close(fd)
        shutil.copy(self.original, self.filename)
        self.audio = M4A(self.filename)

    def test_length(self):
        self.failUnlessAlmostEqual(3.7, self.audio.info.length, 1)

    def set_key(self, key, value):
        self.audio[key] = value
        self.audio.save()
        audio = M4A(self.audio.filename)
        self.failUnless(key in audio)
        self.failUnlessEqual(audio[key], value)

    def test_save_text(self):
        self.set_key('\xa9nam', u"Some test name")

    def test_freeform(self):
        self.set_key('----:net.sacredchao.Mutagen:test key', "whee")

    def test_pair(self):
        self.set_key('trkn', (1, 10))
        self.set_key('disk', (18, 0))

    def test_pair_invalid(self):
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (-1, 0))
        self.failUnlessRaises(ValueError, self.set_key, 'trkn', (2**18, 1))

    def test_tempo(self):
        self.set_key('tmpo', 150)

    def test_tempo_invalud(self):
        self.failUnlessRaises(ValueError, self.set_key, 'tmpo', 100000)

    def test_compilation(self):
        self.set_key('cpil', True)

    def test_cover(self):
        self.set_key('covr', 'woooo')

    def test_pprint(self):
        self.audio.pprint()

    def tearDown(self):
        os.unlink(self.filename)

class TM4AHasTags(TM4A):
    original = os.path.join("tests", "data", "has-tags.m4a")

    def test_save_simple(self):
        self.audio.save(self.filename)

    def test_shrink(self):
        map(self.audio.__delitem__, self.audio.keys())
        self.audio.save()
        audio = M4A(self.audio.filename)
        self.failIf(self.audio.tags)

    def test_has_tags(self):
        self.failUnless(self.audio.tags)

add(TM4AHasTags)

class TM4ANoTags(TM4A):
    original = os.path.join("tests", "data", "no-tags.m4a")

    def test_no_tags(self):
        self.failUnless(self.audio.tags is None)

add(TM4ANoTags)
