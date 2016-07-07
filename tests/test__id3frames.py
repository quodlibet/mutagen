# -*- coding: utf-8 -*-

from tests import TestCase

from mutagen._compat import text_type, xrange, PY2, PY3
from mutagen._constants import GENRES
from mutagen.id3._tags import read_frames, save_frame, ID3Header
from mutagen.id3._util import ID3SaveConfig, is_valid_frame_id, \
    ID3JunkFrameError
from mutagen.id3 import APIC, CTOC, CHAP, TPE2, Frames, Frames_2_2, CRA, \
    AENC, PIC, LNK, LINK, SIGN, PRIV, GRID, ENCR, COMR, USER, UFID, GEOB, \
    POPM, EQU2, RVA2, COMM, SYLT, USLT, WXXX, TXXX, WCOM, TextFrame, \
    UrlFrame, NumericTextFrame, NumericPartTextFrame, TPE1, TIT2, \
    TimeStampTextFrame, TCON, ID3TimeStamp, TIT1, Frame, RVRB, RBUF

_22 = ID3Header()
_22.version = (2, 2, 0)

_23 = ID3Header()
_23.version = (2, 3, 0)

_24 = ID3Header()
_24.version = (2, 4, 0)


class TCRA(TestCase):

    def test_upgrade(self):
        frame = CRA(owner="a", preview_start=1, preview_length=2, data=b"foo")
        new = AENC(frame)
        self.assertEqual(new.owner, "a")
        self.assertEqual(new.preview_start, 1)
        self.assertEqual(new.preview_length, 2)
        self.assertEqual(new.data, b"foo")

        frame = CRA(owner="a", preview_start=1, preview_length=2)
        new = AENC(frame)
        self.assertFalse(hasattr(new, "data"))


class TPIC(TestCase):

    def test_upgrade(self):
        frame = PIC(encoding=0, mime="PNG", desc="bla", type=3, data=b"\x00")
        new = APIC(frame)
        self.assertEqual(new.encoding, 0)
        self.assertEqual(new.mime, "PNG")
        self.assertEqual(new.desc, "bla")
        self.assertEqual(new.data, b"\x00")

        frame = PIC(encoding=0, mime="foo",
                    desc="bla", type=3, data=b"\x00")
        self.assertEqual(frame.mime, "foo")
        new = APIC(frame)
        self.assertEqual(new.mime, "foo")


class TLNK(TestCase):

    def test_upgrade(self):
        url = "http://foo.bar"

        frame = LNK(frameid="PIC", url=url, data=b"\x00")
        new = LINK(frame)
        self.assertEqual(new.frameid, "APIC")
        self.assertEqual(new.url, url)
        self.assertEqual(new.data, b"\x00")

        frame = LNK(frameid="o_O")
        new = LINK(frame)
        self.assertEqual(new.frameid, "o_O ")


class TSIGN(TestCase):

    def test_hash(self):
        frame = SIGN(group=1, sig=b"foo")
        self.assertEqual(frame.HashKey, "SIGN:1:foo")

    def test_pprint(self):
        frame = SIGN(group=1, sig=b"foo")
        frame._pprint()


class TPRIV(TestCase):

    def test_hash(self):
        frame = PRIV(owner="foo", data=b"foo")
        self.assertEqual(frame.HashKey, "PRIV:foo:foo")
        frame._pprint()

        frame = PRIV(owner="foo", data=b"\x00\xff")
        self.assertEqual(frame.HashKey, u"PRIV:foo:\x00\xff")
        frame._pprint()


class TGRID(TestCase):

    def test_hash(self):
        frame = GRID(owner="foo", group=42)
        self.assertEqual(frame.HashKey, "GRID:42")
        frame._pprint()


class TENCR(TestCase):

    def test_hash(self):
        frame = ENCR(owner="foo", method=42, data=b"\xff")
        self.assertEqual(frame.HashKey, "ENCR:foo")
        frame._pprint()


