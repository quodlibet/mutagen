
import os
import subprocess

import pytest

from mutagen import MutagenError
from mutagen.flac import (
    FLAC,
    CueSheet,
    MetadataBlock,
    Padding,
    Picture,
    SeekTable,
    StreamInfo,
    VCFLACDict,
    delete,
    error,
    to_int_be,
)
from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from tests import DATA_DIR, TestCase, get_temp_copy
from tests.test__vorbis import TVCommentDict, VComment


def call_flac(*args):
    with open(os.devnull, 'wb') as null:
        return subprocess.call(
            ["flac"] + list(args), stdout=null, stderr=subprocess.STDOUT)


class Tto_int_be(TestCase):

    def test_empty(self):
        self.assertEqual(to_int_be(b""), 0)

    def test_0(self):
        self.assertEqual(to_int_be(b"\x00"), 0)

    def test_1(self):
        self.assertEqual(to_int_be(b"\x01"), 1)

    def test_256(self):
        self.assertEqual(to_int_be(b"\x01\x00"), 256)

    def test_long(self):
        self.assertEqual(to_int_be(b"\x01\x00\x00\x00\x00"), 2 ** 32)


class TVCFLACDict(TVCommentDict):

    Kind = VCFLACDict

    def test_roundtrip_vc(self):
        self.assertEqual(self.c, VComment(self.c.write() + b"\x01"))


class TMetadataBlock(TestCase):

    def test_empty(self):
        self.assertEqual(MetadataBlock(b"").write(), b"")

    def test_not_empty(self):
        self.assertEqual(MetadataBlock(b"foobar").write(), b"foobar")

    def test_change(self):
        b = MetadataBlock(b"foobar")
        b.data = b"quux"
        self.assertEqual(b.write(), b"quux")

    def test_write_read_max_size(self):

        class SomeBlock(MetadataBlock):
            code = 255

        max_data_size = 2 ** 24 - 1
        block = SomeBlock(b"\x00" * max_data_size)
        data = MetadataBlock._writeblock(block)
        self.assertEqual(data[:4], b"\xff\xff\xff\xff")
        header_size = 4
        self.assertEqual(len(data), max_data_size + header_size)

        block = SomeBlock(b"\x00" * (max_data_size + 1))
        self.assertRaises(error, MetadataBlock._writeblock, block)

    def test_ctr_garbage(self):
        self.assertRaises(TypeError, StreamInfo, 12)

    def test_too_large(self):
        block = Picture()
        block.data = b"\x00" * 0x1FFFFFF
        self.assertRaises(
            error, MetadataBlock._writeblocks, [block], 0, 0, None)

    def test_too_large_padding(self):
        block = Padding()
        self.assertEqual(
            len(MetadataBlock._writeblocks([block], 0, 0, lambda x: 2 ** 24)),
            2**24 - 1 + 4)


class TStreamInfo(TestCase):

    data = (b'\x12\x00\x12\x00\x00\x00\x0e\x005\xea\n\xc4H\xf0\x00\xca0'
            b'\x14(\x90\xf9\xe1)2\x13\x01\xd4\xa7\xa9\x11!8\xab\x91')
    data_invalid = len(data) * b'\x00'

    def setUp(self):
        self.i = StreamInfo(self.data)

    def test_bitrate(self):
        assert self.i.bitrate == 0

    def test_invalid(self):
        # https://github.com/quodlibet/mutagen/issues/117
        self.assertRaises(error, StreamInfo, self.data_invalid)

    def test_blocksize(self):
        self.assertEqual(self.i.max_blocksize, 4608)
        self.assertEqual(self.i.min_blocksize, 4608)
        self.assertTrue(self.i.min_blocksize <= self.i.max_blocksize)

    def test_framesize(self):
        self.assertEqual(self.i.min_framesize, 14)
        self.assertEqual(self.i.max_framesize, 13802)
        self.assertTrue(self.i.min_framesize <= self.i.max_framesize)

    def test_sample_rate(self):
        self.assertEqual(self.i.sample_rate, 44100)

    def test_channels(self):
        self.assertEqual(self.i.channels, 5)

    def test_bps(self):
        self.assertEqual(self.i.bits_per_sample, 16)

    def test_length(self):
        self.assertAlmostEqual(self.i.length, 300.5, 1)

    def test_total_samples(self):
        self.assertEqual(self.i.total_samples, 13250580)

    def test_md5_signature(self):
        self.assertEqual(self.i.md5_signature,
                             int("2890f9e129321301d4a7a9112138ab91", 16))

    def test_eq(self):
        self.assertEqual(self.i, self.i)

    def test_roundtrip(self):
        self.assertEqual(StreamInfo(self.i.write()), self.i)


