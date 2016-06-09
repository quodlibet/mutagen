# -*- coding: utf-8 -*-

from tests import TestCase

from mutagen.id3 import Frames, Frames_2_2, ID3, ID3Header
from mutagen._compat import text_type, xrange, PY2
from mutagen.id3 import APIC

_22 = ID3()
_22._header = ID3Header()
_22._header.version = (2, 2, 0)

_23 = ID3()
_23._header = ID3Header()
_23._header.version = (2, 3, 0)

_24 = ID3()
_24._header = ID3Header()
_24._header.version = (2, 4, 0)


class FrameSanityChecks(TestCase):

    def test_CRA_upgrade(self):
        from mutagen.id3 import CRA, AENC
        frame = CRA(owner="a", preview_start=1, preview_length=2, data=b"foo")
        new = AENC(frame)
        self.assertEqual(new.owner, "a")
        self.assertEqual(new.preview_start, 1)
        self.assertEqual(new.preview_length, 2)
        self.assertEqual(new.data, b"foo")

        frame = CRA(owner="a", preview_start=1, preview_length=2)
        new = AENC(frame)
        self.assertFalse(hasattr(new, "data"))

    def test_PIC_upgrade(self):
        from mutagen.id3 import PIC
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

    def test_LNK_upgrade(self):
        from mutagen.id3 import LNK, LINK
        url = "http://foo.bar"

        frame = LNK(frameid="PIC", url=url, data=b"\x00")
        new = LINK(frame)
        self.assertEqual(new.frameid, "APIC")
        self.assertEqual(new.url, url)
        self.assertEqual(new.data, b"\x00")

        frame = LNK(frameid="o_O")
        new = LINK(frame)
        self.assertEqual(new.frameid, "o_O ")

    def test_SIGN(self):
        from mutagen.id3 import SIGN
        frame = SIGN(group=1, sig=b"foo")
        self.assertEqual(frame.HashKey, "SIGN:1:foo")
        frame._pprint()

    def test_PRIV(self):
        from mutagen.id3 import PRIV
        frame = PRIV(owner="foo", data=b"foo")
        self.assertEqual(frame.HashKey, "PRIV:foo:foo")
        frame._pprint()

        frame = PRIV(owner="foo", data=b"\x00\xff")
        self.assertEqual(frame.HashKey, u"PRIV:foo:\x00\xff")
        frame._pprint()

    def test_GRID(self):
        from mutagen.id3 import GRID

        frame = GRID(owner="foo", group=42)
        self.assertEqual(frame.HashKey, "GRID:42")
        frame._pprint()

    def test_ENCR(self):
        from mutagen.id3 import ENCR

        frame = ENCR(owner="foo", method=42, data=b"\xff")
        self.assertEqual(frame.HashKey, "ENCR:foo")
        frame._pprint()

    def test_COMR(self):
        from mutagen.id3 import COMR

        frame = COMR(
            encoding=0, price="p", valid_until="v" * 8, contact="c",
            format=42, seller="s", desc="d", mime="m", logo=b"\xff")
        self.assertEqual(
            frame.HashKey, u"COMR:\x00p\x00vvvvvvvvc\x00*s\x00d\x00m\x00\xff")
        frame._pprint()

    def test_USER(self):
        from mutagen.id3 import USER

        frame = USER(encoding=0, lang="foo", text="bla")
        self.assertEqual(frame.HashKey, "USER:foo")
        frame._pprint()

    def test_UFID(self):
        from mutagen.id3 import UFID

        frame = UFID(owner="foo", data=b"\x42")
        self.assertEqual(frame.HashKey, "UFID:foo")
        frame._pprint()

    def test_LINK(self):
        from mutagen.id3 import LINK

        frame = LINK(frameid="TPE1", url="http://foo.bar", data=b"\x42")
        self.assertEqual(frame.HashKey, "LINK:TPE1:http://foo.bar:B")
        frame._pprint()

        frame = LINK(frameid="TPE1", url="http://foo.bar")
        self.assertEqual(frame.HashKey, "LINK:TPE1:http://foo.bar")

    def test_AENC(self):
        from mutagen.id3 import AENC

        frame = AENC(
            owner="foo", preview_start=1, preview_length=2, data=b"\x42")
        self.assertEqual(frame.HashKey, "AENC:foo")
        frame._pprint()

    def test_GEOB(self):
        from mutagen.id3 import GEOB

        frame = GEOB(
            encoding=0, mtime="m", filename="f", desc="d", data=b"\x42")
        self.assertEqual(frame.HashKey, "GEOB:d")
        frame._pprint()

    def test_POPM(self):
        from mutagen.id3 import POPM

        frame = POPM(email="e", rating=42)
        self.assertEqual(frame.HashKey, "POPM:e")
        frame._pprint()

    def test_EQU2(self):
        from mutagen.id3 import EQU2

        frame = EQU2(method=42, desc="d", adjustments=[(0, 0)])
        self.assertEqual(frame.HashKey, "EQU2:d")
        frame._pprint()

    def test_RVA2(self):
        from mutagen.id3 import RVA2

        frame = RVA2(method=42, desc="d", channel=1, gain=1, peak=1)
        self.assertEqual(frame.HashKey, "RVA2:d")
        frame._pprint()

    def test_COMM(self):
        from mutagen.id3 import COMM

        frame = COMM(encoding=0, lang="foo", desc="d")
        self.assertEqual(frame.HashKey, "COMM:d:foo")
        frame._pprint()

    def test_SYLT(self):
        from mutagen.id3 import SYLT

        frame = SYLT(encoding=0, lang="foo", format=1, type=2,
                     desc="d", text=[("t", 0)])
        self.assertEqual(frame.HashKey, "SYLT:d:foo")
        frame._pprint()

    def test_USLT(self):
        from mutagen.id3 import USLT

        frame = USLT(encoding=0, lang="foo", desc="d", text="t")
        self.assertEqual(frame.HashKey, "USLT:d:foo")
        frame._pprint()

    def test_WXXX(self):
        from mutagen.id3 import WXXX

        self.assert_(isinstance(WXXX(url='durl'), WXXX))

        frame = WXXX(encoding=0, desc="d", url="u")
        self.assertEqual(frame.HashKey, "WXXX:d")
        frame._pprint()

    def test_TXXX(self):
        from mutagen.id3 import TXXX
        self.assert_(isinstance(TXXX(desc='d', text='text'), TXXX))

        frame = TXXX(encoding=0, desc="d", text=[])
        self.assertEqual(frame.HashKey, "TXXX:d")
        frame._pprint()

    def test_WCOM(self):
        from mutagen.id3 import WCOM

        frame = WCOM(url="u")
        self.assertEqual(frame.HashKey, "WCOM:u")
        frame._pprint()

    def test_TF(self):
        from mutagen.id3 import TextFrame
        self.assert_(isinstance(TextFrame(text='text'), TextFrame))

    def test_UF(self):
        from mutagen.id3 import UrlFrame
        self.assert_(isinstance(UrlFrame('url'), UrlFrame))

    def test_NTF(self):
        from mutagen.id3 import NumericTextFrame
        self.assert_(isinstance(NumericTextFrame(text='1'), NumericTextFrame))

    def test_NTPF(self):
        from mutagen.id3 import NumericPartTextFrame
        self.assert_(
            isinstance(NumericPartTextFrame(text='1/2'), NumericPartTextFrame))

    def test_MTF(self):
        from mutagen.id3 import TextFrame
        self.assert_(isinstance(TextFrame(text=['a', 'b']), TextFrame))

    def test_22_uses_direct_ints(self):
        data = b'TT1\x00\x00\x83\x00' + (b'123456789abcdef' * 16)
        tag = list(_22._ID3__read_frames(data, Frames_2_2))[0]
        self.assertEquals(data[7:7 + 0x82].decode('latin1'), tag.text[0])

    def test_frame_too_small(self):
        self.assertEquals(
            [], list(_24._ID3__read_frames(b'012345678', Frames)))
        self.assertEquals(
            [], list(_23._ID3__read_frames(b'012345678', Frames)))
        self.assertEquals(
            [], list(_22._ID3__read_frames(b'01234', Frames_2_2)))
        self.assertEquals(
            [], list(_22._ID3__read_frames(b'TT1' + b'\x00' * 3, Frames_2_2)))

    def test_unknown_22_frame(self):
        data = b'XYZ\x00\x00\x01\x00'
        self.assertEquals([data], list(_22._ID3__read_frames(data, {})))

    def test_zlib_latin1(self):
        from mutagen.id3 import TPE1
        tag = TPE1._fromData(
            _24._header, 0x9, b'\x00\x00\x00\x0f'
            b'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%'
        )
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a/test'])

    def test_datalen_but_not_compressed(self):
        from mutagen.id3 import TPE1
        tag = TPE1._fromData(_24._header, 0x01, b'\x00\x00\x00\x06\x00A test')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['A test'])

    def test_utf8(self):
        from mutagen.id3 import TPE1
        tag = TPE1._fromData(_23._header, 0x00, b'\x03this is a test')
        self.assertEquals(tag.encoding, 3)
        self.assertEquals(tag, 'this is a test')

    def test_zlib_utf16(self):
        from mutagen.id3 import TPE1
        data = (b'\x00\x00\x00\x1fx\x9cc\xfc\xff\xaf\x84!\x83!\x93\xa1\x98A'
                b'\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#')
        tag = TPE1._fromData(_23._header, 0x80, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

        tag = TPE1._fromData(_24._header, 0x08, data)
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a/test'])

    def test_load_write(self):
        from mutagen.id3 import TPE1, Frames
        artists = [s.decode('utf8') for s in
                   [b'\xc2\xb5', b'\xe6\x97\xa5\xe6\x9c\xac']]
        artist = TPE1(encoding=3, text=artists)
        id3 = ID3()
        id3._header = ID3Header()
        id3._header.version = (2, 4, 0)
        tag = list(id3._ID3__read_frames(
            id3._ID3__save_frame(artist), Frames))[0]
        self.assertEquals('TPE1', type(tag).__name__)
        self.assertEquals(artist.text, tag.text)

    def test_22_to_24(self):
        from mutagen.id3 import TT1
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
        self.assertEquals(RVA2(gain=1).HashKey, RVA2(gain=2).HashKey)
        self.assertNotEquals(RVA2(desc="a").HashKey, RVA2(desc="b").HashKey)

    def test_multi_POPM(self):
        from mutagen.id3 import POPM
        self.assertEquals(POPM(count=1).HashKey, POPM(count=2).HashKey)
        self.assertNotEquals(POPM(email="a").HashKey, POPM(email="b").HashKey)

    def test_multi_GEOB(self):
        from mutagen.id3 import GEOB
        self.assertEquals(GEOB(data=b"1").HashKey, GEOB(data=b"2").HashKey)
        self.assertNotEquals(GEOB(desc="a").HashKey, GEOB(desc="b").HashKey)

    def test_multi_UFID(self):
        from mutagen.id3 import UFID
        self.assertEquals(UFID(data=b"1").HashKey, UFID(data=b"2").HashKey)
        self.assertNotEquals(UFID(owner="a").HashKey, UFID(owner="b").HashKey)

    def test_multi_USER(self):
        from mutagen.id3 import USER
        self.assertEquals(USER(text="a").HashKey, USER(text="b").HashKey)
        self.assertNotEquals(
            USER(lang="abc").HashKey, USER(lang="def").HashKey)


class Genres(TestCase):

    from mutagen.id3 import TCON
    TCON = TCON
    from mutagen._constants import GENRES
    GENRES = GENRES

    def _g(self, s):
        return self.TCON(text=s).genres

    def test_empty(self):
        self.assertEquals(self._g(""), [])

    def test_num(self):
        for i in xrange(len(self.GENRES)):
            self.assertEquals(self._g("%02d" % i), [self.GENRES[i]])

    def test_parened_num(self):
        for i in xrange(len(self.GENRES)):
            self.assertEquals(self._g("(%02d)" % i), [self.GENRES[i]])

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
        gen = self.TCON(encoding=0, text="")
        self.assertEquals(gen.genres, [])
        gen.genres = ["a genre", "another"]
        self.assertEquals(gen.genres, ["a genre", "another"])

    def test_set_string(self):
        gen = self.TCON(encoding=0, text="")
        gen.genres = "foo"
        self.assertEquals(gen.genres, ["foo"])

    def test_nodoubledecode(self):
        gen = self.TCON(encoding=1, text=u"(255)genre")
        gen.genres = gen.genres
        self.assertEquals(gen.genres, [u"Unknown", u"genre"])


class TimeStamp(TestCase):

    from mutagen.id3 import ID3TimeStamp as Stamp
    Stamp = Stamp

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


class NoHashFrame(TestCase):

    def test_frame(self):
        from mutagen.id3 import TIT1
        self.failUnlessRaises(
            TypeError, {}.__setitem__, TIT1(encoding=0, text="foo"), None)


class FrameIDValidate(TestCase):

    def test_valid(self):
        from mutagen.id3 import is_valid_frame_id
        self.failUnless(is_valid_frame_id("APIC"))
        self.failUnless(is_valid_frame_id("TPE2"))

    def test_invalid(self):
        from mutagen.id3 import is_valid_frame_id
        self.failIf(is_valid_frame_id("MP3e"))
        self.failIf(is_valid_frame_id("+ABC"))


class TimeStampTextFrame(TestCase):

    from mutagen.id3 import TimeStampTextFrame as Frame
    Frame = Frame

    def test_compare_to_unicode(self):
        frame = self.Frame(encoding=0, text=[u'1987', u'1988'])
        self.failUnlessEqual(frame, text_type(frame))


class TTextFrame(TestCase):

    def test_list_iface(self):
        from mutagen.id3 import TextFrame

        frame = TextFrame()
        frame.append("a")
        frame.extend(["b", "c"])
        self.assertEqual(frame.text, ["a", "b", "c"])


class TRVA2(TestCase):

    def test_basic(self):
        from mutagen.id3 import RVA2
        r = RVA2(gain=1, channel=1, peak=1)
        self.assertEqual(r, r)
        self.assertNotEqual(r, 42)


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
        new_frame._readData(frame._writeData())
        self.assertEqual(repr(new_frame), expected)