class TCOMR(TestCase):

    def test_hash(self):
        frame = COMR(
            encoding=0, price="p", valid_until="v" * 8, contact="c",
            format=42, seller="s", desc="d", mime="m", logo=b"\xff")
        self.assertEqual(
            frame.HashKey, u"COMR:\x00p\x00vvvvvvvvc\x00*s\x00d\x00m\x00\xff")
        frame._pprint()


class TUSER(TestCase):

    def test_hash(self):
        frame = USER(encoding=0, lang="foo", text="bla")
        self.assertEqual(frame.HashKey, "USER:foo")
        frame._pprint()

        self.assertEquals(USER(text="a").HashKey, USER(text="b").HashKey)
        self.assertNotEquals(
            USER(lang="abc").HashKey, USER(lang="def").HashKey)


class TTIT2(TestCase):

    def test_hash(self):
        self.assertEquals(TIT2(text="a").HashKey, TIT2(text="b").HashKey)


class TUFID(TestCase):

    def test_hash(self):
        frame = UFID(owner="foo", data=b"\x42")
        self.assertEqual(frame.HashKey, "UFID:foo")
        frame._pprint()

        self.assertEquals(UFID(data=b"1").HashKey, UFID(data=b"2").HashKey)
        self.assertNotEquals(UFID(owner="a").HashKey, UFID(owner="b").HashKey)


class TLINK(TestCase):

    def test_hash(self):
        frame = LINK(frameid="TPE1", url="http://foo.bar", data=b"\x42")
        self.assertEqual(frame.HashKey, "LINK:TPE1:http://foo.bar:B")
        frame._pprint()

        frame = LINK(frameid="TPE1", url="http://foo.bar")
        self.assertEqual(frame.HashKey, "LINK:TPE1:http://foo.bar")


class TAENC(TestCase):

    def test_hash(self):
        frame = AENC(
            owner="foo", preview_start=1, preview_length=2, data=b"\x42")
        self.assertEqual(frame.HashKey, "AENC:foo")
        frame._pprint()


class TGEOB(TestCase):

    def test_hash(self):
        frame = GEOB(
            encoding=0, mtime="m", filename="f", desc="d", data=b"\x42")
        self.assertEqual(frame.HashKey, "GEOB:d")
        frame._pprint()

        self.assertEquals(GEOB(data=b"1").HashKey, GEOB(data=b"2").HashKey)
        self.assertNotEquals(GEOB(desc="a").HashKey, GEOB(desc="b").HashKey)


class TPOPM(TestCase):

    def test_hash(self):
        frame = POPM(email="e", rating=42)
        self.assertEqual(frame.HashKey, "POPM:e")
        frame._pprint()

        self.assertEquals(POPM(count=1).HashKey, POPM(count=2).HashKey)
        self.assertNotEquals(POPM(email="a").HashKey, POPM(email="b").HashKey)


class TEQU2(TestCase):

    def test_hash(self):
        frame = EQU2(method=42, desc="d", adjustments=[(0, 0)])
        self.assertEqual(frame.HashKey, "EQU2:d")
        frame._pprint()


class TCOMM(TestCase):

    def test_hash(self):
        frame = COMM(encoding=0, lang="foo", desc="d")
        self.assertEqual(frame.HashKey, "COMM:d:foo")
        frame._pprint()

        self.assertEquals(COMM(text="a").HashKey, COMM(text="b").HashKey)
        self.assertNotEquals(COMM(desc="a").HashKey, COMM(desc="b").HashKey)
        self.assertNotEquals(
            COMM(lang="abc").HashKey, COMM(lang="def").HashKey)

    def test_bad_unicodedecode(self):
        # 7 bytes of "UTF16" data.
        data = b'\x01\x00\x00\x00\xff\xfe\x00\xff\xfeh\x00'
        self.assertRaises(ID3JunkFrameError, COMM._fromData, _24, 0x00, data)


