# -*- coding: utf-8 -*-

import os
from os.path import join
import shutil
from tests import TestCase, DATA_DIR
from mutagen import id3
from mutagen import MutagenError
from mutagen.apev2 import APEv2
from mutagen.id3 import ID3, COMR, Frames, Frames_2_2, ID3Warning, \
    ID3JunkFrameError, ID3Header, ID3UnsupportedVersionError, _fullread, TIT2
from mutagen.id3._util import BitPaddedInt, error as ID3Error
from mutagen._compat import cBytesIO, PY2, iteritems, integer_types, izip
import warnings
from tempfile import mkstemp
warnings.simplefilter('error', ID3Warning)

_22 = ID3Header()
_22.version = (2, 2, 0)
_23 = ID3Header()
_23.version = (2, 3, 0)
_24 = ID3Header()
_24.version = (2, 4, 0)


class ID3GetSetDel(TestCase):

    def setUp(self):
        self.frames = [
            TIT2(text=["1"]), TIT2(text=["2"]),
            TIT2(text=["3"]), TIT2(text=["4"])]
        self.i = ID3()
        self.i["BLAH"] = self.frames[0]
        self.i["QUUX"] = self.frames[1]
        self.i["FOOB:ar"] = self.frames[2]
        self.i["FOOB:az"] = self.frames[3]

    def test_getnormal(self):
        self.assertEquals(self.i.getall("BLAH"), [self.frames[0]])
        self.assertEquals(self.i.getall("QUUX"), [self.frames[1]])
        self.assertEquals(self.i.getall("FOOB:ar"), [self.frames[2]])
        self.assertEquals(self.i.getall("FOOB:az"), [self.frames[3]])

    def test_getlist(self):
        self.assertTrue(
            self.i.getall("FOOB") in [[self.frames[2], self.frames[3]],
                                      [self.frames[3], self.frames[2]]])

    def test_delnormal(self):
        self.assert_("BLAH" in self.i)
        self.i.delall("BLAH")
        self.assert_("BLAH" not in self.i)

    def test_delone(self):
        self.i.delall("FOOB:ar")
        self.assertEquals(self.i.getall("FOOB"), [self.frames[3]])

    def test_delall(self):
        self.assert_("FOOB:ar" in self.i)
        self.assert_("FOOB:az" in self.i)
        self.i.delall("FOOB")
        self.assert_("FOOB:ar" not in self.i)
        self.assert_("FOOB:az" not in self.i)

    def test_setone(self):
        class TEST(TIT2):
            HashKey = ""

        t = TEST()
        t.HashKey = "FOOB:ar"
        self.i.setall("FOOB", [t])
        self.assertEquals(self.i["FOOB:ar"], t)
        self.assertEquals(self.i.getall("FOOB"), [t])

    def test_settwo(self):
        class TEST(TIT2):
            HashKey = ""

        t = TEST()
        t.HashKey = "FOOB:ar"
        t2 = TEST()
        t2.HashKey = "FOOB:az"
        self.i.setall("FOOB", [t, t2])
        self.assertEquals(self.i["FOOB:ar"], t)
        self.assertEquals(self.i["FOOB:az"], t2)
        self.assert_(self.i.getall("FOOB") in [[t, t2], [t2, t]])


class ID3Loading(TestCase):

    empty = join(DATA_DIR, 'emptyfile.mp3')
    silence = join(DATA_DIR, 'silence-44-s.mp3')
    unsynch = join(DATA_DIR, 'id3v23_unsynch.id3')

    def test_empty_file(self):
        name = self.empty
        self.assertRaises(ID3Error, ID3, filename=name)

    def test_nonexistent_file(self):
        name = join(DATA_DIR, 'does', 'not', 'exist')
        self.assertRaises(MutagenError, ID3, name)

    def test_read_padding(self):
        self.assertEqual(ID3(self.silence)._padding, 1142)
        self.assertEqual(ID3(self.unsynch)._padding, 0)

    def test_header_empty(self):
        fileobj = open(self.empty, 'rb')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_silence(self):
        fileobj = open(self.silence, 'rb')
        header = ID3Header(fileobj)
        self.assertEquals(header.version, (2, 3, 0))
        self.assertEquals(header.size, 1314)

    def test_header_2_4_invalid_flags(self):
        fileobj = cBytesIO(b'ID3\x04\x00\x1f\x00\x00\x00\x00')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_4_unsynch_size(self):
        fileobj = cBytesIO(b'ID3\x04\x00\x10\x00\x00\x00\xFF')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_4_allow_footer(self):
        fileobj = cBytesIO(b'ID3\x04\x00\x10\x00\x00\x00\x00')
        self.assertTrue(ID3Header(fileobj).f_footer)

    def test_header_2_3_invalid_flags(self):
        fileobj = cBytesIO(b'ID3\x03\x00\x1f\x00\x00\x00\x00')
        self.assertRaises(ID3Error, ID3Header, fileobj)

        fileobj = cBytesIO(b'ID3\x03\x00\x0f\x00\x00\x00\x00')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_2(self):
        fileobj = cBytesIO(b'ID3\x02\x00\x00\x00\x00\x00\x00')
        header = ID3Header(fileobj)
        self.assertEquals(header.version, (2, 2, 0))

    def test_header_2_1(self):
        fileobj = cBytesIO(b'ID3\x01\x00\x00\x00\x00\x00\x00')
        self.assertRaises(ID3UnsupportedVersionError, ID3Header, fileobj)

    def test_header_too_small(self):
        fileobj = cBytesIO(b'ID3\x01\x00\x00\x00\x00\x00')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_4_extended(self):
        fileobj = cBytesIO(
            b'ID3\x04\x00\x40\x00\x00\x00\x00\x00\x00\x00\x05\x5a')
        header = ID3Header(fileobj)
        self.assertEquals(header._extdata, b'\x5a')

    def test_header_2_4_extended_unsynch_size(self):
        fileobj = cBytesIO(
            b'ID3\x04\x00\x40\x00\x00\x00\x00\x00\x00\x00\xFF\x5a')
        self.assertRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_4_extended_but_not(self):
        fileobj = cBytesIO(
            b'ID3\x04\x00\x40\x00\x00\x00\x00TIT1\x00\x00\x00\x01a')
        header = ID3Header(fileobj)
        self.assertEquals(header._extdata, b'')

    def test_header_2_4_extended_but_not_but_not_tag(self):
        fileobj = cBytesIO(b'ID3\x04\x00\x40\x00\x00\x00\x00TIT9')
        self.failUnlessRaises(ID3Error, ID3Header, fileobj)

    def test_header_2_3_extended(self):
        fileobj = cBytesIO(
            b'ID3\x03\x00\x40\x00\x00\x00\x00\x00\x00\x00\x06'
            b'\x00\x00\x56\x78\x9a\xbc')
        header = ID3Header(fileobj)
        self.assertEquals(header._extdata, b'\x00\x00\x56\x78\x9a\xbc')

    def test_unsynch(self):
        header = ID3Header()
        header.version = (2, 4, 0)
        header._flags = 0x80
        badsync = b'\x00\xff\x00ab\x00'

        self.assertEquals(
            Frames["TPE2"]._fromData(header, 0, badsync), [u"\xffab"])

        header._flags = 0x00
        self.assertEquals(
            Frames["TPE2"]._fromData(header, 0x02, badsync), [u"\xffab"])

        tag = Frames["TPE2"]._fromData(header, 0, badsync)
        self.assertEquals(tag, [u"\xff", u"ab"])

    def test_load_v23_unsynch(self):
        id3 = ID3(self.unsynch)
        self.assertEquals(id3["TPE1"], ["Nina Simone"])

    def test_insane__ID3__fullread(self):
        fileobj = cBytesIO()
        self.assertRaises(ValueError, _fullread, fileobj, -3)
        self.assertRaises(EOFError, _fullread, fileobj, 3)


class Issue21(TestCase):

    # Files with bad extended header flags failed to read tags.
    # Ensure the extended header is turned off, and the frames are
    # read.
    def setUp(self):
        self.id3 = ID3(join(DATA_DIR, 'issue_21.id3'))

    def test_no_ext(self):
        self.failIf(self.id3.f_extended)

    def test_has_tags(self):
        self.failUnless("TIT2" in self.id3)
        self.failUnless("TALB" in self.id3)

    def test_tit2_value(self):
        self.failUnlessEqual(self.id3["TIT2"].text, [u"Punk To Funk"])


