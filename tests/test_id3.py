import os; from os.path import join
import shutil
from unittest import TestCase
from tests import add
from mutagen.id3 import ID3, BitPaddedInt, COMR, Frames, Frames_2_2, ID3Warning, ID3JunkFrameError
from StringIO import StringIO
import warnings
warnings.simplefilter('error', ID3Warning)

try: from sets import Set as set
except ImportError: pass

_22 = ID3(); _22.version = (2,2,0)
_23 = ID3(); _23.version = (2,3,0)
_24 = ID3(); _24.version = (2,4,0)

class ID3GetSetDel(TestCase):
    uses_mmap = False

    def setUp(self):
        self.i = ID3()
        self.i["BLAH"] = 1
        self.i["QUUX"] = 2
        self.i["FOOB:ar"] = 3
        self.i["FOOB:az"] = 4

    def test_getnormal(self):
        self.assertEquals(self.i.getall("BLAH"), [1])
        self.assertEquals(self.i.getall("QUUX"), [2])
        self.assertEquals(self.i.getall("FOOB:ar"), [3])
        self.assertEquals(self.i.getall("FOOB:az"), [4])

    def test_getlist(self):
        self.assert_(self.i.getall("FOOB") in [[3, 4], [4, 3]])

    def test_delnormal(self):
        self.assert_("BLAH" in self.i)
        self.i.delall("BLAH")
        self.assert_("BLAH" not in self.i)

    def test_delone(self):
        self.i.delall("FOOB:ar")
        self.assertEquals(self.i.getall("FOOB"), [4])

    def test_delall(self):
        self.assert_("FOOB:ar" in self.i)
        self.assert_("FOOB:az" in self.i)
        self.i.delall("FOOB")
        self.assert_("FOOB:ar" not in self.i)
        self.assert_("FOOB:az" not in self.i)

    def test_setone(self):
        class TEST(object): HashKey = "FOOB:ar"
        t = TEST()
        self.i.setall("FOOB", [t])
        self.assertEquals(self.i["FOOB:ar"], t)
        self.assertEquals(self.i.getall("FOOB"), [t])

    def test_settwo(self):
        class TEST(object): HashKey = "FOOB:ar"
        t = TEST()
        t2 = TEST(); t2.HashKey = "FOOB:az"
        self.i.setall("FOOB", [t, t2])
        self.assertEquals(self.i["FOOB:ar"], t)
        self.assertEquals(self.i["FOOB:az"], t2)
        self.assert_(self.i.getall("FOOB") in [[t, t2], [t2, t]])