class TSYLT(TestCase):

    def test_hash(self):
        frame = SYLT(encoding=0, lang="foo", format=1, type=2,
                     desc="d", text=[("t", 0)])
        self.assertEqual(frame.HashKey, "SYLT:d:foo")
        frame._pprint()

    def test_bad_sylt(self):
        self.assertRaises(
            ID3JunkFrameError, SYLT._fromData, _24, 0x0,
            b"\x00eng\x01description\x00foobar")
        self.assertRaises(
            ID3JunkFrameError, SYLT._fromData, _24, 0x0,
            b"\x00eng\x01description\x00foobar\x00\xFF\xFF\xFF")


class TRVRB(TestCase):

    def test_extradata(self):
        self.assertEqual(RVRB()._readData(_24, b'L1R1BBFFFFPP#xyz'), b'#xyz')


class TRBUF(TestCase):

    def test_extradata(self):
        self.assertEqual(
            RBUF()._readData(
                _24, b'\x00\x01\x00\x01\x00\x00\x00\x00#xyz'), b'#xyz')


class TUSLT(TestCase):

    def test_hash(self):
        frame = USLT(encoding=0, lang="foo", desc="d", text="t")
        self.assertEqual(frame.HashKey, "USLT:d:foo")
        frame._pprint()


class TWXXX(TestCase):

    def test_hash(self):
        self.assert_(isinstance(WXXX(url='durl'), WXXX))

        frame = WXXX(encoding=0, desc="d", url="u")
        self.assertEqual(frame.HashKey, "WXXX:d")
        frame._pprint()

        self.assertEquals(WXXX(text="a").HashKey, WXXX(text="b").HashKey)
        self.assertNotEquals(WXXX(desc="a").HashKey, WXXX(desc="b").HashKey)


class TTXXX(TestCase):

    def test_hash(self):
        frame = TXXX(encoding=0, desc="d", text=[])
        self.assertEqual(frame.HashKey, "TXXX:d")
        frame._pprint()

        self.assertEquals(TXXX(text="a").HashKey, TXXX(text="b").HashKey)
        self.assertNotEquals(TXXX(desc="a").HashKey, TXXX(desc="b").HashKey)


class TWCOM(TestCase):

    def test_hash(self):
        frame = WCOM(url="u")
        self.assertEqual(frame.HashKey, "WCOM:u")
        frame._pprint()


class TUrlFrame(TestCase):

    def test_main(self):
        self.assertEqual(UrlFrame("url").url, "url")


class TNumericTextFrame(TestCase):

    def test_main(self):
        self.assertEqual(NumericTextFrame(text='1').text, ["1"])
        self.assertEqual(+NumericTextFrame(text='1'), 1)


class TNumericPartTextFrame(TestCase):

    def test_main(self):
        self.assertEqual(NumericPartTextFrame(text='1/2').text, ["1/2"])
        self.assertEqual(+NumericPartTextFrame(text='1/2'), 1)