class TSeekTable(TestCase):
    SAMPLE = os.path.join(DATA_DIR, "silence-44-s.flac")

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.st = self.flac.seektable

    def test_seektable(self):
        self.assertEqual(self.st.seekpoints,
                             [(0, 0, 4608),
                              (41472, 11852, 4608),
                              (50688, 14484, 4608),
                              (87552, 25022, 4608),
                              (105984, 30284, 4608),
                              (0xFFFFFFFFFFFFFFFF, 0, 0)])

    def test_eq(self):
        self.assertEqual(self.st, self.st)

    def test_neq(self):
        self.assertNotEqual(self.st, 12)

    def test_repr(self):
        repr(self.st)

    def test_roundtrip(self):
        self.assertEqual(SeekTable(self.st.write()), self.st)


class TCueSheet(TestCase):
    SAMPLE = os.path.join(DATA_DIR, "silence-44-s.flac")

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.cs = self.flac.cuesheet

    def test_cuesheet(self):
        self.assertEqual(self.cs.media_catalog_number, b"1234567890123")
        self.assertEqual(self.cs.lead_in_samples, 88200)
        self.assertEqual(self.cs.compact_disc, True)
        self.assertEqual(len(self.cs.tracks), 4)

    def test_first_track(self):
        self.assertEqual(self.cs.tracks[0].track_number, 1)
        self.assertEqual(self.cs.tracks[0].start_offset, 0)
        self.assertEqual(self.cs.tracks[0].isrc, b'123456789012')
        self.assertEqual(self.cs.tracks[0].type, 0)
        self.assertEqual(self.cs.tracks[0].pre_emphasis, False)
        self.assertEqual(self.cs.tracks[0].indexes, [(1, 0)])

    def test_second_track(self):
        self.assertEqual(self.cs.tracks[1].track_number, 2)
        self.assertEqual(self.cs.tracks[1].start_offset, 44100)
        self.assertEqual(self.cs.tracks[1].isrc, b'')
        self.assertEqual(self.cs.tracks[1].type, 1)
        self.assertEqual(self.cs.tracks[1].pre_emphasis, True)
        self.assertEqual(self.cs.tracks[1].indexes, [(1, 0),
                                                         (2, 588)])

    def test_lead_out(self):
        self.assertEqual(self.cs.tracks[-1].track_number, 170)
        self.assertEqual(self.cs.tracks[-1].start_offset, 162496)
        self.assertEqual(self.cs.tracks[-1].isrc, b'')
        self.assertEqual(self.cs.tracks[-1].type, 0)
        self.assertEqual(self.cs.tracks[-1].pre_emphasis, False)
        self.assertEqual(self.cs.tracks[-1].indexes, [])

    def test_track_eq(self):
        track = self.cs.tracks[-1]
        self.assertReallyEqual(track, track)
        self.assertReallyNotEqual(track, 42)

    def test_eq(self):
        self.assertReallyEqual(self.cs, self.cs)

    def test_neq(self):
        self.assertReallyNotEqual(self.cs, 12)

    def test_repr(self):
        repr(self.cs)

    def test_roundtrip(self):
        self.assertEqual(CueSheet(self.cs.write()), self.cs)