class ID3Loading(TestCase):
    uses_mmap = False


    empty = join('tests', 'data', 'emptyfile.mp3')
    silence = join('tests', 'data', 'silence-44-s.mp3')

    def test_empty_file(self):
        name = self.empty
        self.assertRaises(ValueError, ID3, filename=name)
        #from_name = ID3(name)
        #obj = open(name, 'rb')
        #from_obj = ID3(fileobj=obj)
        #self.assertEquals(from_name, from_explicit_name)
        #self.assertEquals(from_name, from_obj)

    def test_nonexistent_file(self):
        name = join('tests', 'data', 'does', 'not', 'exist')
        self.assertRaises(EnvironmentError, ID3, name)

    def test_header_empty(self):
        id3 = ID3()
        id3._ID3__fileobj = file(self.empty, 'rb')
        self.assertRaises(EOFError, id3._ID3__load_header)

    def test_header_silence(self):
        id3 = ID3()
        id3._ID3__fileobj = file(self.silence, 'rb')
        id3._ID3__load_header()
        self.assertEquals(id3.version, (2,3,0))
        self.assertEquals(id3.size, 1314)

    def test_header_2_4_invalid_flags(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x04\x00\x1f\x00\x00\x00\x00')
        self.assertRaises(ValueError, id3._ID3__load_header)

    def test_header_2_4_allow_footer(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x04\x00\x10\x00\x00\x00\x00')
        id3._ID3__load_header()

    def test_header_2_3_invalid_flags(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x03\x00\x1f\x00\x00\x00\x00')
        self.assertRaises(ValueError, id3._ID3__load_header)
        id3._ID3__fileobj = StringIO('ID3\x03\x00\x0f\x00\x00\x00\x00')
        self.assertRaises(ValueError, id3._ID3__load_header)

    def test_header_2_2(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x02\x00\x00\x00\x00\x00\x00')
        id3._ID3__load_header()
        self.assertEquals(id3.version, (2,2,0))

    def test_header_2_1(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x01\x00\x00\x00\x00\x00\x00')
        self.assertRaises(NotImplementedError, id3._ID3__load_header)

    def test_header_too_small(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO('ID3\x01\x00\x00\x00\x00\x00')
        self.assertRaises(EOFError, id3._ID3__load_header)

    def test_header_2_4_extended(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO(
            'ID3\x04\x00\x40\x00\x00\x00\x00\x00\x00\x00\x05\x5a')
        id3._ID3__load_header()
        self.assertEquals(id3._ID3__extsize, 1)
        self.assertEquals(id3._ID3__extdata, '\x5a')

    def test_header_2_4_extended_but_not(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO(
            'ID3\x04\x00\x40\x00\x00\x00\x00TIT1\x00\x00\x00\x01a')
        id3._ID3__load_header()
        self.assertEquals(id3._ID3__extsize, 0)
        self.assertEquals(id3._ID3__extdata, '')

    def test_header_2_4_extended_but_not_but_not_tag(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO(
            'ID3\x04\x00\x40\x00\x00\x00\x00TIT9')
        self.failUnlessRaises(EOFError, id3._ID3__load_header)

    def test_header_2_3_extended(self):
        id3 = ID3()
        id3._ID3__fileobj = StringIO(
            'ID3\x03\x00\x40\x00\x00\x00\x00\x00\x00\x00\x06'
            '\x00\x00\x56\x78\x9a\xbc')
        id3._ID3__load_header()
        self.assertEquals(id3._ID3__extsize, 6)
        self.assertEquals(id3._ID3__extdata, '\x00\x00\x56\x78\x9a\xbc')

    def test_unsynch(self):
        id3 = ID3()
        id3.version = (2,4,0)
        id3._ID3__flags = 0x80
        badsync = '\x00\xff\x00ab\x00'
        self.assertEquals(
            id3._ID3__load_framedata(Frames["TPE2"], 0, badsync), [u"\xffab"])
        id3._ID3__flags = 0x00
        self.assertEquals(id3._ID3__load_framedata(
            Frames["TPE2"], 0x02, badsync), [u"\xffab"])
        tag = id3._ID3__load_framedata(Frames["TPE2"], 0, badsync)
        self.assertEquals(tag, [u"\xff", u"ab"])

    def test_insane__ID3__fullread(self):
        id3 = ID3()
        id3._ID3__filesize = 0
        self.assertRaises(ValueError, id3._ID3__fullread, -3)
        self.assertRaises(EOFError, id3._ID3__fullread, 3)

class Issue21(TestCase):
    uses_mmap = False

    # Files with bad extended header flags failed to read tags.
    # Ensure the extended header is turned off, and the frames are
    # read.
    def setUp(self):
        self.id3 = ID3(join('tests', 'data', 'issue_21.id3'))

    def test_no_ext(self):
        self.failIf(self.id3.f_extended)

    def test_has_tags(self):
        self.failUnless("TIT2" in self.id3)
        self.failUnless("TALB" in self.id3)

    def test_tit2_value(self):
        self.failUnlessEqual(self.id3["TIT2"].text, [u"Punk To Funk"])
add(Issue21)

class ID3Tags(TestCase):
    uses_mmap = False

    def setUp(self):
        self.silence = join('tests', 'data', 'silence-44-s.mp3')

    def test_None(self):
        id3 = ID3(self.silence, known_frames={})
        self.assertEquals(0, len(id3.keys()))
        self.assertEquals(9, len(id3.unknown_frames))

    def test_has_docs(self):
        for Kind in Frames.values() + Frames_2_2.values():
            self.failUnless(Kind.__doc__, "%s has no docstring" % Kind)

    def test_23(self):
        id3 = ID3(self.silence)
        self.assertEquals(8, len(id3.keys()))
        self.assertEquals(0, len(id3.unknown_frames))
        self.assertEquals('Quod Libet Test Data', id3['TALB'])
        self.assertEquals('Silence', str(id3['TCON']))
        self.assertEquals('Silence', str(id3['TIT1']))
        self.assertEquals('Silence', str(id3['TIT2']))
        self.assertEquals(3000, +id3['TLEN'])
        self.assertNotEquals(['piman','jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TDRC'])

    def test_23_multiframe_hack(self):
        class ID3hack(ID3):
            "Override 'correct' behavior with desired behavior"
            def loaded_frame(self, tag):
                if tag.HashKey in self: self[tag.HashKey].extend(tag[:])
                else: self[tag.HashKey] = tag

        id3 = ID3hack(self.silence)
        self.assertEquals(8, len(id3.keys()))
        self.assertEquals(0, len(id3.unknown_frames))
        self.assertEquals('Quod Libet Test Data', id3['TALB'])
        self.assertEquals('Silence', str(id3['TCON']))
        self.assertEquals('Silence', str(id3['TIT1']))
        self.assertEquals('Silence', str(id3['TIT2']))
        self.assertEquals(3000, +id3['TLEN'])
        self.assertEquals(['piman','jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TDRC'])

    def test_badencoding(self):
        self.assertRaises(IndexError, Frames["TPE1"].fromData, _24, 0, "\x09ab")
        self.assertRaises(ValueError, Frames["TPE1"], encoding=9, text="ab")

    def test_badsync(self):
        self.assertRaises(
            ValueError, Frames["TPE1"].fromData, _24, 0x02, "\x00\xff\xfe")

    def test_noencrypt(self):
        self.assertRaises(
            NotImplementedError, Frames["TPE1"].fromData, _24, 0x04, "\x00")
        self.assertRaises(
            NotImplementedError, Frames["TPE1"].fromData, _23, 0x40, "\x00")

    def test_badcompress(self):
        self.assertRaises(
            ValueError, Frames["TPE1"].fromData, _24, 0x08, "\x00\x00\x00\x00#")
        self.assertRaises(
            ValueError, Frames["TPE1"].fromData, _23, 0x80, "\x00\x00\x00\x00#")

    def test_junkframe(self):
        self.assertRaises(ValueError, Frames["TPE1"].fromData, _24, 0, "")

    def test_bad_sylt(self):
        self.assertRaises(
            ID3JunkFrameError, Frames["SYLT"].fromData, _24, 0x0,
            "\x00eng\x01description\x00foobar")

    def test_extradata(self):
        from mutagen.id3 import RVRB, RBUF
        self.assertRaises(ID3Warning,
                RVRB()._readData, 'L1R1BBFFFFPP#xyz')
        self.assertRaises(ID3Warning,
                RBUF()._readData, '\x00\x01\x00\x01\x00\x00\x00\x00#xyz')

class ID3v1Tags(TestCase):
    uses_mmap = False

    def setUp(self):
        self.silence = join('tests', 'data', 'silence-44-s-v1.mp3')
        self.id3 = ID3(self.silence)

    def test_album(self):
        self.assertEquals('Quod Libet Test Data', self.id3['TALB'])
    def test_genre(self):
        self.assertEquals('Darkwave', self.id3['TCON'].genres[0])
    def test_title(self):
        self.assertEquals('Silence', str(self.id3['TIT2']))
    def test_artist(self):
        self.assertEquals(['piman'], self.id3['TPE1'])
    def test_track(self):
        self.assertEquals('2', self.id3['TRCK'])
        self.assertEquals(2, +self.id3['TRCK'])
    def test_year(self):
        self.assertEquals('2004', self.id3['TDRC'])

    def test_v1_not_v11(self):
        from mutagen.id3 import MakeID3v1, ParseID3v1, TRCK
        self.id3["TRCK"] = TRCK(encoding=0, text="32")
        tag = MakeID3v1(self.id3)
        self.failUnless(32, ParseID3v1(tag)["TRCK"])
        del(self.id3["TRCK"])
        tag = MakeID3v1(self.id3)
        tag = tag[:125] + '  ' + tag[-1]
        self.failIf("TRCK" in ParseID3v1(tag))

    def test_nulls(self):
        from mutagen.id3 import ParseID3v1
        s = 'TAG%(title)30s%(artist)30s%(album)30s%(year)4s%(cmt)29s\x03\x01'
        s = s % dict(artist='abcd\00fg', title='hijklmn\x00p',
                    album='qrst\x00v', cmt='wxyz', year='1224')
        tags = ParseID3v1(s)
        self.assertEquals('abcd'.decode('latin1'), tags['TPE1'])
        self.assertEquals('hijklmn'.decode('latin1'), tags['TIT2'])
        self.assertEquals('qrst'.decode('latin1'), tags['TALB'])

    def test_nonascii(self):
        from mutagen.id3 import ParseID3v1
        s = 'TAG%(title)30s%(artist)30s%(album)30s%(year)4s%(cmt)29s\x03\x01'
        s = s % dict(artist='abcd\xe9fg', title='hijklmn\xf3p',
                    album='qrst\xfcv', cmt='wxyz', year='1234')
        tags = ParseID3v1(s)
        self.assertEquals('abcd\xe9fg'.decode('latin1'), tags['TPE1'])
        self.assertEquals('hijklmn\xf3p'.decode('latin1'), tags['TIT2'])
        self.assertEquals('qrst\xfcv'.decode('latin1'), tags['TALB'])
        self.assertEquals('wxyz', tags['COMM'])
        self.assertEquals("3", tags['TRCK'])
        self.assertEquals("1234", tags['TDRC'])

    def test_roundtrip(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1
        frames = {}
        for key in ["TIT2", "TALB", "TPE1", "TDRC"]:
            frames[key] = self.id3[key]
        self.assertEquals(ParseID3v1(MakeID3v1(frames)), frames)

    def test_make_from_empty(self):
        from mutagen.id3 import MakeID3v1, TCON, COMM
        empty = 'TAG' + '\x00' * 124 + '\xff'
        self.assertEquals(MakeID3v1({}), empty)
        self.assertEquals(MakeID3v1({'TCON': TCON()}), empty)
        self.assertEquals(
            MakeID3v1({'COMM': COMM(encoding=0, text="")}), empty)

    def test_make_v1_from_tyer(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1, TYER, TDRC
        self.assertEquals(
            MakeID3v1({"TDRC": TDRC(text="2010-10-10")}),
            MakeID3v1({"TYER": TYER(text="2010")}))
        self.assertEquals(
            ParseID3v1(MakeID3v1({"TDRC": TDRC(text="2010-10-10")})),
            ParseID3v1(MakeID3v1({"TYER": TYER(text="2010")})))

    def test_invalid(self):
        from mutagen.id3 import ParseID3v1
        self.failUnless(ParseID3v1("") is None)

    def test_invalid_track(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1, TRCK
        tag = {}
        tag["TRCK"] = TRCK(encoding=0, text="not a number")
        v1tag = MakeID3v1(tag)
        self.failIf("TRCK" in ParseID3v1(v1tag))

    def test_v1_genre(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1, TCON
        tag = {}
        tag["TCON"] = TCON(encoding=0, text="Pop")
        v1tag = MakeID3v1(tag)
        self.failUnlessEqual(ParseID3v1(v1tag)["TCON"].genres, ["Pop"])

class TestWriteID3v1(TestCase):
    SILENCE = os.path.join("tests", "data", "silence-44-s.mp3")
    def setUp(self):
        from tempfile import mkstemp
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(self.SILENCE, self.filename)
        self.audio = ID3(self.filename)

    def failIfV1(self):
        fileobj = file(self.filename, "rb")
        fileobj.seek(-128, 2)
        self.failIf(fileobj.read(3) == "TAG")

    def failUnlessV1(self):
        fileobj = file(self.filename, "rb")
        fileobj.seek(-128, 2)
        self.failUnless(fileobj.read(3) == "TAG")

    def test_save_delete(self):
        self.audio.save(v1=0)
        self.failIfV1()

    def test_save_add(self):
        self.audio.save(v1=2)
        self.failUnlessV1()

    def test_save_defaults(self):
        self.audio.save(v1=0)
        self.failIfV1()
        self.audio.save(v1=1)
        self.failIfV1()
        self.audio.save(v1=2)
        self.failUnlessV1()
        self.audio.save(v1=1)
        self.failUnlessV1()

    def tearDown(self):
        os.unlink(self.filename)

add(TestWriteID3v1)

class TestV22Tags(TestCase):
    uses_mmap = False

    def setUp(self):
        filename = os.path.join("tests", "data", "id3v22-test.mp3")
        self.tags = ID3(filename)

    def test_tags(self):
        self.failUnless(self.tags["TRCK"].text == ["3/11"])
        self.failUnless(self.tags["TPE1"].text == ["Anais Mitchell"])
add(TestV22Tags)

def TestReadTags():
    tests = [
    ['TALB', '\x00a/b', 'a/b', '', dict(encoding=0)],
    ['TBPM', '\x00120', '120', 120, dict(encoding=0)],
    ['TCMP', '\x001', '1', 1, dict(encoding=0)],
    ['TCMP', '\x000', '0', 0, dict(encoding=0)],
    ['TCOM', '\x00a/b', 'a/b', '', dict(encoding=0)],
    ['TCON', '\x00(21)Disco', '(21)Disco', '', dict(encoding=0)],
    ['TCOP', '\x001900 c', '1900 c', '', dict(encoding=0)],
    ['TDAT', '\x00a/b', 'a/b', '', dict(encoding=0)],
    ['TDEN', '\x001987', '1987', '', dict(encoding=0, year=[1987])],
    ['TDOR', '\x001987-12', '1987-12', '',
     dict(encoding=0, year=[1987], month=[12])],
    ['TDRC', '\x001987\x00', '1987', '', dict(encoding=0, year=[1987])],
    ['TDRL', '\x001987\x001988', '1987,1988', '',
     dict(encoding=0, year=[1987,1988])],
    ['TDTG', '\x001987', '1987', '', dict(encoding=0, year=[1987])],
    ['TDLY', '\x001205', '1205', 1205, dict(encoding=0)],
    ['TENC', '\x00a b/c d', 'a b/c d', '', dict(encoding=0)],
    ['TEXT', '\x00a b\x00c d', ['a b', 'c d'], '', dict(encoding=0)],
    ['TFLT', '\x00MPG/3', 'MPG/3', '', dict(encoding=0)],
    ['TIME', '\x001205', '1205', '', dict(encoding=0)],
    ['TIPL', '\x02\x00a\x00\x00\x00b', [["a", "b"]], '', dict(encoding=2)],
    ['TIT1', '\x00a/b', 'a/b', '', dict(encoding=0)],
    # TIT2 checks misaligned terminator '\x00\x00' across crosses utf16 chars
    ['TIT2', '\x01\xff\xfe\x38\x00\x00\x38', u'8\u3800', '', dict(encoding=1)],
    ['TIT3', '\x00a/b', 'a/b', '', dict(encoding=0)],
    ['TKEY', '\x00A#m', 'A#m', '', dict(encoding=0)],
    ['TLAN', '\x006241', '6241', '', dict(encoding=0)],
    ['TLEN', '\x006241', '6241', 6241, dict(encoding=0)],
    ['TMCL', '\x02\x00a\x00\x00\x00b', [["a", "b"]], '', dict(encoding=2)],
    ['TMED', '\x00med', 'med', '', dict(encoding=0)],
    ['TMOO', '\x00moo', 'moo', '', dict(encoding=0)],
    ['TOAL', '\x00alb', 'alb', '', dict(encoding=0)],
    ['TOFN', '\x0012 : bar', '12 : bar', '', dict(encoding=0)],
    ['TOLY', '\x00lyr', 'lyr', '', dict(encoding=0)],
    ['TOPE', '\x00own/lic', 'own/lic', '', dict(encoding=0)],
    ['TORY', '\x001923', '1923', 1923, dict(encoding=0)],
    ['TOWN', '\x00own/lic', 'own/lic', '', dict(encoding=0)],
    ['TPE1', '\x00ab', ['ab'], '', dict(encoding=0)],
    ['TPE2', '\x00ab\x00cd\x00ef', ['ab','cd','ef'], '', dict(encoding=0)],
    ['TPE3', '\x00ab\x00cd', ['ab','cd'], '', dict(encoding=0)],
    ['TPE4', '\x00ab\x00', ['ab'], '', dict(encoding=0)],
    ['TPOS', '\x0008/32', '08/32', 8, dict(encoding=0)],
    ['TPRO', '\x00pro', 'pro', '', dict(encoding=0)],
    ['TPUB', '\x00pub', 'pub', '', dict(encoding=0)],
    ['TRCK', '\x004/9', '4/9', 4, dict(encoding=0)],
    ['TRDA', '\x00Sun Jun 12', 'Sun Jun 12', '', dict(encoding=0)],
    ['TRSN', '\x00ab/cd', 'ab/cd', '', dict(encoding=0)],
    ['TRSO', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSIZ', '\x0012345', '12345', 12345, dict(encoding=0)],
    ['TSOA', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSOP', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSOT', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSO2', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSOC', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TSRC', '\x0012345', '12345', '', dict(encoding=0)],
    ['TSSE', '\x0012345', '12345', '', dict(encoding=0)],
    ['TSST', '\x0012345', '12345', '', dict(encoding=0)],
    ['TYER', '\x002004', '2004', 2004, dict(encoding=0)],

    ['TXXX', '\x00usr\x00a/b\x00c', ['a/b','c'], '',
     dict(encoding=0, desc='usr')],

    ['WCOM', 'http://foo', 'http://foo', '', {}],
    ['WCOP', 'http://bar', 'http://bar', '', {}],
    ['WOAF', 'http://baz', 'http://baz', '', {}],
    ['WOAR', 'http://bar', 'http://bar', '', {}],
    ['WOAS', 'http://bar', 'http://bar', '', {}],
    ['WORS', 'http://bar', 'http://bar', '', {}],
    ['WPAY', 'http://bar', 'http://bar', '', {}],
    ['WPUB', 'http://bar', 'http://bar', '', {}],

    ['WXXX', '\x00usr\x00http', 'http', '', dict(encoding=0, desc='usr')],

    ['IPLS', '\x00a\x00A\x00b\x00B\x00', [['a','A'],['b','B']], '',
        dict(encoding=0)],

    ['MCDI', '\x01\x02\x03\x04', '\x01\x02\x03\x04', '', {}],
    
    ['ETCO', '\x01\x12\x00\x00\x7f\xff', [(18, 32767)], '', dict(format=1)],

    ['COMM', '\x00ENUT\x00Com', 'Com', '',
        dict(desc='T', lang='ENU', encoding=0)],
    # found in a real MP3
    ['COMM', '\x00\x00\xcc\x01\x00     ', '     ', '',
        dict(desc=u'', lang='\x00\xcc\x01', encoding=0)],

    ['APIC', '\x00-->\x00\x03cover\x00cover.jpg', 'cover.jpg', '',
        dict(mime='-->', type=3, desc='cover', encoding=0)],
    ['USER', '\x00ENUCom', 'Com', '', dict(lang='ENU', encoding=0)],

    ['RVA2', 'testdata\x00\x01\xfb\x8c\x10\x12\x23',
        'Master volume: -2.2266 dB/0.1417', '',
        dict(desc='testdata', channel=1, gain=-2.22656, peak=0.14169)],

    ['RVA2', 'testdata\x00\x01\xfb\x8c\x24\x01\x22\x30\x00\x00',
        'Master volume: -2.2266 dB/0.1417', '',
        dict(desc='testdata', channel=1, gain=-2.22656, peak=0.14169)],

    ['RVA2', 'testdata2\x00\x01\x04\x01\x00',
        'Master volume: +2.0020 dB/0.0000', '',
        dict(desc='testdata2', channel=1, gain=2.001953125, peak=0)],

    ['PCNT', '\x00\x00\x00\x11', 17, 17, dict(count=17)],
    ['POPM', 'foo@bar.org\x00\xde\x00\x00\x00\x11', 222, 222,
        dict(email="foo@bar.org", rating=222, count=17)],
    ['POPM', 'foo@bar.org\x00\xde\x00', 222, 222,
        dict(email="foo@bar.org", rating=222, count=0)],
    # Issue #33 - POPM may have no playcount at all.
    ['POPM', 'foo@bar.org\x00\xde', 222, 222,
        dict(email="foo@bar.org", rating=222)],

    ['UFID', 'own\x00data', 'data', '', dict(data='data', owner='own')],
    ['UFID', 'own\x00\xdd', '\xdd', '', dict(data='\xdd', owner='own')],

    ['GEOB', '\x00mime\x00name\x00desc\x00data', 'data', '',
        dict(encoding=0, mime='mime', filename='name', desc='desc')],

    ['USLT', '\x00engsome lyrics\x00woo\nfun', 'woo\nfun', '',
     dict(encoding=0, lang='eng', desc='some lyrics', text='woo\nfun')],

    ['SYLT', ('\x00eng\x02\x01some lyrics\x00foo\x00\x00\x00\x00\x01bar'
              '\x00\x00\x00\x00\x10'), "foobar", '',
     dict(encoding=0, lang='eng', type=1, format=2, desc='some lyrics')],

    ['POSS', '\x01\x0f', 15, 15, dict(format=1, position=15)],
    ['OWNE', '\x00USD10.01\x0020041010CDBaby', 'CDBaby', 'CDBaby',
     dict(encoding=0, price="USD10.01", date='20041010', seller='CDBaby')],

    ['PRIV', 'a@b.org\x00random data', 'random data', 'random data',
     dict(owner='a@b.org', data='random data')],
    ['PRIV', 'a@b.org\x00\xdd', '\xdd', '\xdd',
     dict(owner='a@b.org', data='\xdd')],

    ['SIGN', '\x92huh?', 'huh?', 'huh?', dict(group=0x92, sig='huh?')],
    ['ENCR', 'a@b.org\x00\x92Data!', 'Data!', 'Data!',
     dict(owner='a@b.org', method=0x92, data='Data!')],
    ['SEEK', '\x00\x12\x00\x56', 0x12*256*256+0x56, 0x12*256*256+0x56,
     dict(offset=0x12*256*256+0x56)],

    ['SYTC', "\x01\x10obar", '\x10obar', '', dict(format=1, data='\x10obar')],
    
    ['RBUF', '\x00\x12\x00', 0x12*256, 0x12*256, dict(size=0x12*256)],
    ['RBUF', '\x00\x12\x00\x01', 0x12*256, 0x12*256,
     dict(size=0x12*256, info=1)],
    ['RBUF', '\x00\x12\x00\x01\x00\x00\x00\x23', 0x12*256, 0x12*256,
     dict(size=0x12*256, info=1, offset=0x23)],

    ['RVRB', '\x12\x12\x23\x23\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11',
     (0x12*256+0x12, 0x23*256+0x23), '',
     dict(left=0x12*256+0x12, right=0x23*256+0x23) ],

    ['AENC', 'a@b.org\x00\x00\x12\x00\x23', 'a@b.org', 'a@b.org',
     dict(owner='a@b.org', preview_start=0x12, preview_length=0x23)],
    ['AENC', 'a@b.org\x00\x00\x12\x00\x23!', 'a@b.org', 'a@b.org',
     dict(owner='a@b.org', preview_start=0x12, preview_length=0x23, data='!')],

    ['GRID', 'a@b.org\x00\x99', 'a@b.org', 0x99,
     dict(owner='a@b.org', group=0x99)],
    ['GRID', 'a@b.org\x00\x99data', 'a@b.org', 0x99,
     dict(owner='a@b.org', group=0x99, data='data')],

    ['COMR', '\x00USD10.00\x0020051010ql@sc.net\x00\x09Joe\x00A song\x00'
     'x-image/fake\x00some data',
     COMR(encoding=0, price="USD10.00", valid_until="20051010",
          contact="ql@sc.net", format=9, seller="Joe", desc="A song",
          mime='x-image/fake', logo='some data'), '',
     dict(
        encoding=0, price="USD10.00", valid_until="20051010",
        contact="ql@sc.net", format=9, seller="Joe", desc="A song",
        mime='x-image/fake', logo='some data')],

    ['COMR', '\x00USD10.00\x0020051010ql@sc.net\x00\x09Joe\x00A song\x00',
     COMR(encoding=0, price="USD10.00", valid_until="20051010",
          contact="ql@sc.net", format=9, seller="Joe", desc="A song"), '',
     dict(
        encoding=0, price="USD10.00", valid_until="20051010",
        contact="ql@sc.net", format=9, seller="Joe", desc="A song")],

    ['MLLT', '\x00\x01\x00\x00\x02\x00\x00\x03\x04\x08foobar', 'foobar', '',
     dict(frames=1, bytes=2, milliseconds=3, bits_for_bytes=4,
          bits_for_milliseconds=8, data='foobar')],

    ['EQU2', '\x00Foobar\x00\x01\x01\x04\x00', [(128.5, 2.0)], '',
     dict(method=0, desc="Foobar")],

    ['ASPI', '\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x08\x01\x02\x03',
     [1, 2, 3], '', dict(S=0, L=16, N=3, b=8)],

    ['ASPI', '\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x10'
     '\x00\x01\x00\x02\x00\x03', [1, 2, 3], '', dict(S=0, L=16, N=3, b=16)],

    ['LINK', 'TIT1http://www.example.org/TIT1.txt\x00',
     ("TIT1", 'http://www.example.org/TIT1.txt'), '',
     dict(frameid='TIT1', url='http://www.example.org/TIT1.txt')],
    ['LINK', 'COMMhttp://www.example.org/COMM.txt\x00engfoo',
     ("COMM", 'http://www.example.org/COMM.txt', 'engfoo'), '',
     dict(frameid='COMM', url='http://www.example.org/COMM.txt',
          data='engfoo')],

    # 2.2 tags
    ['UFI', 'own\x00data', 'data', '', dict(data='data', owner='own')],
    ['SLT', ('\x00eng\x02\x01some lyrics\x00foo\x00\x00\x00\x00\x01bar'
              '\x00\x00\x00\x00\x10'), "foobar", '',
     dict(encoding=0, lang='eng', type=1, format=2, desc='some lyrics')],
    ['TT1', '\x00ab\x00', 'ab', '', dict(encoding=0)],
    ['TT2', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TT3', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TP1', '\x00ab\x00', 'ab', '', dict(encoding=0)],
    ['TP2', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TP3', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TP4', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TCM', '\x00ab/cd', 'ab/cd', '', dict(encoding=0)],
    ['TXT', '\x00lyr', 'lyr', '', dict(encoding=0)],
    ['TLA', '\x00ENU', 'ENU', '', dict(encoding=0)],
    ['TCO', '\x00gen', 'gen', '', dict(encoding=0)],
    ['TAL', '\x00alb', 'alb', '', dict(encoding=0)],
    ['TPA', '\x001/9', '1/9', 1, dict(encoding=0)],
    ['TRK', '\x002/8', '2/8', 2, dict(encoding=0)],
    ['TRC', '\x00isrc', 'isrc', '', dict(encoding=0)],
    ['TYE', '\x001900', '1900', 1900, dict(encoding=0)],
    ['TDA', '\x002512', '2512', '', dict(encoding=0)],
    ['TIM', '\x001225', '1225', '', dict(encoding=0)],
    ['TRD', '\x00Jul 17', 'Jul 17', '', dict(encoding=0)],
    ['TMT', '\x00DIG/A', 'DIG/A', '', dict(encoding=0)],
    ['TFT', '\x00MPG/3', 'MPG/3', '', dict(encoding=0)],
    ['TBP', '\x00133', '133', 133, dict(encoding=0)],
    ['TCP', '\x001', '1', 1, dict(encoding=0)],
    ['TCP', '\x000', '0', 0, dict(encoding=0)],
    ['TCR', '\x00Me', 'Me', '', dict(encoding=0)],
    ['TPB', '\x00Him', 'Him', '', dict(encoding=0)],
    ['TEN', '\x00Lamer', 'Lamer', '', dict(encoding=0)],
    ['TSS', '\x00ab', 'ab', '', dict(encoding=0)],
    ['TOF', '\x00ab:cd', 'ab:cd', '', dict(encoding=0)],
    ['TLE', '\x0012', '12', 12, dict(encoding=0)],
    ['TSI', '\x0012', '12', 12, dict(encoding=0)],
    ['TDY', '\x0012', '12', 12, dict(encoding=0)],
    ['TKE', '\x00A#m', 'A#m', '', dict(encoding=0)],
    ['TOT', '\x00org', 'org', '', dict(encoding=0)],
    ['TOA', '\x00org', 'org', '', dict(encoding=0)],
    ['TOL', '\x00org', 'org', '', dict(encoding=0)],
    ['TOR', '\x001877', '1877', 1877, dict(encoding=0)],
    ['TXX', '\x00desc\x00val', 'val', '', dict(encoding=0, desc='desc')],

    ['WAF', 'http://zzz', 'http://zzz', '', {}],
    ['WAR', 'http://zzz', 'http://zzz', '', {}],
    ['WAS', 'http://zzz', 'http://zzz', '', {}],
    ['WCM', 'http://zzz', 'http://zzz', '', {}],
    ['WCP', 'http://zzz', 'http://zzz', '', {}],
    ['WPB', 'http://zzz', 'http://zzz', '', {}],
    ['WXX', '\x00desc\x00http', 'http', '', dict(encoding=0, desc='desc')],

    ['IPL', '\x00a\x00A\x00b\x00B\x00', [['a','A'],['b','B']], '',
        dict(encoding=0)],
    ['MCI', '\x01\x02\x03\x04', '\x01\x02\x03\x04', '', {}],

    ['ETC', '\x01\x12\x00\x00\x7f\xff', [(18, 32767)], '', dict(format=1)],

    ['COM', '\x00ENUT\x00Com', 'Com', '',
        dict(desc='T', lang='ENU', encoding=0)],
    ['PIC', '\x00-->\x03cover\x00cover.jpg', 'cover.jpg', '',
        dict(mime='-->', type=3, desc='cover', encoding=0)],

    ['POP', 'foo@bar.org\x00\xde\x00\x00\x00\x11', 222, 222,
        dict(email="foo@bar.org", rating=222, count=17)],
    ['CNT', '\x00\x00\x00\x11', 17, 17, dict(count=17)],
    ['GEO', '\x00mime\x00name\x00desc\x00data', 'data', '',
        dict(encoding=0, mime='mime', filename='name', desc='desc')],
    ['ULT', '\x00engsome lyrics\x00woo\nfun', 'woo\nfun', '',
     dict(encoding=0, lang='eng', desc='some lyrics', text='woo\nfun')],

    ['BUF', '\x00\x12\x00', 0x12*256, 0x12*256, dict(size=0x12*256)],

    ['CRA', 'a@b.org\x00\x00\x12\x00\x23', 'a@b.org', 'a@b.org',
     dict(owner='a@b.org', preview_start=0x12, preview_length=0x23)],
    ['CRA', 'a@b.org\x00\x00\x12\x00\x23!', 'a@b.org', 'a@b.org',
     dict(owner='a@b.org', preview_start=0x12, preview_length=0x23, data='!')],

    ['REV', '\x12\x12\x23\x23\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11',
     (0x12*256+0x12, 0x23*256+0x23), '',
     dict(left=0x12*256+0x12, right=0x23*256+0x23) ],

    ['STC', "\x01\x10obar", '\x10obar', '', dict(format=1, data='\x10obar')],

    ['MLL', '\x00\x01\x00\x00\x02\x00\x00\x03\x04\x08foobar', 'foobar', '',
     dict(frames=1, bytes=2, milliseconds=3, bits_for_bytes=4,
          bits_for_milliseconds=8, data='foobar')],
    ['LNK', 'TT1http://www.example.org/TIT1.txt\x00',
     ("TT1", 'http://www.example.org/TIT1.txt'), '',
     dict(frameid='TT1', url='http://www.example.org/TIT1.txt')],
    ['CRM', 'foo@example.org\x00test\x00woo',
     'woo', '', dict(owner='foo@example.org', desc='test', data='woo')],

    ]

    load_tests = {}
    repr_tests = {}
    write_tests = {}
    for i, (tag, data, value, intval, info) in enumerate(tests):
        info = info.copy()

        def test_tag(self, tag=tag, data=data, value=value, intval=intval,
                     info=info):
            from operator import pos
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG.fromData(_23, 0, data)
            self.failUnless(tag.HashKey)
            self.failUnless(tag.pprint())
            self.assertEquals(value, tag)
            if 'encoding' not in info:
                self.assertRaises(AttributeError, getattr, tag, 'encoding')
            for attr, value in info.iteritems():
                t = tag
                if not isinstance(value, list):
                    value = [value]
                    t = [t]
                for value, t in zip(value, iter(t)):
                    if isinstance(value, float):
                        self.failUnlessAlmostEqual(value, getattr(t, attr), 5)
                    else: self.assertEquals(value, getattr(t, attr))

                    if isinstance(intval, (int,long)):
                        self.assertEquals(intval, pos(t))
                    else:
                        self.assertRaises(TypeError, pos, t)

        load_tests['test_%s_%d' % (tag, i)] = test_tag

        def test_tag_repr(self, tag=tag, data=data):
            from mutagen.id3 import ID3TimeStamp
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG.fromData(_23, 0, data)
            tag2 = eval(repr(tag), {TAG.__name__:TAG,
                    'ID3TimeStamp':ID3TimeStamp})
            self.assertEquals(type(tag), type(tag2))
            for spec in TAG._framespec:
                attr = spec.name
                self.assertEquals(getattr(tag, attr), getattr(tag2, attr))
        repr_tests['test_repr_%s_%d' % (tag, i)] = test_tag_repr

        def test_tag_write(self, tag=tag, data=data):
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG.fromData(_24, 0, data)
            towrite = tag._writeData()
            tag2 = TAG.fromData(_24, 0, towrite)
            for spec in TAG._framespec:
                attr = spec.name
                self.assertEquals(getattr(tag, attr), getattr(tag2, attr))
        write_tests['test_write_%s_%d' % (tag, i)] = test_tag_write

    testcase = type('TestReadTags', (TestCase,), load_tests)
    testcase.uses_mmap = False
    add(testcase)
    testcase = type('TestReadReprTags', (TestCase,), repr_tests)
    testcase.uses_mmap = False
    add(testcase)
    testcase = type('TestReadWriteTags', (TestCase,), write_tests)
    testcase.uses_mmap = False
    add(testcase)

    test_tests = {}
    from mutagen.id3 import Frames, Frames_2_2
    check = dict.fromkeys(Frames.keys() + Frames_2_2.keys())
    tested_tags = dict.fromkeys([row[0] for row in tests])
    for tag in check:
        def check(self, tag=tag): self.assert_(tag in tested_tags)
        tested_tags['test_' + tag + '_tested'] = check
    testcase = type('TestTestedTags', (TestCase,), tested_tags)
    testcase.uses_mmap = False
    add(testcase)

TestReadTags()
del TestReadTags

class BitPaddedIntTest(TestCase):
    uses_mmap = False

    def test_zero(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x00'), 0)

    def test_1(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x01'), 1)

    def test_1l(self):
        self.assertEquals(BitPaddedInt('\x01\x00\x00\x00', bigendian=False), 1)

    def test_129(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x01'), 0x81)

    def test_129b(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81'), 0x81)

    def test_65(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81', 6), 0x41)

    def test_32b(self):
        self.assertEquals(BitPaddedInt('\xFF\xFF\xFF\xFF', bits=8),
            0xFFFFFFFF)

    def test_32bi(self):
        self.assertEquals(BitPaddedInt(0xFFFFFFFF, bits=8), 0xFFFFFFFF)

    def test_s32b(self):
        self.assertEquals(BitPaddedInt('\xFF\xFF\xFF\xFF', bits=8).as_str(),
            '\xFF\xFF\xFF\xFF')

    def test_s0(self):
        self.assertEquals(BitPaddedInt.to_str(0), '\x00\x00\x00\x00')

    def test_s1(self):
        self.assertEquals(BitPaddedInt.to_str(1), '\x00\x00\x00\x01')

    def test_s1l(self):
        self.assertEquals(
            BitPaddedInt.to_str(1, bigendian=False), '\x01\x00\x00\x00')

    def test_s129(self):
        self.assertEquals(BitPaddedInt.to_str(129), '\x00\x00\x01\x01')

    def test_s65(self):
        self.assertEquals(BitPaddedInt.to_str(0x41, 6), '\x00\x00\x01\x01')

    def test_w129(self):
        self.assertEquals(BitPaddedInt.to_str(129, width=2), '\x01\x01')

    def test_w129l(self):
        self.assertEquals(
            BitPaddedInt.to_str(129, width=2, bigendian=False), '\x01\x01')

    def test_wsmall(self):
        self.assertRaises(ValueError, BitPaddedInt.to_str, 129, width=1)

    def test_str_int_init(self):
        from struct import pack
        self.assertEquals(BitPaddedInt(238).as_str(),
                BitPaddedInt(pack('>L', 238)).as_str())

    def test_varwidth(self):
        self.assertEquals(len(BitPaddedInt.to_str(100)), 4)
        self.assertEquals(len(BitPaddedInt.to_str(100, width=-1)), 4)
        self.assertEquals(len(BitPaddedInt.to_str(2**32, width=-1)), 5)


class SpecSanityChecks(TestCase):
    uses_mmap = False

    def test_bytespec(self):
        from mutagen.id3 import ByteSpec
        s = ByteSpec('name')
        self.assertEquals((97, 'bcdefg'), s.read(None, 'abcdefg'))
        self.assertEquals('a', s.write(None, 97))
        self.assertRaises(TypeError, s.write, None, 'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_encodingspec(self):
        from mutagen.id3 import EncodingSpec
        s = EncodingSpec('name')
        self.assertEquals((0, 'abcdefg'), s.read(None, 'abcdefg'))
        self.assertEquals((3, 'abcdefg'), s.read(None, '\x03abcdefg'))
        self.assertEquals('\x00', s.write(None, 0))
        self.assertRaises(TypeError, s.write, None, 'abc')
        self.assertRaises(TypeError, s.write, None, None)

    def test_stringspec(self):
        from mutagen.id3 import StringSpec
        s = StringSpec('name', 3)
        self.assertEquals(('abc', 'defg'),  s.read(None, 'abcdefg'))
        self.assertEquals('abc', s.write(None, 'abcdefg'))
        self.assertEquals('\x00\x00\x00', s.write(None, None))
        self.assertEquals('\x00\x00\x00', s.write(None, '\x00'))
        self.assertEquals('a\x00\x00', s.write(None, 'a'))

    def test_binarydataspec(self):
        from mutagen.id3 import BinaryDataSpec
        s = BinaryDataSpec('name')
        self.assertEquals(('abcdefg', ''), s.read(None, 'abcdefg'))
        self.assertEquals('None',  s.write(None, None))
        self.assertEquals('43',  s.write(None, 43))

    def test_encodedtextspec(self):
        from mutagen.id3 import EncodedTextSpec, Frame
        s = EncodedTextSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals(('abcd', 'fg'), s.read(f, 'abcd\x00fg'))
        self.assertEquals('abcdefg\x00', s.write(f, 'abcdefg'))
        self.assertRaises(AttributeError, s.write, f, None)

    def test_timestampspec(self):
        from mutagen.id3 import TimeStampSpec, Frame, ID3TimeStamp
        s = TimeStampSpec('name')
        f = Frame(); f.encoding = 0
        self.assertEquals((ID3TimeStamp('ab'), 'fg'), s.read(f, 'ab\x00fg'))
        self.assertEquals((ID3TimeStamp('1234'), ''), s.read(f, '1234\x00'))
        self.assertEquals('1234\x00', s.write(f, ID3TimeStamp('1234')))
        self.assertRaises(AttributeError, s.write, f, None)

    def test_volumeadjustmentspec(self):
        from mutagen.id3 import VolumeAdjustmentSpec
        s = VolumeAdjustmentSpec('gain')
        self.assertEquals((0.0, ''), s.read(None, '\x00\x00'))
        self.assertEquals((2.0, ''), s.read(None, '\x04\x00'))
        self.assertEquals((-2.0, ''), s.read(None, '\xfc\x00'))
        self.assertEquals('\x00\x00', s.write(None, 0.0))
        self.assertEquals('\x04\x00', s.write(None, 2.0))
        self.assertEquals('\xfc\x00', s.write(None, -2.0))

class FrameSanityChecks(TestCase):
    uses_mmap = False

    def test_TF(self):
        from mutagen.id3 import TextFrame
        self.assert_(isinstance(TextFrame(text='text'), TextFrame))

    def test_UF(self):
        from mutagen.id3 import UrlFrame
        self.assert_(isinstance(UrlFrame('url'), UrlFrame))

    def test_WXXX(self):
        from mutagen.id3 import WXXX
        self.assert_(isinstance(WXXX(url='durl'), WXXX))

    def test_NTF(self):
        from mutagen.id3 import NumericTextFrame
        self.assert_(isinstance(NumericTextFrame(text='1'), NumericTextFrame))

    def test_NTPF(self):
        from mutagen.id3 import NumericPartTextFrame
        self.assert_(
            isinstance(NumericPartTextFrame(text='1/2'), NumericPartTextFrame))

    def test_MTF(self):
        from mutagen.id3 import TextFrame
        self.assert_(isinstance(TextFrame(text=['a','b']), TextFrame))

    def test_TXXX(self):
        from mutagen.id3 import TXXX
        self.assert_(isinstance(TXXX(desc='d',text='text'), TXXX))

    def test_22_uses_direct_ints(self):
        data = 'TT1\x00\x00\x83\x00' + ('123456789abcdef' * 16)
        id3 = ID3()
        id3.version = (2,2,0)
        tag = list(id3._ID3__read_frames(data, Frames_2_2))[0]
        self.assertEquals(data[7:7+0x82].decode('latin1'), tag.text[0])

    def test_frame_too_small(self):
        self.assertEquals([], list(_24._ID3__read_frames('012345678', Frames)))
        self.assertEquals([], list(_23._ID3__read_frames('012345678', Frames)))
        self.assertEquals([], list(_22._ID3__read_frames('01234', Frames_2_2)))
        self.assertEquals(
            [], list(_22._ID3__read_frames('TT1'+'\x00'*3, Frames_2_2)))

    def test_unknown_22_frame(self):
        data = 'XYZ\x00\x00\x01\x00'
        self.assertEquals([data], list(_22._ID3__read_frames(data, {})))


    def test_zlib_latin1(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_24, 0x9, '\x00\x00\x00\x0f'
                'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])

    def test_datalen_but_not_compressed(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_24, 0x01, '\x00\x00\x00\x06\x00A test')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['A test'])

    def test_utf8(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_23, 0x00, '\x03this is a test')
        self.assertEquals(tag.encoding, 3)
        self.assertEquals(tag, 'this is a test')

    def test_zlib_utf16(self):
        from mutagen.id3 import TPE1
        data = ('\x00\x00\x00\x1fx\x9cc\xfc\xff\xaf\x84!\x83!\x93\xa1\x98A'
                '\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#')
        tag = TPE1.fromData(_23, 0x80, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

        tag = TPE1.fromData(_24, 0x08, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

    def test_unsync_encode(self):
        from mutagen.id3 import unsynch as un
        for d in ('\xff\xff\xff\xff', '\xff\xf0\x0f\x00', '\xff\x00\x0f\xf0'):
            self.assertEquals(d, un.decode(un.encode(d)))
            self.assertNotEqual(d, un.encode(d))
        self.assertEquals('\xff\x44', un.encode('\xff\x44'))
        self.assertEquals('\xff\x00\x00', un.encode('\xff\x00'))

    def test_unsync_decode(self):
        from mutagen.id3 import unsynch as un
        self.assertRaises(ValueError, un.decode, '\xff\xff\xff\xff')
        self.assertRaises(ValueError, un.decode, '\xff\xf0\x0f\x00')
        self.assertRaises(ValueError, un.decode, '\xff\xe0')
        self.assertEquals('\xff\x44', un.decode('\xff\x44'))

    def test_load_write(self):
        from mutagen.id3 import TPE1, Frames
        artists= [s.decode('utf8') for s in
                  ['\xc2\xb5', '\xe6\x97\xa5\xe6\x9c\xac']]
        artist = TPE1(encoding=3, text=artists)
        id3 = ID3()
        tag = list(id3._ID3__read_frames(
            id3._ID3__save_frame(artist), Frames))[0]
        self.assertEquals('TPE1', type(tag).__name__)
        self.assertEquals(artist.text, tag.text)

    def test_22_to_24(self):
        from mutagen.id3 import TT1, TIT1
        id3 = ID3()
        tt1 = TT1(encoding=0, text=u'whatcha staring at?')
        id3.loaded_frame(tt1)
        tit1 = id3['TIT1']

        self.assertEquals(tt1.encoding, tit1.encoding)
        self.assertEquals(tt1.text, tit1.text)
        self.assert_('TT1' not in id3)

    def test_single_TXYZ(self):
        from mutagen.id3 import TIT2
        self.assertEquals(TIT2(text="a").HashKey, TIT2(text="b").HashKey)

    def test_multi_TXXX(self):
        from mutagen.id3 import TXXX
        self.assertEquals(TXXX(text="a").HashKey, TXXX(text="b").HashKey)
        self.assertNotEquals(TXXX(desc="a").HashKey, TXXX(desc="b").HashKey)

    def test_multi_WXXX(self):
        from mutagen.id3 import WXXX
        self.assertEquals(WXXX(text="a").HashKey, WXXX(text="b").HashKey)
        self.assertNotEquals(WXXX(desc="a").HashKey, WXXX(desc="b").HashKey)

    def test_multi_COMM(self):
        from mutagen.id3 import COMM
        self.assertEquals(COMM(text="a").HashKey, COMM(text="b").HashKey)
        self.assertNotEquals(COMM(desc="a").HashKey, COMM(desc="b").HashKey)
        self.assertNotEquals(
            COMM(lang="abc").HashKey, COMM(lang="def").HashKey)

    def test_multi_RVA2(self):
        from mutagen.id3 import RVA2
        self.assertEquals(RVA2(gain="1").HashKey, RVA2(gain="2").HashKey)
        self.assertNotEquals(RVA2(desc="a").HashKey, RVA2(desc="b").HashKey)

    def test_multi_APIC(self):
        from mutagen.id3 import APIC
        self.assertEquals(APIC(data="1").HashKey, APIC(data="2").HashKey)
        self.assertNotEquals(APIC(desc="a").HashKey, APIC(desc="b").HashKey)

    def test_multi_POPM(self):
        from mutagen.id3 import POPM
        self.assertEquals(POPM(count=1).HashKey, POPM(count=2).HashKey)
        self.assertNotEquals(POPM(email="a").HashKey, POPM(email="b").HashKey)

    def test_multi_GEOB(self):
        from mutagen.id3 import GEOB
        self.assertEquals(GEOB(data="1").HashKey, GEOB(data="2").HashKey)
        self.assertNotEquals(GEOB(desc="a").HashKey, GEOB(desc="b").HashKey)

    def test_multi_UFID(self):
        from mutagen.id3 import UFID
        self.assertEquals(UFID(data="1").HashKey, UFID(data="2").HashKey)
        self.assertNotEquals(UFID(owner="a").HashKey, UFID(owner="b").HashKey)

    def test_multi_USER(self):
        from mutagen.id3 import USER
        self.assertEquals(USER(text="a").HashKey, USER(text="b").HashKey)
        self.assertNotEquals(
            USER(lang="abc").HashKey, USER(lang="def").HashKey)

class UpdateTo24(TestCase):
    uses_mmap = False

    def test_pic(self):
        from mutagen.id3 import PIC
        id3 = ID3()
        id3.version = (2, 2)
        id3.add(PIC(encoding=0, mime="PNG", desc="cover", type=3, data=""))
        id3.update_to_v24()
        self.failUnlessEqual(id3["APIC:cover"].mime, "image/png")

    def test_tyer(self):
        from mutagen.id3 import TYER
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(TYER(encoding=0, text="2006"))
        id3.update_to_v24()
        self.failUnlessEqual(id3["TDRC"], "2006")

    def test_tyer_tdat(self):
        from mutagen.id3 import TYER, TDAT
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(TYER(encoding=0, text="2006"))
        id3.add(TDAT(encoding=0, text="0603"))
        id3.update_to_v24()
        self.failUnlessEqual(id3["TDRC"], "2006-03-06")

    def test_tyer_tdat_time(self):
        from mutagen.id3 import TYER, TDAT, TIME
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(TYER(encoding=0, text="2006"))
        id3.add(TDAT(encoding=0, text="0603"))
        id3.add(TIME(encoding=0, text="1127"))
        id3.update_to_v24()
        self.failUnlessEqual(id3["TDRC"], "2006-03-06 11:27:00")

    def test_tory(self):
        from mutagen.id3 import TORY
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(TORY(encoding=0, text="2006"))
        id3.update_to_v24()
        self.failUnlessEqual(id3["TDOR"], "2006")

    def test_ipls(self):
        from mutagen.id3 import IPLS
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(IPLS(encoding=0, people=[["a", "b"], ["c", "d"]]))
        id3.update_to_v24()
        self.failUnlessEqual(id3["TIPL"], [["a", "b"], ["c", "d"]])


add(UpdateTo24)

class Genres(TestCase):
    uses_mmap = False

    from mutagen.id3 import TCON
    from mutagen._constants import GENRES

    def _g(self, s): return self.TCON(text=s).genres

    def test_empty(self): self.assertEquals(self._g(""), [])

    def test_num(self):
        for i in range(len(self.GENRES)):
            self.assertEquals(self._g("%02d" % i), [self.GENRES[i]])

    def test_parened_num(self):
        for i in range(len(self.GENRES)):
            self.assertEquals(self._g("(%02d)" % i), [self.GENRES[i]])

    def test_unknown(self):
        self.assertEquals(self._g("(255)"), ["Unknown"])
        self.assertEquals(self._g("199"), ["Unknown"])

    def test_parened_multi(self):
        self.assertEquals(self._g("(00)(02)"), ["Blues", "Country"])

    def test_coverremix(self):
        self.assertEquals(self._g("CR"), ["Cover"])
        self.assertEquals(self._g("(CR)"), ["Cover"])
        self.assertEquals(self._g("RX"), ["Remix"])
        self.assertEquals(self._g("(RX)"), ["Remix"])

    def test_parened_text(self):
        self.assertEquals(
            self._g("(00)(02)Real Folk Blues"),
            ["Blues", "Country", "Real Folk Blues"])

    def test_escape(self):
        self.assertEquals(self._g("(0)((A genre)"), ["Blues", "(A genre)"])
        self.assertEquals(self._g("(10)((20)"), ["New Age", "(20)"])

    def test_nullsep(self):
        self.assertEquals(self._g("0\x00A genre"), ["Blues", "A genre"])

    def test_nullsep_empty(self):
        self.assertEquals(self._g("\x000\x00A genre"), ["Blues", "A genre"])

    def test_crazy(self):
        self.assertEquals(
            self._g("(20)(CR)\x0030\x00\x00Another\x00(51)Hooray"),
             ['Alternative', 'Cover', 'Fusion', 'Another',
              'Techno-Industrial', 'Hooray'])

    def test_repeat(self):
        self.assertEquals(self._g("(20)Alternative"), ["Alternative"])
        self.assertEquals(
            self._g("(20)\x00Alternative"), ["Alternative", "Alternative"])

    def test_set_genre(self):
        gen = self.TCON(encoding=0, text="")
        self.assertEquals(gen.genres, [])
        gen.genres = ["a genre", "another"]
        self.assertEquals(gen.genres, ["a genre", "another"])

    def test_nodoubledecode(self):
        gen = self.TCON(encoding=1, text=u"(255)genre")
        gen.genres = gen.genres
        self.assertEquals(gen.genres, [u"Unknown", u"genre"])

class BrokenDiscarded(TestCase):
    uses_mmap = False

    def test_empty(self):
        from mutagen.id3 import TPE1, ID3JunkFrameError
        self.assertRaises(ID3JunkFrameError, TPE1.fromData, _24, 0x00, '')

    def test_wacky_truncated_RVA2(self):
        from mutagen.id3 import RVA2, ID3JunkFrameError
        data = '\x01{\xf0\x10\xff\xff\x00'
        self.assertRaises(ID3JunkFrameError, RVA2.fromData, _24, 0x00, data)

    def test_bad_number_of_bits_RVA2(self):
        from mutagen.id3 import RVA2, ID3JunkFrameError
        data = '\x00\x00\x01\xe6\xfc\x10{\xd7'
        self.assertRaises(ID3JunkFrameError, RVA2.fromData, _24, 0x00, data)

    def test_drops_truncated_frames(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        tail = '\x00\x00\x00\x03\x00\x00' '\x01\x02\x03'
        for head in 'RVA2 TXXX APIC'.split():
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_drops_nonalphanum_frames(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        tail = '\x00\x00\x00\x03\x00\x00' '\x01\x02\x03'
        for head in ['\x06\xaf\xfe\x20', 'ABC\x00', 'A   ']:
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_bad_unicodedecode(self):
        from mutagen.id3 import COMM, ID3JunkFrameError
        # 7 bytes of "UTF16" data.
        data = '\x01\x00\x00\x00\xff\xfe\x00\xff\xfeh\x00'
        self.assertRaises(ID3JunkFrameError, COMM.fromData, _24, 0x00, data)

class BrokenButParsed(TestCase):
    uses_mmap = False

    def test_missing_encoding(self):
        from mutagen.id3 import TIT2
        tag = TIT2.fromData(_23, 0x00, 'a test')
        self.assertEquals(0, tag.encoding)
        self.assertEquals('a test', tag)
        self.assertEquals(['a test'], tag)
        self.assertEquals(['a test'], tag.text)

    def test_zerolength_framedata(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        tail = '\x00' * 6
        for head in 'WOAR TENC TCOP TOPE WXXX'.split():
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_lengthone_utf16(self):
        from mutagen.id3 import TPE1
        tpe1 = TPE1.fromData(_24, 0, '\x01\x00')
        self.assertEquals(u'', tpe1)
        tpe1 = TPE1.fromData(_24, 0, '\x01\x00\x00\x00\x00')
        self.assertEquals([u'', u''], tpe1)

    def test_fake_zlib_pedantic(self):
        from mutagen.id3 import TPE1, Frame, ID3BadCompressedData
        id3 = ID3()
        id3.PEDANTIC = True
        self.assertRaises(ID3BadCompressedData, TPE1.fromData, id3,
                          Frame.FLAG24_COMPRESS, '\x03abcdefg')

    def test_zlib_bpi(self):
        from mutagen.id3 import TPE1, Frame, ID3BadCompressedData
        id3 = ID3()
        tpe1 = TPE1(encoding=0, text="a" * (0xFFFF - 2))
        data = id3._ID3__save_frame(tpe1)
        datalen_size = data[4 + 4 + 2:4 + 4 + 2 + 4]
        self.failIf(
            max(datalen_size) >= '\x80', "data is not syncsafe: %r" % data)

    def test_fake_zlib_nopedantic(self):
        from mutagen.id3 import TPE1, Frame, ID3BadCompressedData
        id3 = ID3()
        id3.PEDANTIC = False
        tpe1 = TPE1.fromData(id3, Frame.FLAG24_COMPRESS, '\x03abcdefg')
        self.assertEquals(u'abcdefg', tpe1)

    def test_ql_0_12_missing_uncompressed_size(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_24, 0x08, 'x\x9cc\xfc\xff\xaf\x84!\x83!\x93'
                '\xa1\x98A\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#')
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

    def test_zlib_latin1_missing_datalen(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_24, 0x8, '\x00\x00\x00\x0f'
                'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])

    def test_detect_23_ints_in_24_frames(self):
        from mutagen.id3 import Frames
        head = 'TIT1\x00\x00\x01\x00\x00\x00\x00'
        tail = 'TPE1\x00\x00\x00\x04\x00\x00Yay!'

        tagsgood = list(_24._ID3__read_frames(head + 'a'*127 + tail, Frames))
        tagsbad = list(_24._ID3__read_frames(head + 'a'*255 + tail, Frames))
        self.assertEquals(2, len(tagsgood))
        self.assertEquals(2, len(tagsbad))
        self.assertEquals('a'*127, tagsgood[0])
        self.assertEquals('a'*255, tagsbad[0])
        self.assertEquals('Yay!', tagsgood[1])
        self.assertEquals('Yay!', tagsbad[1])

        tagsgood = list(_24._ID3__read_frames(head + 'a'*127, Frames))
        tagsbad = list(_24._ID3__read_frames(head + 'a'*255, Frames))
        self.assertEquals(1, len(tagsgood))
        self.assertEquals(1, len(tagsbad))
        self.assertEquals('a'*127, tagsgood[0])
        self.assertEquals('a'*255, tagsbad[0])


class TimeStamp(TestCase):
    uses_mmap = False

    from mutagen.id3 import ID3TimeStamp as Stamp

    def test_Y(self):
        s = self.Stamp('1234')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.text, '1234')

    def test_yM(self):
        s = self.Stamp('1234-56')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.text, '1234-56')

    def test_ymD(self):
        s = self.Stamp('1234-56-78')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.text, '1234-56-78')

    def test_ymdH(self):
        s = self.Stamp('1234-56-78T12')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.text, '1234-56-78 12')

    def test_ymdhM(self):
        s = self.Stamp('1234-56-78T12:34')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.minute, 34)
        self.assertEquals(s.text, '1234-56-78 12:34')

    def test_ymdhmS(self):
        s = self.Stamp('1234-56-78T12:34:56')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.minute, 34)
        self.assertEquals(s.second, 56)
        self.assertEquals(s.text, '1234-56-78 12:34:56')

    def test_Ymdhms(self):
        s = self.Stamp('1234-56-78T12:34:56')
        s.month = None
        self.assertEquals(s.text, '1234')

    def test_alternate_reprs(self):
        s = self.Stamp('1234-56.78 12:34:56')
        self.assertEquals(s.text, '1234-56-78 12:34:56')

    def test_order(self):
        s = self.Stamp('1234')
        t = self.Stamp('1233-12')
        u = self.Stamp('1234-01')

        self.assert_(t < s < u)
        self.assert_(u > s > t)

class OddWrites(TestCase):
    silence = join('tests', 'data', 'silence-44-s.mp3')
    newsilence = join('tests', 'data', 'silence-written.mp3')
    def setUp(self):
        shutil.copy(self.silence, self.newsilence)

    def test_toemptyfile(self):
        os.unlink(self.newsilence)
        file(self.newsilence, "wb").close()
        ID3(self.silence).save(self.newsilence)

    def test_tononfile(self):
        os.unlink(self.newsilence)
        ID3(self.silence).save(self.newsilence)

    def test_1bfile(self):
        os.unlink(self.newsilence)
        f = file(self.newsilence, "wb")
        f.write("!")
        f.close()
        ID3(self.silence).save(self.newsilence)
        self.assert_(os.path.getsize(self.newsilence) > 1)
        self.assertEquals(file(self.newsilence, "rb").read()[-1], "!")

    def tearDown(self):
        try: os.unlink(self.newsilence)
        except OSError: pass

class WriteRoundtrip(TestCase):
    silence = join('tests', 'data', 'silence-44-s.mp3')
    newsilence = join('tests', 'data', 'silence-written.mp3')
    def setUp(self):
        shutil.copy(self.silence, self.newsilence)

    def test_same(self):
        ID3(self.newsilence).save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TALB"], "Quod Libet Test Data")
        self.assertEquals(id3["TCON"], "Silence")
        self.assertEquals(id3["TIT2"], "Silence")
        self.assertEquals(id3["TPE1"], ["jzig"])

    def test_addframe(self):
        from mutagen.id3 import TIT3
        f = ID3(self.newsilence)
        self.assert_("TIT3" not in f)
        f["TIT3"] = TIT3(encoding=0, text="A subtitle!")
        f.save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TIT3"], "A subtitle!")

    def test_changeframe(self):
        from mutagen.id3 import TIT2
        f = ID3(self.newsilence)
        self.assertEquals(f["TIT2"], "Silence")
        f["TIT2"].text = [u"The sound of silence."]
        f.save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TIT2"], "The sound of silence.")

    def test_replaceframe(self):
        from mutagen.id3 import TPE1
        f = ID3(self.newsilence)
        self.assertEquals(f["TPE1"], "jzig")
        f["TPE1"] = TPE1(encoding=0, text=u"jzig\x00piman")
        f.save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TPE1"], ["jzig", "piman"])

    def test_compressibly_large(self):
        from mutagen.id3 import TPE2
        f = ID3(self.newsilence)
        self.assert_("TPE2" not in f)
        f["TPE2"] = TPE2(encoding=0, text="Ab" * 1025)
        f.save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TPE2"], "Ab" * 1025)

    def test_nofile_emptytag(self):
        os.unlink(self.newsilence)
        ID3().save(self.newsilence)
        self.assertRaises(EnvironmentError, open, self.newsilence)

    def test_nofile_silencetag(self):
        id3 = ID3(self.newsilence)
        os.unlink(self.newsilence)
        id3.save(self.newsilence)
        self.assertEquals('ID3', open(self.newsilence).read(3))
        self.test_same()

    def test_emptyfile_silencetag(self):
        id3 = ID3(self.newsilence)
        open(self.newsilence, 'wb').truncate()
        id3.save(self.newsilence)
        self.assertEquals('ID3', open(self.newsilence).read(3))
        self.test_same()

    def test_empty_plustag_minustag_empty(self):
        id3 = ID3(self.newsilence)
        open(self.newsilence, 'wb').truncate()
        id3.save()
        id3.delete()
        self.failIf(id3)
        self.assertEquals(open(self.newsilence).read(10), '')

    def test_empty_plustag_emptytag_empty(self):
        id3 = ID3(self.newsilence)
        open(self.newsilence, 'wb').truncate()
        id3.save()
        id3.clear()
        id3.save()
        self.assertEquals(open(self.newsilence).read(10), '')

    def test_delete_invalid_zero(self):
        open(self.newsilence, 'wb').write('ID3\x04\x00\x00\x00\x00\x00\x00abc')
        ID3(self.newsilence).delete()
        self.assertEquals(open(self.newsilence).read(10), 'abc')

    def test_frame_order(self):
        from mutagen.id3 import TIT2, APIC, TALB, COMM
        f = ID3(self.newsilence)
        f["TIT2"] = TIT2(encoding=0, text="A title!")
        f["APIC"] = APIC(encoding=0, mime="b", type=3, desc='', data="a")
        f["TALB"] = TALB(encoding=0, text="c")
        f["COMM"] = COMM(encoding=0, desc="x", text="y")
        f.save()
        data = open(self.newsilence, 'rb').read()
        self.assert_(data.find("TIT2") < data.find("APIC"))
        self.assert_(data.find("TIT2") < data.find("COMM"))
        self.assert_(data.find("TALB") < data.find("APIC"))
        self.assert_(data.find("TALB") < data.find("COMM"))
        self.assert_(data.find("TIT2") < data.find("TALB"))

    def tearDown(self):
        try: os.unlink(self.newsilence)
        except EnvironmentError: pass

class WriteForEyeD3(TestCase):
    silence = join('tests', 'data', 'silence-44-s.mp3')
    newsilence = join('tests', 'data', 'silence-written.mp3')
    def setUp(self):
        shutil.copy(self.silence, self.newsilence)
        # remove ID3v1 tag
        f = file(self.newsilence, "rb+")
        f.seek(-128, 2)
        f.truncate()
        f.close()

    def test_same(self):
        ID3(self.newsilence).save()
        id3 = eyeD3.tag.Tag(eyeD3.ID3_V2_4)
        id3.link(self.newsilence)

        self.assertEquals(id3.frames["TALB"][0].text, "Quod Libet Test Data")
        self.assertEquals(id3.frames["TCON"][0].text, "Silence")
        self.assertEquals(id3.frames["TIT2"][0].text, "Silence")
        # "piman" should have been cleared
        self.assertEquals(len(id3.frames["TPE1"]), 1)
        self.assertEquals(id3.frames["TPE1"][0].text, "jzig")

    def test_addframe(self):
        from mutagen.id3 import TIT3
        f = ID3(self.newsilence)
        self.assert_("TIT3" not in f)
        f["TIT3"] = TIT3(encoding=0, text="A subtitle!")
        f.save()
        id3 = eyeD3.tag.Tag(eyeD3.ID3_V2_4)
        id3.link(self.newsilence)
        self.assertEquals(id3.frames["TIT3"][0].text, "A subtitle!")

    def test_changeframe(self):
        from mutagen.id3 import TIT2
        f = ID3(self.newsilence)
        self.assertEquals(f["TIT2"], "Silence")
        f["TIT2"].text = [u"The sound of silence."]
        f.save()
        id3 = eyeD3.tag.Tag(eyeD3.ID3_V2_4)
        id3.link(self.newsilence)
        self.assertEquals(id3.frames["TIT2"][0].text, "The sound of silence.")

    def tearDown(self):
        os.unlink(self.newsilence)

class NoHash(TestCase):
    uses_mmap = False

    def test_spec(self):
        from mutagen.id3 import Spec
        self.failUnlessRaises(TypeError, {}.__setitem__, Spec("foo"), None)

    def test_frame(self):
        from mutagen.id3 import TIT1
        self.failUnlessRaises(
            TypeError, {}.__setitem__, TIT1(encoding=0, text="foo"), None)

class FrameIDValidate(TestCase):
    uses_mmap = False

    def test_valid(self):
        from mutagen.id3 import is_valid_frame_id
        self.failUnless(is_valid_frame_id("APIC"))
        self.failUnless(is_valid_frame_id("TPE2"))

    def test_invalid(self):
        from mutagen.id3 import is_valid_frame_id
        self.failIf(is_valid_frame_id("MP3e"))
        self.failIf(is_valid_frame_id("+ABC"))

class BadTYER(TestCase):
    uses_mmap = False
    filename = join('tests', 'data', 'bad-TYER-frame.mp3')
    def setUp(self):
        self.audio = ID3(self.filename)

    def test_no_year(self):
        self.failIf("TYER" in self.audio)

    def test_has_title(self):
        self.failUnless("TIT2" in self.audio)

    def tearDown(self):
        del(self.audio)

class BadPOPM(TestCase):
    uses_mmap = False
    filename = join('tests', 'data', 'bad-POPM-frame.mp3')
    newfilename = join('tests', 'data', 'bad-POPM-frame-written.mp3')

    def setUp(self):
        shutil.copy(self.filename, self.newfilename)

    def tearDown(self):
        try: os.unlink(self.newfilename)
        except EnvironmentError: pass

    def test_read_popm_long_counter(self):
        f = ID3(self.newfilename)
        self.failUnless("POPM:Windows Media Player 9 Series" in f)
        popm = f["POPM:Windows Media Player 9 Series"]
        self.assertEquals(popm.rating, 255)
        self.assertEquals(popm.count, 2709193061)

    def test_write_popm_long_counter(self):
        from mutagen.id3 import POPM
        f = ID3(self.newfilename)
        f.add(POPM(email="foo@example.com", rating=125, count=2**32+1))
        f.save()
        f = ID3(self.newfilename)
        self.failUnless("POPM:foo@example.com" in f)
        self.failUnless("POPM:Windows Media Player 9 Series" in f)
        popm = f["POPM:foo@example.com"]
        self.assertEquals(popm.rating, 125)
        self.assertEquals(popm.count, 2**32+1)

class TimeStampTextFrame(TestCase):
    uses_mmap = False

    from mutagen.id3 import TimeStampTextFrame as Frame

    def test_compare_to_unicode(self):
        frame = self.Frame(encoding=0, text=[u'1987', u'1988'])
        self.failUnlessEqual(frame, unicode(frame))

add(ID3Loading)
add(ID3GetSetDel)
add(BitPaddedIntTest)
add(ID3Tags)
add(ID3v1Tags)
add(BrokenDiscarded)
add(BrokenButParsed)
add(FrameSanityChecks)
add(SpecSanityChecks)
add(Genres)
add(TimeStamp)
add(WriteRoundtrip)
add(OddWrites)
add(NoHash)
add(FrameIDValidate)
add(BadTYER)
add(BadPOPM)
add(TimeStampTextFrame)

try: import eyeD3
except ImportError: pass
else: add(WriteForEyeD3)