class Tread_frames_load_frame(TestCase):

    def test_detect_23_ints_in_24_frames(self):
        head = b'TIT1\x00\x00\x01\x00\x00\x00\x00'
        tail = b'TPE1\x00\x00\x00\x05\x00\x00\x00Yay!'

        tagsgood = read_frames(_24, head + b'a' * 127 + tail, Frames)[0]
        tagsbad = read_frames(_24, head + b'a' * 255 + tail, Frames)[0]
        self.assertEquals(2, len(tagsgood))
        self.assertEquals(2, len(tagsbad))
        self.assertEquals('a' * 127, tagsgood[0])
        self.assertEquals('a' * 255, tagsbad[0])
        self.assertEquals('Yay!', tagsgood[1])
        self.assertEquals('Yay!', tagsbad[1])

        tagsgood = read_frames(_24, head + b'a' * 127, Frames)[0]
        tagsbad = read_frames(_24, head + b'a' * 255, Frames)[0]
        self.assertEquals(1, len(tagsgood))
        self.assertEquals(1, len(tagsbad))
        self.assertEquals('a' * 127, tagsgood[0])
        self.assertEquals('a' * 255, tagsbad[0])

    def test_zerolength_framedata(self):
        tail = b'\x00' * 6
        for head in b'WOAR TENC TCOP TOPE WXXX'.split():
            data = head + tail
            self.assertEquals(
                0, len(list(read_frames(_24, data, Frames)[1])))

    def test_drops_truncated_frames(self):
        tail = b'\x00\x00\x00\x03\x00\x00' b'\x01\x02\x03'
        for head in b'RVA2 TXXX APIC'.split():
            data = head + tail
            self.assertEquals(
                0, len(read_frames(_24, data, Frames)[1]))

    def test_drops_nonalphanum_frames(self):
        tail = b'\x00\x00\x00\x03\x00\x00' b'\x01\x02\x03'
        for head in [b'\x06\xaf\xfe\x20', b'ABC\x00', b'A   ']:
            data = head + tail
            self.assertEquals(
                0, len(read_frames(_24, data, Frames)[0]))

    def test_frame_too_small(self):
        self.assertEquals([], read_frames(_24, b'012345678', Frames)[0])
        self.assertEquals([], read_frames(_23, b'012345678', Frames)[0])
        self.assertEquals([], read_frames(_22, b'01234', Frames_2_2)[0])
        self.assertEquals(
            [], read_frames(_22, b'TT1' + b'\x00' * 3, Frames_2_2)[0])

    def test_unknown_22_frame(self):
        data = b'XYZ\x00\x00\x01\x00'
        self.assertEquals([data], read_frames(_22, data, {})[1])

    def test_22_uses_direct_ints(self):
        data = b'TT1\x00\x00\x83\x00' + (b'123456789abcdef' * 16)
        tag = read_frames(_22, data, Frames_2_2)[0][0]
        self.assertEquals(data[7:7 + 0x82].decode('latin1'), tag.text[0])

    def test_load_write(self):
        artists = [s.decode('utf8') for s in
                   [b'\xc2\xb5', b'\xe6\x97\xa5\xe6\x9c\xac']]
        artist = TPE1(encoding=3, text=artists)
        config = ID3SaveConfig()
        tag = read_frames(_24, save_frame(artist, config=config), Frames)[0][0]
        self.assertEquals('TPE1', type(tag).__name__)
        self.assertEquals(artist.text, tag.text)


class TTPE2(TestCase):

    def test_unsynch(self):
        header = ID3Header()
        header.version = (2, 4, 0)
        header._flags = 0x80
        badsync = b'\x00\xff\x00ab\x00'

        self.assertEquals(TPE2._fromData(header, 0, badsync), [u"\xffab"])

        header._flags = 0x00
        self.assertEquals(TPE2._fromData(header, 0x02, badsync), [u"\xffab"])

        tag = TPE2._fromData(header, 0, badsync)
        self.assertEquals(tag, [u"\xff", u"ab"])