class TPicture(TestCase):
    SAMPLE = os.path.join(DATA_DIR, "silence-44-s.flac")

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.p = self.flac.pictures[0]

    def test_count(self):
        self.assertEqual(len(self.flac.pictures), 1)

    def test_picture(self):
        self.assertEqual(self.p.width, 1)
        self.assertEqual(self.p.height, 1)
        self.assertEqual(self.p.depth, 24)
        self.assertEqual(self.p.colors, 0)
        self.assertEqual(self.p.mime, 'image/png')
        self.assertEqual(self.p.desc, 'A pixel.')
        self.assertEqual(self.p.type, 3)
        self.assertEqual(len(self.p.data), 150)

    def test_eq(self):
        self.assertEqual(self.p, self.p)

    def test_neq(self):
        self.assertNotEqual(self.p, 12)

    def test_repr(self):
        repr(self.p)

    def test_roundtrip(self):
        self.assertEqual(Picture(self.p.write()), self.p)


class TPadding(TestCase):

    def setUp(self):
        self.b = Padding(b"\x00" * 100)

    def test_padding(self):
        self.assertEqual(self.b.write(), b"\x00" * 100)

    def test_blank(self):
        self.assertFalse(Padding().write())

    def test_empty(self):
        self.assertFalse(Padding(b"").write())

    def test_repr(self):
        repr(Padding())

    def test_change(self):
        self.b.length = 20
        self.assertEqual(self.b.write(), b"\x00" * 20)