class ID3Tags(TestCase):

    def setUp(self):
        self.silence = join(DATA_DIR, 'silence-44-s.mp3')

    def test_set_wrong_type(self):
        id3 = ID3(self.silence)
        self.assertRaises(TypeError, id3.__setitem__, "FOO", object())

    def test_None(self):
        id3 = ID3(self.silence, known_frames={})
        self.assertEquals(0, len(id3.keys()))
        self.assertEquals(9, len(id3.unknown_frames))

    def test_unknown_reset(self):
        id3 = ID3(self.silence, known_frames={})
        self.assertEquals(9, len(id3.unknown_frames))
        id3.load(self.silence, known_frames={})
        self.assertEquals(9, len(id3.unknown_frames))

    def test_has_docs(self):
        for Kind in (list(Frames.values()) + list(Frames_2_2.values())):
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
        self.assertNotEquals(['piman', 'jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TDRC'])

    def test_23_multiframe_hack(self):
        class ID3hack(ID3):
            "Override 'correct' behavior with desired behavior"
            def loaded_frame(self, tag):
                if tag.HashKey in self:
                    self[tag.HashKey].extend(tag[:])
                else:
                    self[tag.HashKey] = tag

        id3 = ID3hack(self.silence)
        self.assertEquals(8, len(id3.keys()))
        self.assertEquals(0, len(id3.unknown_frames))
        self.assertEquals('Quod Libet Test Data', id3['TALB'])
        self.assertEquals('Silence', str(id3['TCON']))
        self.assertEquals('Silence', str(id3['TIT1']))
        self.assertEquals('Silence', str(id3['TIT2']))
        self.assertEquals(3000, +id3['TLEN'])
        self.assertEquals(['piman', 'jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TDRC'])

    def test_badencoding(self):
        self.assertRaises(
            ID3JunkFrameError, Frames["TPE1"]._fromData, _24, 0, b"\x09ab")
        self.assertRaises(
            ValueError, Frames["TPE1"], encoding=9, text="ab")

    def test_badsync(self):
        frame = Frames["TPE1"]._fromData(_24, 0x02, b"\x00\xff\xfe")
        self.assertEqual(frame.text, [u'\xff\xfe'])

    def test_noencrypt(self):
        self.assertRaises(
            NotImplementedError, Frames["TPE1"]._fromData, _24, 0x04, b"\x00")
        self.assertRaises(
            NotImplementedError, Frames["TPE1"]._fromData, _23, 0x40, b"\x00")

    def test_badcompress(self):
        self.assertRaises(
            ID3JunkFrameError, Frames["TPE1"]._fromData, _24, 0x08,
            b"\x00\x00\x00\x00#")
        self.assertRaises(
            ID3JunkFrameError, Frames["TPE1"]._fromData, _23, 0x80,
            b"\x00\x00\x00\x00#")

    def test_junkframe(self):
        self.assertRaises(
            ID3JunkFrameError, Frames["TPE1"]._fromData, _24, 0, b"")

    def test_bad_sylt(self):
        self.assertRaises(
            ID3JunkFrameError, Frames["SYLT"]._fromData, _24, 0x0,
            b"\x00eng\x01description\x00foobar")
        self.assertRaises(
            ID3JunkFrameError, Frames["SYLT"]._fromData, _24, 0x0,
            b"\x00eng\x01description\x00foobar\x00\xFF\xFF\xFF")

    def test_extradata(self):
        from mutagen.id3 import RVRB, RBUF
        self.assertEqual(RVRB()._readData(b'L1R1BBFFFFPP#xyz'), b'#xyz')
        self.assertEqual(
            RBUF()._readData(b'\x00\x01\x00\x01\x00\x00\x00\x00#xyz'), b'#xyz')


class ID3v1Tags(TestCase):

    def setUp(self):
        self.silence = join(DATA_DIR, 'silence-44-s-v1.mp3')
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
        tag = tag[:125] + b'  ' + tag[-1:]
        self.failIf("TRCK" in ParseID3v1(tag))

    def test_nulls(self):
        from mutagen.id3 import ParseID3v1
        s = u'TAG%(title)30s%(artist)30s%(album)30s%(year)4s%(cmt)29s\x03\x01'
        s = s % dict(artist=u'abcd\00fg', title=u'hijklmn\x00p',
                     album=u'qrst\x00v', cmt=u'wxyz', year=u'1224')
        tags = ParseID3v1(s.encode("ascii"))
        self.assertEquals(b'abcd'.decode('latin1'), tags['TPE1'])
        self.assertEquals(b'hijklmn'.decode('latin1'), tags['TIT2'])
        self.assertEquals(b'qrst'.decode('latin1'), tags['TALB'])

    def test_nonascii(self):
        from mutagen.id3 import ParseID3v1
        s = u'TAG%(title)30s%(artist)30s%(album)30s%(year)4s%(cmt)29s\x03\x01'
        s = s % dict(artist=u'abcd\xe9fg', title=u'hijklmn\xf3p',
                     album=u'qrst\xfcv', cmt=u'wxyz', year=u'1234')
        tags = ParseID3v1(s.encode("latin-1"))
        self.assertEquals(b'abcd\xe9fg'.decode('latin1'), tags['TPE1'])
        self.assertEquals(b'hijklmn\xf3p'.decode('latin1'), tags['TIT2'])
        self.assertEquals(b'qrst\xfcv'.decode('latin1'), tags['TALB'])
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
        empty = b'TAG' + b'\x00' * 124 + b'\xff'
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
        self.failUnless(ParseID3v1(b"") is None)

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
    SILENCE = os.path.join(DATA_DIR, "silence-44-s.mp3")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(self.SILENCE, self.filename)
        self.audio = ID3(self.filename)

    def failIfV1(self):
        fileobj = open(self.filename, "rb")
        fileobj.seek(-128, 2)
        self.failIf(fileobj.read(3) == b"TAG")

    def failUnlessV1(self):
        fileobj = open(self.filename, "rb")
        fileobj.seek(-128, 2)
        self.failUnless(fileobj.read(3) == b"TAG")

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


class TestV22Tags(TestCase):

    def setUp(self):
        filename = os.path.join(DATA_DIR, "id3v22-test.mp3")
        self.tags = ID3(filename)

    def test_tags(self):
        self.failUnless(self.tags["TRCK"].text == ["3/11"])
        self.failUnless(self.tags["TPE1"].text == ["Anais Mitchell"])