class TTPE1(TestCase):

    def test_badencoding(self):
        self.assertRaises(
            ID3JunkFrameError, TPE1._fromData, _24, 0, b"\x09ab")
        self.assertRaises(ValueError, TPE1, encoding=9, text="ab")

    def test_badsync(self):
        frame = TPE1._fromData(_24, 0x02, b"\x00\xff\xfe")
        self.assertEqual(frame.text, [u'\xff\xfe'])

    def test_noencrypt(self):
        self.assertRaises(
            NotImplementedError, TPE1._fromData, _24, 0x04, b"\x00")
        self.assertRaises(
            NotImplementedError, TPE1._fromData, _23, 0x40, b"\x00")

    def test_badcompress(self):
        self.assertRaises(
            ID3JunkFrameError, TPE1._fromData, _24, 0x08,
            b"\x00\x00\x00\x00#")
        self.assertRaises(
            ID3JunkFrameError, TPE1._fromData, _23, 0x80,
            b"\x00\x00\x00\x00#")

    def test_junkframe(self):
        self.assertRaises(
            ID3JunkFrameError, TPE1._fromData, _24, 0, b"")

    def test_lengthone_utf16(self):
        tpe1 = TPE1._fromData(_24, 0, b'\x01\x00')
        self.assertEquals(u'', tpe1)
        tpe1 = TPE1._fromData(_24, 0, b'\x01\x00\x00\x00\x00')
        self.assertEquals([u'', u''], tpe1)

    def test_utf16_wrongnullterm(self):
        # issue 169
        tpe1 = TPE1._fromData(
            _24, 0, b'\x01\xff\xfeH\x00e\x00l\x00l\x00o\x00\x00')
        self.assertEquals(tpe1, [u'Hello'])

    def test_zlib_bpi(self):
        tpe1 = TPE1(encoding=0, text="a" * (0xFFFF - 2))
        data = save_frame(tpe1)
        datalen_size = data[4 + 4 + 2:4 + 4 + 2 + 4]
        self.failIf(
            max(datalen_size) >= b'\x80'[0], "data is not syncsafe: %r" % data)

    def test_ql_0_12_missing_uncompressed_size(self):
        tag = TPE1._fromData(
            _24, 0x08,
            b'x\x9cc\xfc\xff\xaf\x84!\x83!\x93'
            b'\xa1\x98A\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#'
        )
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

    def test_zlib_latin1_missing_datalen(self):
        tag = TPE1._fromData(
            _24, 0x8,
            b'\x00\x00\x00\x0f'
            b'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%'
        )
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])


class TTCON(TestCase):

    def _g(self, s):
        return TCON(text=s).genres

    def test_empty(self):
        self.assertEquals(self._g(""), [])

    def test_num(self):
        for i in xrange(len(GENRES)):
            self.assertEquals(self._g("%02d" % i), [GENRES[i]])

    def test_parened_num(self):
        for i in xrange(len(GENRES)):
            self.assertEquals(self._g("(%02d)" % i), [GENRES[i]])

    def test_unknown(self):
        self.assertEquals(self._g("(255)"), ["Unknown"])
        self.assertEquals(self._g("199"), ["Unknown"])
        self.assertNotEqual(self._g("256"), ["Unknown"])

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
        gen = TCON(encoding=0, text="")
        self.assertEquals(gen.genres, [])
        gen.genres = ["a genre", "another"]
        self.assertEquals(gen.genres, ["a genre", "another"])

    def test_set_string(self):
        gen = TCON(encoding=0, text="")
        gen.genres = "foo"
        self.assertEquals(gen.genres, ["foo"])

    def test_nodoubledecode(self):
        gen = TCON(encoding=1, text=u"(255)genre")
        gen.genres = gen.genres
        self.assertEquals(gen.genres, [u"Unknown", u"genre"])


class TID3TimeStamp(TestCase):

    def test_Y(self):
        s = ID3TimeStamp('1234')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.text, '1234')

    def test_yM(self):
        s = ID3TimeStamp('1234-56')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.text, '1234-56')

    def test_ymD(self):
        s = ID3TimeStamp('1234-56-78')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.text, '1234-56-78')

    def test_ymdH(self):
        s = ID3TimeStamp('1234-56-78T12')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.text, '1234-56-78 12')

    def test_ymdhM(self):
        s = ID3TimeStamp('1234-56-78T12:34')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.minute, 34)
        self.assertEquals(s.text, '1234-56-78 12:34')

    def test_ymdhmS(self):
        s = ID3TimeStamp('1234-56-78T12:34:56')
        self.assertEquals(s.year, 1234)
        self.assertEquals(s.month, 56)
        self.assertEquals(s.day, 78)
        self.assertEquals(s.hour, 12)
        self.assertEquals(s.minute, 34)
        self.assertEquals(s.second, 56)
        self.assertEquals(s.text, '1234-56-78 12:34:56')

    def test_Ymdhms(self):
        s = ID3TimeStamp('1234-56-78T12:34:56')
        s.month = None
        self.assertEquals(s.text, '1234')

    def test_alternate_reprs(self):
        s = ID3TimeStamp('1234-56.78 12:34:56')
        self.assertEquals(s.text, '1234-56-78 12:34:56')

    def test_order(self):
        s = ID3TimeStamp('1234')
        t = ID3TimeStamp('1233-12')
        u = ID3TimeStamp('1234-01')

        self.assert_(t < s < u)
        self.assert_(u > s > t)

    def test_types(self):
        if PY3:
            self.assertRaises(TypeError, ID3TimeStamp, b"blah")
        self.assertEquals(
            text_type(ID3TimeStamp(u"2000-01-01")), u"2000-01-01")
        self.assertEquals(
            bytes(ID3TimeStamp(u"2000-01-01")), b"2000-01-01")