class TFLAC(TestCase):
    SAMPLE = os.path.join(DATA_DIR, "silence-44-s.flac")

    def setUp(self):
        self.NEW = get_temp_copy(self.SAMPLE)
        self.flac = FLAC(self.NEW)

    def tearDown(self):
        os.unlink(self.NEW)

    def test_zero_samples(self):
        # write back zero sample count and load again
        self.flac.info.total_samples = 0
        self.flac.save()
        new = FLAC(self.flac.filename)
        assert new.info.total_samples == 0
        assert new.info.bitrate == 0
        assert new.info.length == 0.0

    def test_bitrate(self):
        assert self.flac.info.bitrate == 101430
        old_file_size = os.path.getsize(self.flac.filename)
        self.flac.save(padding=lambda x: 9999)
        new_flac = FLAC(self.flac.filename)
        assert os.path.getsize(new_flac.filename) > old_file_size
        assert new_flac.info.bitrate == 101430

    def test_padding(self):
        for pad in [0, 42, 2**24 - 1, 2 ** 24]:
            self.flac.save(padding=lambda x: pad)
            new = FLAC(self.flac.filename)
            expected = min(2**24 - 1, pad)
            self.assertEqual(new.metadata_blocks[-1].length, expected)

    def test_save_multiple_padding(self):
        # we don't touch existing padding blocks on save, but will
        # replace them in the file with one at the end

        def num_padding(f):
            blocks = f.metadata_blocks
            return len([b for b in blocks if isinstance(b, Padding)])

        num_blocks = num_padding(self.flac)
        self.assertEqual(num_blocks, 1)
        block = Padding()
        block.length = 42
        self.flac.metadata_blocks.append(block)
        block = Padding()
        block.length = 24
        self.flac.metadata_blocks.append(block)
        self.flac.save()
        self.assertEqual(num_padding(self.flac), num_blocks + 2)

        new = FLAC(self.flac.filename)
        self.assertEqual(num_padding(new), 1)
        self.assertTrue(isinstance(new.metadata_blocks[-1], Padding))

    def test_increase_size_new_padding(self):
        self.assertEqual(self.flac.metadata_blocks[-1].length, 3060)
        value = "foo" * 100
        self.flac["foo"] = [value]
        self.flac.save()
        new = FLAC(self.NEW)
        self.assertEqual(new.metadata_blocks[-1].length, 2752)
        self.assertEqual(new["foo"], [value])

    def test_delete(self):
        self.assertTrue(self.flac.tags)
        self.flac.delete()
        self.assertTrue(self.flac.tags is not None)
        self.assertFalse(self.flac.tags)
        flac = FLAC(self.NEW)
        self.assertTrue(flac.tags is None)

    def test_delete_change_reload(self):
        self.flac.delete()
        self.flac.tags["FOO"] = ["BAR"]
        self.flac.save()
        assert FLAC(self.flac.filename)["FOO"] == ["BAR"]

        # same with delete failing due to IO etc.
        with pytest.raises(MutagenError):
            self.flac.delete(os.devnull)
        self.flac.tags["FOO"] = ["QUUX"]
        self.flac.save()
        assert FLAC(self.flac.filename)["FOO"] == ["QUUX"]

    def test_module_delete(self):
        delete(self.NEW)
        flac = FLAC(self.NEW)
        self.assertFalse(flac.tags)

    def test_info(self):
        self.assertAlmostEqual(FLAC(self.NEW).info.length, 3.7, 1)

    def test_keys(self):
        self.assertEqual(
            list(self.flac.keys()), list(self.flac.tags.keys()))

    def test_values(self):
        self.assertEqual(
            list(self.flac.values()), list(self.flac.tags.values()))

    def test_items(self):
        self.assertEqual(
            list(self.flac.items()), list(self.flac.tags.items()))

    def test_vc(self):
        self.assertEqual(self.flac['title'][0], 'Silence')

    def test_write_nochange(self):
        f = FLAC(self.NEW)
        f.save()
        with open(self.SAMPLE, "rb") as a, open(self.NEW, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_write_changetitle(self):
        f = FLAC(self.NEW)
        self.assertRaises(
            TypeError, f.__setitem__, b'title', b"A New Title")

    def test_write_changetitle_unicode_value(self):
        f = FLAC(self.NEW)
        self.assertRaises(
            TypeError, f.__setitem__, b'title', "A Unicode Title \u2022")

    def test_write_changetitle_unicode_key(self):
        f = FLAC(self.NEW)
        f["title"] = b"A New Title"
        self.assertRaises(ValueError, f.save)

    def test_write_changetitle_unicode_key_and_value(self):
        f = FLAC(self.NEW)
        f["title"] = "A Unicode Title \u2022"
        f.save()
        f = FLAC(self.NEW)
        self.assertEqual(f["title"][0], "A Unicode Title \u2022")

    def test_force_grow(self):
        f = FLAC(self.NEW)
        f["faketag"] = ["a" * 1000] * 1000
        f.save()
        f = FLAC(self.NEW)
        self.assertEqual(f["faketag"], ["a" * 1000] * 1000)

    def test_force_shrink(self):
        self.test_force_grow()
        f = FLAC(self.NEW)
        f["faketag"] = "foo"
        f.save()
        f = FLAC(self.NEW)
        self.assertEqual(f["faketag"], ["foo"])

    def test_add_vc(self):
        f = FLAC(os.path.join(DATA_DIR, "no-tags.flac"))
        self.assertFalse(f.tags)
        f.add_tags()
        self.assertTrue(f.tags == [])
        self.assertRaises(ValueError, f.add_tags)

    def test_add_vc_implicit(self):
        f = FLAC(os.path.join(DATA_DIR, "no-tags.flac"))
        self.assertFalse(f.tags)
        f["foo"] = "bar"
        self.assertTrue(f.tags == [("foo", "bar")])
        self.assertRaises(ValueError, f.add_tags)

    def test_ooming_vc_header(self):
        # issue 112: Malformed FLAC Vorbis header causes out of memory error
        # https://github.com/quodlibet/mutagen/issues/112
        self.assertRaises(error, FLAC, os.path.join(DATA_DIR,
                                                    'ooming-header.flac'))

    def test_with_real_flac(self):
        if not have_flac:
            return
        self.flac["faketag"] = "foobar" * 1000
        self.flac.save()
        self.assertFalse(call_flac("-t", self.flac.filename) != 0)

    def test_save_unknown_block(self):
        block = MetadataBlock(b"test block data")
        block.code = 99
        self.flac.metadata_blocks.append(block)
        self.flac.save()

    def test_load_unknown_block(self):
        self.test_save_unknown_block()
        flac = FLAC(self.NEW)
        self.assertEqual(len(flac.metadata_blocks), 7)
        self.assertEqual(flac.metadata_blocks[5].code, 99)
        self.assertEqual(flac.metadata_blocks[5].data, b"test block data")

    def test_two_vorbis_blocks(self):
        self.flac.metadata_blocks.append(self.flac.metadata_blocks[1])
        self.flac.save()
        self.assertRaises(error, FLAC, self.NEW)

    def test_missing_streaminfo(self):
        self.flac.metadata_blocks.pop(0)
        self.flac.save()
        self.assertRaises(error, FLAC, self.NEW)

    def test_load_invalid_flac(self):
        self.assertRaises(
            error, FLAC, os.path.join(DATA_DIR, "xing.mp3"))

    def test_save_invalid_flac(self):
        self.assertRaises(
            error, self.flac.save, os.path.join(DATA_DIR, "xing.mp3"))

    def test_pprint(self):
        self.assertTrue(self.flac.pprint())

    def test_double_load(self):
        blocks = list(self.flac.metadata_blocks)
        self.flac.load(self.flac.filename)
        self.assertEqual(blocks, self.flac.metadata_blocks)

    def test_seektable(self):
        self.assertTrue(self.flac.seektable)

    def test_cuesheet(self):
        self.assertTrue(self.flac.cuesheet)

    def test_pictures(self):
        self.assertTrue(self.flac.pictures)

    def test_add_picture(self):
        f = FLAC(self.NEW)
        c = len(f.pictures)
        f.add_picture(Picture())
        f.save()
        f = FLAC(self.NEW)
        self.assertEqual(len(f.pictures), c + 1)

    def test_clear_pictures(self):
        f = FLAC(self.NEW)
        c1 = len(f.pictures)
        c2 = len(f.metadata_blocks)
        f.clear_pictures()
        f.save()
        f = FLAC(self.NEW)
        self.assertEqual(len(f.metadata_blocks), c2 - c1)

    def test_ignore_id3(self):
        id3 = ID3()
        id3.add(TIT2(encoding=0, text='id3 title'))
        id3.save(self.NEW)
        f = FLAC(self.NEW)
        f['title'] = 'vc title'
        f.save()
        id3 = ID3(self.NEW)
        self.assertEqual(id3['TIT2'].text, ['id3 title'])
        f = FLAC(self.NEW)
        self.assertEqual(f['title'], ['vc title'])

    def test_delete_id3(self):
        id3 = ID3()
        id3.add(TIT2(encoding=0, text='id3 title'))
        id3.save(self.NEW, v1=2)
        f = FLAC(self.NEW)
        f['title'] = 'vc title'
        f.save(deleteid3=True)
        self.assertRaises(ID3NoHeaderError, ID3, self.NEW)
        f = FLAC(self.NEW)
        self.assertEqual(f['title'], ['vc title'])

    def test_save_on_mp3(self):
        path = os.path.join(DATA_DIR, "silence-44-s.mp3")
        self.assertRaises(error, self.flac.save, path)

    def test_mime(self):
        self.assertTrue("audio/x-flac" in self.flac.mime)

    def test_variable_block_size(self):
        FLAC(os.path.join(DATA_DIR, "variable-block.flac"))

    def test_load_flac_with_application_block(self):
        FLAC(os.path.join(DATA_DIR, "flac_application.flac"))


class TFLACFile(TestCase):

    def test_open_nonexistant(self):
        """mutagen 1.2 raises UnboundLocalError, then it tries to open
        non-existent FLAC files"""
        filename = os.path.join(DATA_DIR, "doesntexist.flac")
        self.assertRaises(MutagenError, FLAC, filename)


class TFLACBadBlockSize(TestCase):
    TOO_SHORT = os.path.join(DATA_DIR, "52-too-short-block-size.flac")
    TOO_SHORT_2 = os.path.join(DATA_DIR, "106-short-picture-block-size.flac")
    OVERWRITTEN = os.path.join(DATA_DIR, "52-overwritten-metadata.flac")
    INVAL_INFO = os.path.join(DATA_DIR, "106-invalid-streaminfo.flac")

    def test_too_short_read(self):
        flac = FLAC(self.TOO_SHORT)
        self.assertEqual(flac["artist"], ["Tunng"])

    def test_too_short_read_picture(self):
        flac = FLAC(self.TOO_SHORT_2)
        self.assertEqual(flac.pictures[0].width, 10)

    def test_overwritten_read(self):
        flac = FLAC(self.OVERWRITTEN)
        self.assertEqual(flac["artist"], ["Giora Feidman"])

    def test_inval_streaminfo(self):
        self.assertRaises(error, FLAC, self.INVAL_INFO)


class TFLACBadBlockSizeWrite(TestCase):
    TOO_SHORT = os.path.join(DATA_DIR, "52-too-short-block-size.flac")

    def setUp(self):
        self.NEW = get_temp_copy(self.TOO_SHORT)

    def tearDown(self):
        os.unlink(self.NEW)

    def test_write_reread(self):
        flac = FLAC(self.NEW)
        del flac["artist"]
        flac.save()
        flac2 = FLAC(self.NEW)
        self.assertEqual(flac["title"], flac2["title"])
        with open(self.NEW, "rb") as h:
            data = h.read(1024)
        self.assertFalse(b"Tunng" in data)


class TFLACBadDuplicateVorbisComment(TestCase):

    def setUp(self):
        self.filename = get_temp_copy(
            os.path.join(DATA_DIR, "silence-44-s.flac"))

        # add a second vorbis comment block to the file right after the first
        some_tags = VCFLACDict()
        some_tags["DUPLICATE"] = ["SECOND"]
        f = FLAC(self.filename)
        f.tags["DUPLICATE"] = ["FIRST"]
        assert f.tags is f.metadata_blocks[2]
        f.metadata_blocks.insert(3, some_tags)
        f.save()

    def tearDown(self):
        os.unlink(self.filename)

    def test_load_multiple(self):
        # on load always use the first one, like metaflac
        f = FLAC(self.filename)
        assert f["DUPLICATE"] == ["FIRST"]
        assert f.metadata_blocks[2] is f.tags
        assert f.metadata_blocks[3]["DUPLICATE"] == ["SECOND"]

        # save in the same order
        f.save()
        f = FLAC(self.filename)
        assert f["DUPLICATE"] == ["FIRST"]

    def test_delete_multiple(self):
        # on delete we delete both
        f = FLAC(self.filename)
        f.delete()
        assert len(f.tags) == 0
        f = FLAC(self.filename)
        assert f.tags is None

    def test_delete_multiple_fail(self):
        f = FLAC(self.filename)
        with pytest.raises(MutagenError):
            f.delete(os.devnull)
        f.save()

        # if delete failed we shouldn't see a difference
        f = FLAC(self.filename)
        assert f.metadata_blocks[2] is f.tags
        assert f.metadata_blocks[3].code == f.tags.code


class TFLACBadBlockSizeOverflow(TestCase):

    def setUp(self):
        self.filename = get_temp_copy(
            os.path.join(DATA_DIR, "silence-44-s.flac"))

    def tearDown(self):
        os.unlink(self.filename)

    def test_largest_valid(self):
        f = FLAC(self.filename)
        pic = Picture()
        pic.data = b"\x00" * (2 ** 24 - 1 - 32)
        self.assertEqual(len(pic.write()), 2 ** 24 - 1)
        f.add_picture(pic)
        f.save()

    def test_smallest_invalid(self):
        f = FLAC(self.filename)
        pic = Picture()
        pic.data = b"\x00" * (2 ** 24 - 32)
        f.add_picture(pic)
        self.assertRaises(error, f.save)

    def test_invalid_overflow_recover_and_save_back(self):
        # save a picture which is too large for flac, but still write it
        # with a wrong block size
        f = FLAC(self.filename)
        f.clear_pictures()
        pic = Picture()
        pic.data = b"\x00" * (2 ** 24 - 32)
        pic._invalid_overflow_size = 42
        f.add_picture(pic)
        f.save()

        # make sure we can read it and save it again
        f = FLAC(self.filename)
        self.assertTrue(f.pictures)
        self.assertEqual(len(f.pictures[0].data), 2 ** 24 - 32)
        f.save()


have_flac = True
try:
    call_flac()
except OSError:
    have_flac = False
    print("WARNING: Skipping FLAC reference tests.")