def create_read_tag_tests():
    tests = [
        ['TALB', b'\x00a/b', 'a/b', '', dict(encoding=0)],
        ['TBPM', b'\x00120', '120', 120, dict(encoding=0)],
        ['TCMP', b'\x001', '1', 1, dict(encoding=0)],
        ['TCMP', b'\x000', '0', 0, dict(encoding=0)],
        ['TCOM', b'\x00a/b', 'a/b', '', dict(encoding=0)],
        ['TCON', b'\x00(21)Disco', '(21)Disco', '', dict(encoding=0)],
        ['TCOP', b'\x001900 c', '1900 c', '', dict(encoding=0)],
        ['TDAT', b'\x00a/b', 'a/b', '', dict(encoding=0)],
        ['TDEN', b'\x001987', '1987', '', dict(encoding=0, year=[1987])],
        [
            'TDOR', b'\x001987-12', '1987-12', '',
            dict(encoding=0, year=[1987], month=[12])
        ],
        ['TDRC', b'\x001987\x00', '1987', '', dict(encoding=0, year=[1987])],
        [
            'TDRL', b'\x001987\x001988', '1987,1988', '',
            dict(encoding=0, year=[1987, 1988])
        ],
        ['TDTG', b'\x001987', '1987', '', dict(encoding=0, year=[1987])],
        ['TDLY', b'\x001205', '1205', 1205, dict(encoding=0)],
        ['TENC', b'\x00a b/c d', 'a b/c d', '', dict(encoding=0)],
        ['TEXT', b'\x00a b\x00c d', ['a b', 'c d'], '', dict(encoding=0)],
        ['TFLT', b'\x00MPG/3', 'MPG/3', '', dict(encoding=0)],
        ['TIME', b'\x001205', '1205', '', dict(encoding=0)],
        [
            'TIPL', b'\x02\x00a\x00\x00\x00b', [["a", "b"]], '',
            dict(encoding=2)
        ],
        ['TIT1', b'\x00a/b', 'a/b', '', dict(encoding=0)],
        # TIT2 checks misaligned terminator '\x00\x00' across crosses utf16
        # chars
        [
            'TIT2', b'\x01\xff\xfe\x38\x00\x00\x38', u'8\u3800', '',
            dict(encoding=1)
        ],
        ['TIT3', b'\x00a/b', 'a/b', '', dict(encoding=0)],
        ['TKEY', b'\x00A#m', 'A#m', '', dict(encoding=0)],
        ['TLAN', b'\x006241', '6241', '', dict(encoding=0)],
        ['TLEN', b'\x006241', '6241', 6241, dict(encoding=0)],
        [
            'TMCL', b'\x02\x00a\x00\x00\x00b', [["a", "b"]], '',
            dict(encoding=2)
        ],
        ['TMED', b'\x00med', 'med', '', dict(encoding=0)],
        ['TMOO', b'\x00moo', 'moo', '', dict(encoding=0)],
        ['TOAL', b'\x00alb', 'alb', '', dict(encoding=0)],
        ['TOFN', b'\x0012 : bar', '12 : bar', '', dict(encoding=0)],
        ['TOLY', b'\x00lyr', 'lyr', '', dict(encoding=0)],
        ['TOPE', b'\x00own/lic', 'own/lic', '', dict(encoding=0)],
        ['TORY', b'\x001923', '1923', 1923, dict(encoding=0)],
        ['TOWN', b'\x00own/lic', 'own/lic', '', dict(encoding=0)],
        ['TPE1', b'\x00ab', ['ab'], '', dict(encoding=0)],
        [
            'TPE2', b'\x00ab\x00cd\x00ef', ['ab', 'cd', 'ef'], '',
            dict(encoding=0)
        ],
        ['TPE3', b'\x00ab\x00cd', ['ab', 'cd'], '', dict(encoding=0)],
        ['TPE4', b'\x00ab\x00', ['ab'], '', dict(encoding=0)],
        ['TPOS', b'\x0008/32', '08/32', 8, dict(encoding=0)],
        ['TPRO', b'\x00pro', 'pro', '', dict(encoding=0)],
        ['TPUB', b'\x00pub', 'pub', '', dict(encoding=0)],
        ['TRCK', b'\x004/9', '4/9', 4, dict(encoding=0)],
        ['TRDA', b'\x00Sun Jun 12', 'Sun Jun 12', '', dict(encoding=0)],
        ['TRSN', b'\x00ab/cd', 'ab/cd', '', dict(encoding=0)],
        ['TRSO', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSIZ', b'\x0012345', '12345', 12345, dict(encoding=0)],
        ['TSOA', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSOP', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSOT', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSO2', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSOC', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TSRC', b'\x0012345', '12345', '', dict(encoding=0)],
        ['TSSE', b'\x0012345', '12345', '', dict(encoding=0)],
        ['TSST', b'\x0012345', '12345', '', dict(encoding=0)],
        ['TYER', b'\x002004', '2004', 2004, dict(encoding=0)],
        [
            'TXXX', b'\x00usr\x00a/b\x00c', ['a/b', 'c'], '',
            dict(encoding=0, desc='usr')
        ],
        ['WCOM', b'http://foo', 'http://foo', '', {}],
        ['WCOP', b'http://bar', 'http://bar', '', {}],
        ['WOAF', b'http://baz', 'http://baz', '', {}],
        ['WOAR', b'http://bar', 'http://bar', '', {}],
        ['WOAS', b'http://bar', 'http://bar', '', {}],
        ['WORS', b'http://bar', 'http://bar', '', {}],
        ['WPAY', b'http://bar', 'http://bar', '', {}],
        ['WPUB', b'http://bar', 'http://bar', '', {}],
        ['WXXX', b'\x00usr\x00http', 'http', '', dict(encoding=0, desc='usr')],
        [
            'IPLS', b'\x00a\x00A\x00b\x00B\x00', [['a', 'A'], ['b', 'B']], '',
            dict(encoding=0)
        ],
        ['MCDI', b'\x01\x02\x03\x04', b'\x01\x02\x03\x04', '', {}],
        [
            'ETCO', b'\x01\x12\x00\x00\x7f\xff', [(18, 32767)], '',
            dict(format=1)
        ],
        [
            'COMM', b'\x00ENUT\x00Com', 'Com', '',
            dict(desc='T', lang='ENU', encoding=0)
        ],
        [
            'APIC', b'\x00-->\x00\x03cover\x00cover.jpg', b'cover.jpg', '',
            dict(mime='-->', type=3, desc='cover', encoding=0)
        ],
        ['USER', b'\x00ENUCom', 'Com', '', dict(lang='ENU', encoding=0)],
        [
            'RVA2', b'testdata\x00\x01\xfb\x8c\x10\x12\x23',
            'Master volume: -2.2266 dB/0.1417', '',
            dict(desc='testdata', channel=1, gain=-2.22656, peak=0.14169)
        ],
        [
            'RVA2', b'testdata\x00\x01\xfb\x8c\x24\x01\x22\x30\x00\x00',
            'Master volume: -2.2266 dB/0.1417', '',
            dict(desc='testdata', channel=1, gain=-2.22656, peak=0.14169)
        ],
        [
            'RVA2', b'testdata2\x00\x01\x04\x01\x00',
            'Master volume: +2.0020 dB/0.0000', '',
            dict(desc='testdata2', channel=1, gain=2.001953125, peak=0)
        ],
        ['PCNT', b'\x00\x00\x00\x11', 17, 17, dict(count=17)],
        [
            'POPM', b'foo@bar.org\x00\xde\x00\x00\x00\x11', 222, 222,
            dict(email="foo@bar.org", rating=222, count=17)
        ],
        [
            'POPM', b'foo@bar.org\x00\xde\x00', 222, 222,
            dict(email="foo@bar.org", rating=222, count=0)
        ],
        # Issue #33 - POPM may have no playcount at all.
        [
            'POPM', b'foo@bar.org\x00\xde', 222, 222,
            dict(email="foo@bar.org", rating=222)
        ],
        ['UFID', b'own\x00data', b'data', '', dict(data=b'data', owner='own')],
        ['UFID', b'own\x00\xdd', b'\xdd', '', dict(data=b'\xdd', owner='own')],
        [
            'GEOB', b'\x00mime\x00name\x00desc\x00data', b'data', '',
            dict(encoding=0, mime='mime', filename='name', desc='desc')
        ],
        [
            'USLT', b'\x00engsome lyrics\x00woo\nfun', 'woo\nfun', '',
            dict(encoding=0, lang='eng', desc='some lyrics', text='woo\nfun')
        ],
        [
            'SYLT', (b'\x00eng\x02\x01some lyrics\x00foo\x00\x00\x00\x00\x01'
                     b'bar\x00\x00\x00\x00\x10'), "foobar", '',
            dict(encoding=0, lang='eng', type=1, format=2, desc='some lyrics')
        ],
        ['POSS', b'\x01\x0f', 15, 15, dict(format=1, position=15)],
        [
            'OWNE', b'\x00USD10.01\x0020041010CDBaby', 'CDBaby', 'CDBaby',
            dict(encoding=0, price="USD10.01", date='20041010',
                 seller='CDBaby')
        ],
        [
            'PRIV', b'a@b.org\x00random data', b'random data', 'random data',
            dict(owner='a@b.org', data=b'random data')
        ],
        [
            'PRIV', b'a@b.org\x00\xdd', b'\xdd', '\xdd',
            dict(owner='a@b.org', data=b'\xdd')
        ],
        ['SIGN', b'\x92huh?', b'huh?', 'huh?', dict(group=0x92, sig=b'huh?')],
        [
            'ENCR', b'a@b.org\x00\x92Data!', b'Data!', 'Data!',
            dict(owner='a@b.org', method=0x92, data=b'Data!')
        ],
        [
            'SEEK', b'\x00\x12\x00\x56',
            0x12 * 256 * 256 + 0x56, 0x12 * 256 * 256 + 0x56,
            dict(offset=0x12 * 256 * 256 + 0x56)
        ],
        [
            'SYTC', b"\x01\x10obar", b'\x10obar', '',
            dict(format=1, data=b'\x10obar')
        ],
        [
            'RBUF', b'\x00\x12\x00', 0x12 * 256, 0x12 * 256,
            dict(size=0x12 * 256)
        ],
        [
            'RBUF', b'\x00\x12\x00\x01', 0x12 * 256, 0x12 * 256,
            dict(size=0x12 * 256, info=1)
        ],
        [
            'RBUF', b'\x00\x12\x00\x01\x00\x00\x00\x23',
            0x12 * 256, 0x12 * 256,
            dict(size=0x12 * 256, info=1, offset=0x23)
        ],
        [
            'RVRB', b'\x12\x12\x23\x23\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11',
            (0x12 * 256 + 0x12, 0x23 * 256 + 0x23), '',
            dict(left=0x12 * 256 + 0x12, right=0x23 * 256 + 0x23)
        ],
        [
            'AENC', b'a@b.org\x00\x00\x12\x00\x23', 'a@b.org', 'a@b.org',
            dict(owner='a@b.org', preview_start=0x12, preview_length=0x23)
        ],
        [
            'AENC', b'a@b.org\x00\x00\x12\x00\x23!', 'a@b.org', 'a@b.org',
            dict(owner='a@b.org', preview_start=0x12,
                 preview_length=0x23, data=b'!')
        ],
        [
            'GRID', b'a@b.org\x00\x99', 'a@b.org', 0x99,
            dict(owner='a@b.org', group=0x99)
        ],
        [
            'GRID', b'a@b.org\x00\x99data', 'a@b.org', 0x99,
            dict(owner='a@b.org', group=0x99, data=b'data')
        ],
        [
            'COMR',
            (b'\x00USD10.00\x0020051010ql@sc.net\x00\x09Joe\x00A song\x00'
             b'x-image/fake\x00some data'),
            COMR(encoding=0, price="USD10.00", valid_until="20051010",
                 contact="ql@sc.net", format=9, seller="Joe", desc="A song",
                 mime='x-image/fake', logo=b'some data'), '',
            dict(encoding=0, price="USD10.00", valid_until="20051010",
                 contact="ql@sc.net", format=9, seller="Joe", desc="A song",
                 mime='x-image/fake', logo=b'some data')
        ],
        [
            'COMR',
            b'\x00USD10.00\x0020051010ql@sc.net\x00\x09Joe\x00A song\x00',
            COMR(encoding=0, price="USD10.00", valid_until="20051010",
                 contact="ql@sc.net", format=9, seller="Joe", desc="A song"),
            '',
            dict(encoding=0, price="USD10.00", valid_until="20051010",
                 contact="ql@sc.net", format=9, seller="Joe", desc="A song")
        ],
        [
            'MLLT', b'\x00\x01\x00\x00\x02\x00\x00\x03\x04\x08foobar',
            b'foobar', '',
            dict(frames=1, bytes=2, milliseconds=3, bits_for_bytes=4,
                 bits_for_milliseconds=8, data=b'foobar')
        ],
        [
            'EQU2', b'\x00Foobar\x00\x01\x01\x04\x00', [(128.5, 2.0)], '',
            dict(method=0, desc="Foobar")
        ],
        [
            'ASPI',
            b'\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x08\x01\x02\x03',
            [1, 2, 3], '', dict(S=0, L=16, N=3, b=8)
        ],
        [
            'ASPI', b'\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x10'
            b'\x00\x01\x00\x02\x00\x03', [1, 2, 3], '',
            dict(S=0, L=16, N=3, b=16)
        ],
        [
            'LINK', b'TIT1http://www.example.org/TIT1.txt\x00',
            ("TIT1", 'http://www.example.org/TIT1.txt'), '',
            dict(frameid='TIT1', url='http://www.example.org/TIT1.txt')
        ],
        [
            'LINK', b'COMMhttp://www.example.org/COMM.txt\x00engfoo',
            ("COMM", 'http://www.example.org/COMM.txt', b'engfoo'), '',
            dict(frameid='COMM', url='http://www.example.org/COMM.txt',
                 data=b'engfoo')
        ],
        # iTunes podcast frames
        ['TGID', b'\x00i', u'i', '', dict(encoding=0)],
        ['TDES', b'\x00ii', u'ii', '', dict(encoding=0)],
        ['WFED', b'http://zzz', 'http://zzz', '', {}],

        # 2.2 tags
        ['UFI', b'own\x00data', b'data', '', dict(data=b'data', owner='own')],
        [
            'SLT', (b'\x00eng\x02\x01some lyrics\x00foo\x00\x00\x00\x00\x01bar'
                    b'\x00\x00\x00\x00\x10'),
            "foobar", '',
            dict(encoding=0, lang='eng', type=1, format=2, desc='some lyrics')
        ],
        ['TT1', b'\x00ab\x00', 'ab', '', dict(encoding=0)],
        ['TT2', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TT3', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TP1', b'\x00ab\x00', 'ab', '', dict(encoding=0)],
        ['TP2', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TP3', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TP4', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TCM', b'\x00ab/cd', 'ab/cd', '', dict(encoding=0)],
        ['TXT', b'\x00lyr', 'lyr', '', dict(encoding=0)],
        ['TLA', b'\x00ENU', 'ENU', '', dict(encoding=0)],
        ['TCO', b'\x00gen', 'gen', '', dict(encoding=0)],
        ['TAL', b'\x00alb', 'alb', '', dict(encoding=0)],
        ['TPA', b'\x001/9', '1/9', 1, dict(encoding=0)],
        ['TRK', b'\x002/8', '2/8', 2, dict(encoding=0)],
        ['TRC', b'\x00isrc', 'isrc', '', dict(encoding=0)],
        ['TYE', b'\x001900', '1900', 1900, dict(encoding=0)],
        ['TDA', b'\x002512', '2512', '', dict(encoding=0)],
        ['TIM', b'\x001225', '1225', '', dict(encoding=0)],
        ['TRD', b'\x00Jul 17', 'Jul 17', '', dict(encoding=0)],
        ['TMT', b'\x00DIG/A', 'DIG/A', '', dict(encoding=0)],
        ['TFT', b'\x00MPG/3', 'MPG/3', '', dict(encoding=0)],
        ['TBP', b'\x00133', '133', 133, dict(encoding=0)],
        ['TCP', b'\x001', '1', 1, dict(encoding=0)],
        ['TCP', b'\x000', '0', 0, dict(encoding=0)],
        ['TCR', b'\x00Me', 'Me', '', dict(encoding=0)],
        ['TPB', b'\x00Him', 'Him', '', dict(encoding=0)],
        ['TEN', b'\x00Lamer', 'Lamer', '', dict(encoding=0)],
        ['TSS', b'\x00ab', 'ab', '', dict(encoding=0)],
        ['TOF', b'\x00ab:cd', 'ab:cd', '', dict(encoding=0)],
        ['TLE', b'\x0012', '12', 12, dict(encoding=0)],
        ['TSI', b'\x0012', '12', 12, dict(encoding=0)],
        ['TDY', b'\x0012', '12', 12, dict(encoding=0)],
        ['TKE', b'\x00A#m', 'A#m', '', dict(encoding=0)],
        ['TOT', b'\x00org', 'org', '', dict(encoding=0)],
        ['TOA', b'\x00org', 'org', '', dict(encoding=0)],
        ['TOL', b'\x00org', 'org', '', dict(encoding=0)],
        ['TOR', b'\x001877', '1877', 1877, dict(encoding=0)],
        ['TXX', b'\x00desc\x00val', 'val', '', dict(encoding=0, desc='desc')],

        ['WAF', b'http://zzz', 'http://zzz', '', {}],
        ['WAR', b'http://zzz', 'http://zzz', '', {}],
        ['WAS', b'http://zzz', 'http://zzz', '', {}],
        ['WCM', b'http://zzz', 'http://zzz', '', {}],
        ['WCP', b'http://zzz', 'http://zzz', '', {}],
        ['WPB', b'http://zzz', 'http://zzz', '', {}],
        [
            'WXX', b'\x00desc\x00http', 'http', '',
            dict(encoding=0, desc='desc')
        ],
        [
            'IPL', b'\x00a\x00A\x00b\x00B\x00', [['a', 'A'], ['b', 'B']], '',
            dict(encoding=0)
        ],
        ['MCI', b'\x01\x02\x03\x04', b'\x01\x02\x03\x04', '', {}],
        [
            'ETC', b'\x01\x12\x00\x00\x7f\xff', [(18, 32767)], '',
            dict(format=1)
        ],
        [
            'COM', b'\x00ENUT\x00Com', 'Com', '',
            dict(desc='T', lang='ENU', encoding=0)
        ],
        [
            'PIC', b'\x00-->\x03cover\x00cover.jpg', b'cover.jpg', '',
            dict(mime='-->', type=3, desc='cover', encoding=0)
        ],
        [
            'POP', b'foo@bar.org\x00\xde\x00\x00\x00\x11', 222, 222,
            dict(email="foo@bar.org", rating=222, count=17)
        ],
        ['CNT', b'\x00\x00\x00\x11', 17, 17, dict(count=17)],
        [
            'GEO', b'\x00mime\x00name\x00desc\x00data', b'data', '',
            dict(encoding=0, mime='mime', filename='name', desc='desc')
        ],
        [
            'ULT', b'\x00engsome lyrics\x00woo\nfun', 'woo\nfun', '',
            dict(encoding=0, lang='eng', desc='some lyrics', text='woo\nfun')],
        [
            'BUF', b'\x00\x12\x00', 0x12 * 256, 0x12 * 256,
            dict(size=0x12 * 256)
        ],
        [
            'CRA', b'a@b.org\x00\x00\x12\x00\x23', 'a@b.org', 'a@b.org',
            dict(owner='a@b.org', preview_start=0x12, preview_length=0x23)
        ],
        [
            'CRA', b'a@b.org\x00\x00\x12\x00\x23!', 'a@b.org', 'a@b.org',
            dict(owner='a@b.org', preview_start=0x12,
                 preview_length=0x23, data=b'!')
        ],
        [
            'REV', b'\x12\x12\x23\x23\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11',
            (0x12 * 256 + 0x12, 0x23 * 256 + 0x23), '',
            dict(left=0x12 * 256 + 0x12, right=0x23 * 256 + 0x23)
        ],
        [
            'STC', b"\x01\x10obar", b'\x10obar', '',
            dict(format=1, data=b'\x10obar')
        ],
        [
            'MLL', b'\x00\x01\x00\x00\x02\x00\x00\x03\x04\x08foobar',
            b'foobar', '',
            dict(frames=1, bytes=2, milliseconds=3, bits_for_bytes=4,
                 bits_for_milliseconds=8, data=b'foobar')
        ],
        [
            'LNK', b'TT1http://www.example.org/TIT1.txt\x00',
            ("TT1", 'http://www.example.org/TIT1.txt'), '',
            dict(frameid='TT1', url='http://www.example.org/TIT1.txt')
        ],
        [
            'CRM', b'foo@example.org\x00test\x00woo', b'woo', '',
            dict(owner='foo@example.org', desc='test', data=b'woo')
        ],
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
            tag = TAG._fromData(_23, 0, data)
            self.failUnless(tag.HashKey)
            self.failUnless(tag.pprint())
            self.assertEquals(value, tag)
            if 'encoding' not in info:
                self.assertRaises(AttributeError, getattr, tag, 'encoding')
            for attr, value in iteritems(info):
                t = tag
                if not isinstance(value, list):
                    value = [value]
                    t = [t]
                for value, t in izip(value, iter(t)):
                    if isinstance(value, float):
                        self.failUnlessAlmostEqual(value, getattr(t, attr), 5)
                    else:
                        self.assertEquals(value, getattr(t, attr))

                    if isinstance(intval, integer_types):
                        self.assertEquals(intval, pos(t))
                    else:
                        self.assertRaises(TypeError, pos, t)

        load_tests['test_%s_%d' % (tag, i)] = test_tag

        def test_tag_repr(self, tag=tag, data=data):
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG._fromData(_23, 0, data)
            self.assertTrue(isinstance(tag.__str__(), str))
            if PY2:
                if hasattr(tag, "__unicode__"):
                    self.assertTrue(isinstance(tag.__unicode__(), unicode))
            else:
                if hasattr(tag, "__bytes__"):
                    self.assertTrue(isinstance(tag.__bytes__(), bytes))

        repr_tests['test_repr_%s_%d' % (tag, i)] = test_tag_repr

        def test_tag_write(self, tag=tag, data=data):
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG._fromData(_24, 0, data)
            towrite = tag._writeData()
            tag2 = TAG._fromData(_24, 0, towrite)
            for spec in TAG._framespec:
                attr = spec.name
                self.assertEquals(getattr(tag, attr), getattr(tag2, attr))
        write_tests['test_write_%s_%d' % (tag, i)] = test_tag_write

    testcase = type('TestReadTags', (TestCase,), load_tests)
    assert testcase.__name__ not in globals()
    globals()[testcase.__name__] = testcase
    testcase = type('TestReadReprTags', (TestCase,), repr_tests)
    assert testcase.__name__ not in globals()
    globals()[testcase.__name__] = testcase
    testcase = type('TestReadWriteTags', (TestCase,), write_tests)
    assert testcase.__name__ not in globals()
    globals()[testcase.__name__] = testcase

    from mutagen.id3 import Frames, Frames_2_2
    check = dict.fromkeys(list(Frames.keys()) + list(Frames_2_2.keys()))
    tested_tags = dict.fromkeys([row[0] for row in tests])
    for tag in check:
        def check(self, tag=tag):
            self.assert_(tag in tested_tags)
        tested_tags['test_' + tag + '_tested'] = check
    testcase = type('TestTestedTags', (TestCase,), tested_tags)
    assert testcase.__name__ not in globals()
    globals()[testcase.__name__] = testcase

create_read_tag_tests()


class UpdateTo24(TestCase):

    def test_pic(self):
        from mutagen.id3 import PIC
        id3 = ID3()
        id3.version = (2, 2)
        id3.add(PIC(encoding=0, mime="PNG", desc="cover", type=3, data=b""))
        id3.update_to_v24()
        self.failUnlessEqual(id3["APIC:cover"].mime, "image/png")

    def test_lnk(self):
        from mutagen.id3 import LNK
        id3 = ID3()
        id3.version = (2, 2)
        id3.add(LNK(frameid="PIC", url="http://foo.bar"))
        id3.update_to_v24()
        self.assertTrue(id3.getall("LINK"))

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

    def test_dropped(self):
        from mutagen.id3 import TIME
        id3 = ID3()
        id3.version = (2, 3)
        id3.add(TIME(encoding=0, text=["1155"]))
        id3.update_to_v24()
        self.assertFalse(id3.getall("TIME"))


class Issue97_UpgradeUnknown23(TestCase):
    SILENCE = os.path.join(DATA_DIR, "97-unknown-23-update.mp3")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(self.SILENCE, self.filename)

    def test_unknown(self):
        from mutagen.id3 import TPE1
        orig = ID3(self.filename)
        self.failUnlessEqual(orig.version, (2, 3, 0))

        # load a 2.3 file and pretend we don't support TIT2
        unknown = ID3(self.filename, known_frames={"TPE1": TPE1},
                      translate=False)

        # TIT2 ends up in unknown_frames
        self.failUnlessEqual(unknown.unknown_frames[0][:4], b"TIT2")

        # frame should be different now
        orig_unknown = unknown.unknown_frames[0]
        unknown.update_to_v24()
        self.failIfEqual(unknown.unknown_frames[0], orig_unknown)

        # save as 2.4
        unknown.save()

        # load again with support for TIT2, all should be there again
        new = ID3(self.filename)
        self.failUnlessEqual(new.version, (2, 4, 0))
        self.failUnlessEqual(new["TIT2"].text, orig["TIT2"].text)
        self.failUnlessEqual(new["TPE1"].text, orig["TPE1"].text)

    def test_double_update(self):
        from mutagen.id3 import TPE1
        unknown = ID3(self.filename, known_frames={"TPE1": TPE1})
        # Make sure the data doesn't get updated again
        unknown.update_to_v24()
        unknown.unknown_frames = [b"foobar"]
        unknown.update_to_v24()
        self.failUnless(unknown.unknown_frames)

    def test_unknown_invalid(self):
        f = ID3(self.filename, translate=False)
        f.unknown_frames = [b"foobar", b"\xff" * 50]
        # throw away invalid frames
        f.update_to_v24()
        self.failIf(f.unknown_frames)

    def tearDown(self):
        os.unlink(self.filename)


class BrokenDiscarded(TestCase):

    def test_empty(self):
        from mutagen.id3 import TPE1, ID3JunkFrameError
        self.assertRaises(ID3JunkFrameError, TPE1._fromData, _24, 0x00, b'')

    def test_wacky_truncated_RVA2(self):
        from mutagen.id3 import RVA2, ID3JunkFrameError
        data = b'\x01{\xf0\x10\xff\xff\x00'
        self.assertRaises(ID3JunkFrameError, RVA2._fromData, _24, 0x00, data)

    def test_bad_number_of_bits_RVA2(self):
        from mutagen.id3 import RVA2, ID3JunkFrameError
        data = b'\x00\x00\x01\xe6\xfc\x10{\xd7'
        self.assertRaises(ID3JunkFrameError, RVA2._fromData, _24, 0x00, data)

    def test_drops_truncated_frames(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        id3._header = ID3Header()
        id3._header.version = (2, 4, 0)
        tail = b'\x00\x00\x00\x03\x00\x00' b'\x01\x02\x03'
        for head in b'RVA2 TXXX APIC'.split():
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_drops_nonalphanum_frames(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        tail = b'\x00\x00\x00\x03\x00\x00' b'\x01\x02\x03'
        for head in [b'\x06\xaf\xfe\x20', b'ABC\x00', b'A   ']:
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_bad_unicodedecode(self):
        from mutagen.id3 import COMM, ID3JunkFrameError
        # 7 bytes of "UTF16" data.
        data = b'\x01\x00\x00\x00\xff\xfe\x00\xff\xfeh\x00'
        self.assertRaises(ID3JunkFrameError, COMM._fromData, _24, 0x00, data)


class BrokenButParsed(TestCase):

    def test_zerolength_framedata(self):
        from mutagen.id3 import Frames
        id3 = ID3()
        tail = b'\x00' * 6
        for head in b'WOAR TENC TCOP TOPE WXXX'.split():
            data = head + tail
            self.assertEquals(
                0, len(list(id3._ID3__read_frames(data, Frames))))

    def test_lengthone_utf16(self):
        from mutagen.id3 import TPE1
        tpe1 = TPE1._fromData(_24, 0, b'\x01\x00')
        self.assertEquals(u'', tpe1)
        tpe1 = TPE1._fromData(_24, 0, b'\x01\x00\x00\x00\x00')
        self.assertEquals([u'', u''], tpe1)

    def test_utf16_wrongnullterm(self):
        # issue 169
        from mutagen.id3 import TPE1
        tpe1 = TPE1._fromData(
            _24, 0, b'\x01\xff\xfeH\x00e\x00l\x00l\x00o\x00\x00')
        self.assertEquals(tpe1, [u'Hello'])

    def test_fake_zlib(self):
        from mutagen.id3 import TPE1, Frame
        header = ID3Header()
        header.version = (2, 4, 0)
        self.assertRaises(ID3JunkFrameError, TPE1._fromData, header,
                          Frame.FLAG24_COMPRESS, b'\x03abcdefg')

    def test_zlib_bpi(self):
        from mutagen.id3 import TPE1
        id3 = ID3()
        tpe1 = TPE1(encoding=0, text="a" * (0xFFFF - 2))
        data = id3._ID3__save_frame(tpe1)
        datalen_size = data[4 + 4 + 2:4 + 4 + 2 + 4]
        self.failIf(
            max(datalen_size) >= b'\x80'[0], "data is not syncsafe: %r" % data)

    def test_ql_0_12_missing_uncompressed_size(self):
        from mutagen.id3 import TPE1
        tag = TPE1._fromData(
            _24, 0x08,
            b'x\x9cc\xfc\xff\xaf\x84!\x83!\x93'
            b'\xa1\x98A\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#'
        )
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

    def test_zlib_latin1_missing_datalen(self):
        from mutagen.id3 import TPE1
        tag = TPE1._fromData(
            _24, 0x8,
            b'\x00\x00\x00\x0f'
            b'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%'
        )
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])

    def test_detect_23_ints_in_24_frames(self):
        from mutagen.id3 import Frames
        head = b'TIT1\x00\x00\x01\x00\x00\x00\x00'
        tail = b'TPE1\x00\x00\x00\x05\x00\x00\x00Yay!'

        id3 = ID3()
        id3._header = ID3Header()
        id3._header.version = (2, 4, 0)

        tagsgood = list(
            id3._ID3__read_frames(head + b'a' * 127 + tail, Frames))
        tagsbad = list(id3._ID3__read_frames(head + b'a' * 255 + tail, Frames))
        self.assertEquals(2, len(tagsgood))
        self.assertEquals(2, len(tagsbad))
        self.assertEquals('a' * 127, tagsgood[0])
        self.assertEquals('a' * 255, tagsbad[0])
        self.assertEquals('Yay!', tagsgood[1])
        self.assertEquals('Yay!', tagsbad[1])

        tagsgood = list(id3._ID3__read_frames(head + b'a' * 127, Frames))
        tagsbad = list(id3._ID3__read_frames(head + b'a' * 255, Frames))
        self.assertEquals(1, len(tagsgood))
        self.assertEquals(1, len(tagsbad))
        self.assertEquals('a' * 127, tagsgood[0])
        self.assertEquals('a' * 255, tagsbad[0])


class OddWrites(TestCase):
    silence = join(DATA_DIR, 'silence-44-s.mp3')
    newsilence = join(DATA_DIR, 'silence-written.mp3')

    def setUp(self):
        shutil.copy(self.silence, self.newsilence)

    def test_toemptyfile(self):
        os.unlink(self.newsilence)
        open(self.newsilence, "wb").close()
        ID3(self.silence).save(self.newsilence)

    def test_tononfile(self):
        os.unlink(self.newsilence)
        ID3(self.silence).save(self.newsilence)

    def test_1bfile(self):
        os.unlink(self.newsilence)
        f = open(self.newsilence, "wb")
        f.write(b"!")
        f.close()
        ID3(self.silence).save(self.newsilence)
        self.assert_(os.path.getsize(self.newsilence) > 1)
        self.assertEquals(open(self.newsilence, "rb").read()[-1], b"!"[0])

    def tearDown(self):
        try:
            os.unlink(self.newsilence)
        except OSError:
            pass


class WriteRoundtrip(TestCase):
    silence = join(DATA_DIR, 'silence-44-s.mp3')
    newsilence = join(DATA_DIR, 'silence-written.mp3')

    def setUp(self):
        shutil.copy(self.silence, self.newsilence)

    def test_same(self):
        ID3(self.newsilence).save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TALB"], "Quod Libet Test Data")
        self.assertEquals(id3["TCON"], "Silence")
        self.assertEquals(id3["TIT2"], "Silence")
        self.assertEquals(id3["TPE1"], ["jzig"])

    def test_same_v23(self):
        id3 = ID3(self.newsilence, v2_version=3)
        id3.save(v2_version=3)
        id3 = ID3(self.newsilence)
        self.assertEqual(id3.version, (2, 3, 0))
        self.assertEquals(id3["TALB"], "Quod Libet Test Data")
        self.assertEquals(id3["TCON"], "Silence")
        self.assertEquals(id3["TIT2"], "Silence")
        self.assertEquals(id3["TPE1"], "jzig")

    def test_addframe(self):
        from mutagen.id3 import TIT3
        f = ID3(self.newsilence)
        self.assert_("TIT3" not in f)
        f["TIT3"] = TIT3(encoding=0, text="A subtitle!")
        f.save()
        id3 = ID3(self.newsilence)
        self.assertEquals(id3["TIT3"], "A subtitle!")

    def test_changeframe(self):
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

    def test_nofile_silencetag(self):
        id3 = ID3(self.newsilence)
        os.unlink(self.newsilence)
        id3.save(self.newsilence)
        self.assertEquals(b'ID3', open(self.newsilence, 'rb').read(3))
        self.test_same()

    def test_emptyfile_silencetag(self):
        id3 = ID3(self.newsilence)
        open(self.newsilence, 'wb').truncate()
        id3.save(self.newsilence)
        self.assertEquals(b'ID3', open(self.newsilence, 'rb').read(3))
        self.test_same()

    def test_empty_plustag_minustag_empty(self):
        id3 = ID3(self.newsilence)
        open(self.newsilence, 'wb').truncate()
        id3.save()
        id3.delete()
        self.failIf(id3)
        self.assertEquals(open(self.newsilence, 'rb').read(10), b'')

    def test_delete_invalid_zero(self):
        f = open(self.newsilence, 'wb')
        f.write(b'ID3\x04\x00\x00\x00\x00\x00\x00abc')
        f.close()
        ID3(self.newsilence).delete()
        self.assertEquals(open(self.newsilence, 'rb').read(10), b'abc')

    def test_frame_order(self):
        from mutagen.id3 import TIT2, APIC, TALB, COMM
        f = ID3(self.newsilence)
        f["TIT2"] = TIT2(encoding=0, text="A title!")
        f["APIC"] = APIC(encoding=0, mime="b", type=3, desc='', data=b"a")
        f["TALB"] = TALB(encoding=0, text="c")
        f["COMM"] = COMM(encoding=0, desc="x", text="y")
        f.save()
        data = open(self.newsilence, 'rb').read()
        self.assert_(data.find(b"TIT2") < data.find(b"APIC"))
        self.assert_(data.find(b"TIT2") < data.find(b"COMM"))
        self.assert_(data.find(b"TALB") < data.find(b"APIC"))
        self.assert_(data.find(b"TALB") < data.find(b"COMM"))
        self.assert_(data.find(b"TIT2") < data.find(b"TALB"))

    def tearDown(self):
        try:
            os.unlink(self.newsilence)
        except EnvironmentError:
            pass


class WriteForEyeD3(TestCase):
    silence = join(DATA_DIR, 'silence-44-s.mp3')
    newsilence = join(DATA_DIR, 'silence-written.mp3')

    def setUp(self):
        shutil.copy(self.silence, self.newsilence)
        # remove ID3v1 tag
        f = open(self.newsilence, "rb+")
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
        f = ID3(self.newsilence)
        self.assertEquals(f["TIT2"], "Silence")
        f["TIT2"].text = [u"The sound of silence."]
        f.save()
        id3 = eyeD3.tag.Tag(eyeD3.ID3_V2_4)
        id3.link(self.newsilence)
        self.assertEquals(id3.frames["TIT2"][0].text, "The sound of silence.")

    def tearDown(self):
        os.unlink(self.newsilence)


class BadTYER(TestCase):

    filename = join(DATA_DIR, 'bad-TYER-frame.mp3')

    def setUp(self):
        self.audio = ID3(self.filename)

    def test_no_year(self):
        self.failIf("TYER" in self.audio)

    def test_has_title(self):
        self.failUnless("TIT2" in self.audio)

    def tearDown(self):
        del(self.audio)


class BadPOPM(TestCase):

    filename = join(DATA_DIR, 'bad-POPM-frame.mp3')
    newfilename = join(DATA_DIR, 'bad-POPM-frame-written.mp3')

    def setUp(self):
        shutil.copy(self.filename, self.newfilename)

    def tearDown(self):
        try:
            os.unlink(self.newfilename)
        except EnvironmentError:
            pass

    def test_read_popm_long_counter(self):
        f = ID3(self.newfilename)
        self.failUnless("POPM:Windows Media Player 9 Series" in f)
        popm = f["POPM:Windows Media Player 9 Series"]
        self.assertEquals(popm.rating, 255)
        self.assertEquals(popm.count, 2709193061)

    def test_write_popm_long_counter(self):
        from mutagen.id3 import POPM
        f = ID3(self.newfilename)
        f.add(POPM(email="foo@example.com", rating=125, count=2 ** 32 + 1))
        f.save()
        f = ID3(self.newfilename)
        self.failUnless("POPM:foo@example.com" in f)
        self.failUnless("POPM:Windows Media Player 9 Series" in f)
        popm = f["POPM:foo@example.com"]
        self.assertEquals(popm.rating, 125)
        self.assertEquals(popm.count, 2 ** 32 + 1)


class Issue69_BadV1Year(TestCase):

    def test_missing_year(self):
        from mutagen.id3 import ParseID3v1

        tag = ParseID3v1(
            b'ABCTAGhello world\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\xff'
        )
        self.failUnlessEqual(tag["TIT2"], "hello world")

    def test_short_year(self):
        from mutagen.id3 import ParseID3v1, _find_id3v1

        data = (
            b'XTAGhello world\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x001\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\xff'
        )
        tag = ParseID3v1(data)
        self.failUnlessEqual(tag["TIT2"], "hello world")
        self.failUnlessEqual(tag["TDRC"], "0001")

        frames, offset = _find_id3v1(cBytesIO(data))
        self.assertEqual(offset, -125)
        self.assertEqual(frames, tag)

    def test_none(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1
        s = MakeID3v1(dict())
        self.failUnlessEqual(len(s), 128)
        tag = ParseID3v1(s)
        self.failIf("TDRC" in tag)

    def test_empty(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1
        s = MakeID3v1(dict(TDRC=""))
        self.failUnlessEqual(len(s), 128)
        tag = ParseID3v1(s)
        self.failIf("TDRC" in tag)

    def test_short(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1
        s = MakeID3v1(dict(TDRC="1"))
        self.failUnlessEqual(len(s), 128)
        tag = ParseID3v1(s)
        self.failUnlessEqual(tag["TDRC"], "0001")

    def test_long(self):
        from mutagen.id3 import ParseID3v1, MakeID3v1
        s = MakeID3v1(dict(TDRC="123456789"))
        self.failUnlessEqual(len(s), 128)
        tag = ParseID3v1(s)
        self.failUnlessEqual(tag["TDRC"], "1234")


class UpdateTo23(TestCase):

    def test_tdrc(self):
        tags = ID3()
        tags.add(id3.TDRC(encoding=1, text="2003-04-05 12:03"))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TYER"].text, ["2003"])
        self.failUnlessEqual(tags["TDAT"].text, ["0504"])
        self.failUnlessEqual(tags["TIME"].text, ["1203"])

    def test_tdor(self):
        tags = ID3()
        tags.add(id3.TDOR(encoding=1, text="2003-04-05 12:03"))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TORY"].text, ["2003"])

    def test_genre_from_v24_1(self):
        tags = ID3()
        tags.add(id3.TCON(encoding=1, text=["4", "Rock"]))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TCON"].text, ["Disco", "Rock"])

    def test_genre_from_v24_2(self):
        tags = ID3()
        tags.add(id3.TCON(encoding=1, text=["RX", "3", "CR"]))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TCON"].text, ["Remix", "Dance", "Cover"])

    def test_genre_from_v23_1(self):
        tags = ID3()
        tags.add(id3.TCON(encoding=1, text=["(4)Rock"]))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TCON"].text, ["Disco", "Rock"])

    def test_genre_from_v23_2(self):
        tags = ID3()
        tags.add(id3.TCON(encoding=1, text=["(RX)(3)(CR)"]))
        tags.update_to_v23()
        self.failUnlessEqual(tags["TCON"].text, ["Remix", "Dance", "Cover"])

    def test_ipls(self):
        tags = ID3()
        tags.version = (2, 3)
        tags.add(id3.TIPL(encoding=0, people=[["a", "b"], ["c", "d"]]))
        tags.add(id3.TMCL(encoding=0, people=[["e", "f"], ["g", "h"]]))
        tags.update_to_v23()
        self.failUnlessEqual(tags["IPLS"], [["a", "b"], ["c", "d"],
                                            ["e", "f"], ["g", "h"]])


class WriteTo23(TestCase):

    SILENCE = os.path.join(DATA_DIR, "silence-44-s.mp3")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(self.SILENCE, self.filename)
        self.audio = ID3(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_update_to_v23_on_load(self):
        from mutagen.id3 import TSOT
        self.audio.add(TSOT(text=["Ha"], encoding=3))
        self.audio.save()

        # update_to_v23 called
        id3 = ID3(self.filename, v2_version=3)
        self.assertFalse(id3.getall("TSOT"))

        # update_to_v23 not called
        id3 = ID3(self.filename, v2_version=3, translate=False)
        self.assertTrue(id3.getall("TSOT"))

    def test_load_save_inval_version(self):
        self.assertRaises(ValueError, self.audio.save, v2_version=5)
        self.assertRaises(ValueError, ID3, self.filename, v2_version=5)

    def test_save(self):
        strings = ["one", "two", "three"]
        from mutagen.id3 import TPE1
        self.audio.add(TPE1(text=strings, encoding=3))
        self.audio.save(v2_version=3)

        frame = self.audio["TPE1"]
        self.assertEqual(frame.encoding, 3)
        self.assertEqual(frame.text, strings)

        id3 = ID3(self.filename, translate=False)
        self.assertEqual(id3.version, (2, 3, 0))
        frame = id3["TPE1"]
        self.assertEqual(frame.encoding, 1)
        self.assertEqual(frame.text, ["/".join(strings)])

        # null separator, mutagen can still read it
        self.audio.save(v2_version=3, v23_sep=None)

        id3 = ID3(self.filename, translate=False)
        self.assertEqual(id3.version, (2, 3, 0))
        frame = id3["TPE1"]
        self.assertEqual(frame.encoding, 1)
        self.assertEqual(frame.text, strings)

    def test_save_off_spec_frames(self):
        # These are not defined in v2.3 and shouldn't be written.
        # Still make sure reading them again works and the encoding
        # is at least changed

        from mutagen.id3 import TDEN, TIPL
        dates = ["2013", "2014"]
        frame = TDEN(text=dates, encoding=3)
        self.audio.add(frame)
        tipl_frame = TIPL(people=[("a", "b"), ("c", "d")], encoding=2)
        self.audio.add(tipl_frame)
        self.audio.save(v2_version=3)

        id3 = ID3(self.filename, translate=False)
        self.assertEqual(id3.version, (2, 3, 0))

        self.assertEqual([stamp.text for stamp in id3["TDEN"].text], dates)
        self.assertEqual(id3["TDEN"].encoding, 1)

        self.assertEqual(id3["TIPL"].people, tipl_frame.people)
        self.assertEqual(id3["TIPL"].encoding, 1)


class Read22FrameNamesin23(TestCase):

    def test_PIC_in_23(self):
        fd, filename = mkstemp(suffix='.mp3')
        os.close(fd)

        try:
            with open(filename, "wb") as h:
                # contains a bad upgraded frame, 2.3 structure with 2.2 name.
                # PIC was upgraded to APIC, but mime was not
                h.write(b"ID3\x03\x00\x00\x00\x00\x08\x00PIC\x00\x00\x00"
                        b"\x00\x0b\x00\x00\x00JPG\x00\x03foo\x00\x42"
                        b"\x00" * 100)
            id3 = ID3(filename)
            self.assertEqual(id3.version, (2, 3, 0))
            self.assertTrue(id3.getall("APIC"))
            frame = id3.getall("APIC")[0]
            self.assertEqual(frame.mime, "image/jpeg")
            self.assertEqual(frame.data, b"\x42")
            self.assertEqual(frame.type, 3)
            self.assertEqual(frame.desc, "foo")
        finally:
            os.remove(filename)


class ID3V1_vs_APEv2(TestCase):
    SILENCE = os.path.join(DATA_DIR, "silence-44-s.mp3")

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(self.SILENCE, self.filename)

    def test_save_id3_over_ape(self):
        id3.delete(self.filename, delete_v2=False)

        ape_tag = APEv2()
        ape_tag["oh"] = ["no"]
        ape_tag.save(self.filename)

        ID3(self.filename).save()
        self.assertEqual(APEv2(self.filename)["oh"], "no")

    def test_delete_id3_with_ape(self):
        ID3(self.filename).save(v1=2)

        ape_tag = APEv2()
        ape_tag["oh"] = ["no"]
        ape_tag.save(self.filename)

        id3.delete(self.filename, delete_v2=False)
        self.assertEqual(APEv2(self.filename)["oh"], "no")

    def test_ape_id3_lookalike(self):
        # mp3 with apev2 tag that parses as id3v1 (at least with ParseID3v1)

        id3.delete(self.filename, delete_v2=False)

        ape_tag = APEv2()
        ape_tag["oh"] = [
            "noooooooooo0000000000000000000000000000000000ooooooooooo"]
        ape_tag.save(self.filename)

        ID3(self.filename).save()
        self.assertTrue(APEv2(self.filename))

    def tearDown(self):
        os.remove(self.filename)


class TID3Misc(TestCase):

    def test_main(self):
        self.assertEqual(id3.Encoding.UTF8, 3)
        self.assertEqual(id3.ID3v1SaveOptions.UPDATE, 1)
        self.assertEqual(id3.PictureType.COVER_FRONT, 3)

    def test_determine_bpi(self):
        determine_bpi = id3._determine_bpi
        # default to BitPaddedInt
        self.assertTrue(determine_bpi("", {}) is BitPaddedInt)

        def get_frame_data(name, size, bpi=True):
            data = name
            if bpi:
                data += BitPaddedInt.to_str(size)
            else:
                data += BitPaddedInt.to_str(size, bits=8)
            data += b"\x00\x00" + b"\x01" * size
            return data

        data = get_frame_data(b"TPE2", 1000, True)
        self.assertTrue(determine_bpi(data, Frames) is BitPaddedInt)
        self.assertTrue(
            determine_bpi(data + b"\x00" * 1000, Frames) is BitPaddedInt)

        data = get_frame_data(b"TPE2", 1000, False)
        self.assertTrue(determine_bpi(data, Frames) is int)
        self.assertTrue(determine_bpi(data + b"\x00" * 1000, Frames) is int)

        # in this case it helps that we know the frame name
        d = get_frame_data(b"TPE2", 1000) + get_frame_data(b"TPE2", 10) + \
                b"\x01" * 875
        self.assertTrue(determine_bpi(d, Frames) is BitPaddedInt)


class TID3Padding(TestCase):

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        orig = os.path.join(DATA_DIR, "silence-44-s.mp3")
        shutil.copy(orig, self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_fill_all(self):
        tag = ID3(self.filename)
        self.assertEqual(tag._padding, 1142)
        tag.delall("TPE1")
        # saving should increase the padding not decrease the tag size
        tag.save()
        tag = ID3(self.filename)
        self.assertEqual(tag._padding, 1166)

    def test_remove_add_padding(self):
        ID3(self.filename).save()

        tag = ID3(self.filename)
        old_padding = tag._padding
        old_size = os.path.getsize(self.filename)
        tag.save(padding=lambda x: 0)
        self.assertEqual(os.path.getsize(self.filename),
                         old_size - old_padding)
        old_size = old_size - old_padding
        tag.save(padding=lambda x: 137)
        self.assertEqual(os.path.getsize(self.filename),
                         old_size + 137)


class TID3Corrupt(TestCase):

    def setUp(self):
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        orig = os.path.join(DATA_DIR, "silence-44-s.mp3")
        shutil.copy(orig, self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_header_too_small(self):
        with open(self.filename, "r+b") as h:
            h.truncate(5)
        self.assertRaises(id3.error, ID3, self.filename)

    def test_tag_too_small(self):
        with open(self.filename, "r+b") as h:
            h.truncate(50)
        self.assertRaises(id3.error, ID3, self.filename)

    def test_save(self):
        with open(self.filename, "r+b") as h:
            h.seek(5, 0)
            h.write(b"nope")
        self.assertRaises(id3.error, ID3().save, self.filename)

try:
    import eyeD3
except ImportError:
    del WriteForEyeD3