class TFrames(TestCase):

    def test_has_docs(self):
        for Kind in (list(Frames.values()) + list(Frames_2_2.values())):
            self.failUnless(Kind.__doc__, "%s has no docstring" % Kind)


class TFrame(TestCase):

    def test_fake_zlib(self):
        header = ID3Header()
        header.version = (2, 4, 0)
        self.assertRaises(ID3JunkFrameError, Frame._fromData, header,
                          Frame.FLAG24_COMPRESS, b'\x03abcdefg')


class NoHashFrame(TestCase):

    def test_frame(self):
        self.failUnlessRaises(
            TypeError, {}.__setitem__, TIT1(encoding=0, text="foo"), None)


class FrameIDValidate(TestCase):

    def test_valid(self):
        self.failUnless(is_valid_frame_id("APIC"))
        self.failUnless(is_valid_frame_id("TPE2"))

    def test_invalid(self):
        self.failIf(is_valid_frame_id("MP3e"))
        self.failIf(is_valid_frame_id("+ABC"))


class TTimeStampTextFrame(TestCase):

    def test_compare_to_unicode(self):
        frame = TimeStampTextFrame(encoding=0, text=[u'1987', u'1988'])
        self.failUnlessEqual(frame, text_type(frame))


class TTextFrame(TestCase):

    def test_main(self):
        self.assertEqual(TextFrame(text='text').text, ["text"])
        self.assertEqual(TextFrame(text=['a', 'b']).text, ["a", "b"])

    def test_list_iface(self):
        frame = TextFrame()
        frame.append("a")
        frame.extend(["b", "c"])
        self.assertEqual(frame.text, ["a", "b", "c"])

    def test_zlib_latin1(self):
        tag = TextFrame._fromData(
            _24, 0x9, b'\x00\x00\x00\x0f'
            b'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%'
        )
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])

    def test_datalen_but_not_compressed(self):
        tag = TextFrame._fromData(_24, 0x01, b'\x00\x00\x00\x06\x00A test')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['A test'])

    def test_utf8(self):
        tag = TextFrame._fromData(_23, 0x00, b'\x03this is a test')
        self.assertEquals(tag.encoding, 3)
        self.assertEquals(tag, 'this is a test')

    def test_zlib_utf16(self):
        data = (b'\x00\x00\x00\x1fx\x9cc\xfc\xff\xaf\x84!\x83!\x93\xa1\x98A'
                b'\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#')
        tag = TextFrame._fromData(_23, 0x80, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

        tag = TextFrame._fromData(_24, 0x08, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])


class TRVA2(TestCase):

    def test_basic(self):
        r = RVA2(gain=1, channel=1, peak=1)
        self.assertEqual(r, r)
        self.assertNotEqual(r, 42)

    def test_hash_key(self):
        frame = RVA2(method=42, desc="d", channel=1, gain=1, peak=1)
        self.assertEqual(frame.HashKey, "RVA2:d")

        self.assertEquals(RVA2(gain=1).HashKey, RVA2(gain=2).HashKey)
        self.assertNotEquals(RVA2(desc="a").HashKey, RVA2(desc="b").HashKey)

    def test_pprint(self):
        frame = RVA2(method=42, desc="d", channel=1, gain=1, peak=1)
        frame._pprint()

    def test_wacky_truncated(self):
        data = b'\x01{\xf0\x10\xff\xff\x00'
        self.assertRaises(ID3JunkFrameError, RVA2._fromData, _24, 0x00, data)

    def test_bad_number_of_bits(self):
        data = b'\x00\x00\x01\xe6\xfc\x10{\xd7'
        self.assertRaises(ID3JunkFrameError, RVA2._fromData, _24, 0x00, data)


class TCTOC(TestCase):

    def test_hash(self):
        frame = CTOC(element_id=u"foo", flags=3,
                     child_element_ids=[u"ch0"],
                     sub_frames=[TPE2(encoding=3, text=[u"foo"])])
        self.assertEqual(frame.HashKey, "CTOC:foo")

    def test_pprint(self):
        frame = CTOC(element_id=u"foo", flags=3,
                     child_element_ids=[u"ch0"],
                     sub_frames=[TPE2(encoding=3, text=[u"foo"])])
        self.assertEqual(
            frame.pprint(),
            "CTOC=foo flags=3 child_element_ids=ch0\n    TPE2=foo")

    def test_write(self):
        frame = CTOC(element_id=u"foo", flags=3,
                     child_element_ids=[u"ch0"],
                     sub_frames=[TPE2(encoding=3, text=[u"f", u"b"])])
        config = ID3SaveConfig(3, "/")
        data = (b"foo\x00\x03\x01ch0\x00TPE2\x00\x00\x00\x0b\x00\x00\x01"
                b"\xff\xfef\x00/\x00b\x00\x00\x00")
        self.assertEqual(frame._writeData(config), data)

    def test_eq(self):
        self.assertEqual(CTOC(), CTOC())
        self.assertNotEqual(CTOC(), object())


class TCHAP(TestCase):

    def test_hash(self):
        frame = CHAP(element_id=u"foo", start_time=0, end_time=0,
                     start_offset=0, end_offset=0,
                     sub_frames=[TPE2(encoding=3, text=[u"foo"])])
        self.assertEqual(frame.HashKey, "CHAP:foo")

    def test_pprint(self):
        frame = CHAP(element_id=u"foo", start_time=0, end_time=0,
                     start_offset=0, end_offset=0,
                     sub_frames=[TPE2(encoding=3, text=[u"foo"])])
        self.assertEqual(
            frame.pprint(), "CHAP=foo time=0..0 offset=0..0\n    TPE2=foo")

    def test_eq(self):
        self.assertEqual(CHAP(), CHAP())
        self.assertNotEqual(CHAP(), object())


class TAPIC(TestCase):

    def test_hash(self):
        frame = APIC(encoding=0, mime=u"m", type=3, desc=u"d", data=b"\x42")
        self.assertEqual(frame.HashKey, "APIC:d")

    def test_pprint(self):
        frame = APIC(
            encoding=0, mime=u"mime", type=3, desc=u"desc", data=b"\x42")
        self.assertEqual(frame._pprint(), u"cover front, desc (mime, 1 bytes)")

    def test_multi(self):
        self.assertEquals(APIC(data=b"1").HashKey, APIC(data=b"2").HashKey)
        self.assertNotEquals(APIC(desc="a").HashKey, APIC(desc="b").HashKey)

    def test_repr(self):
        frame = APIC(encoding=0, mime=u"m", type=3, desc=u"d", data=b"\x42")
        if PY2:
            expected = (
                "APIC(encoding=<Encoding.LATIN1: 0>, mime=u'm', "
                "type=<PictureType.COVER_FRONT: 3>, desc=u'd', data='B')")
        else:
            expected = (
                "APIC(encoding=<Encoding.LATIN1: 0>, mime='m', "
                "type=<PictureType.COVER_FRONT: 3>, desc='d', data=b'B')")

        self.assertEqual(repr(frame), expected)
        new_frame = APIC()
        new_frame._readData(_24, frame._writeData())
        self.assertEqual(repr(new_frame), expected)
