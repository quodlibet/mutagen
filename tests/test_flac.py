
import shutil, os
from tests import TestCase, add
from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from mutagen.flac import to_int_be, Padding, VCFLACDict, MetadataBlock
from mutagen.flac import StreamInfo, SeekTable, CueSheet, FLAC, delete, Picture
from tests.test__vorbis import TVCommentDict, VComment
try: from os.path import devnull
except ImportError: devnull = "/dev/null"

class Tto_int_be(TestCase):
    uses_mmap = False

    def test_empty(self): self.failUnlessEqual(to_int_be(""), 0)
    def test_0(self): self.failUnlessEqual(to_int_be("\x00"), 0)
    def test_1(self): self.failUnlessEqual(to_int_be("\x01"), 1)
    def test_256(self): self.failUnlessEqual(to_int_be("\x01\x00"), 256)
    def test_long(self):
        self.failUnlessEqual(to_int_be("\x01\x00\x00\x00\x00"), 2**32)
add(Tto_int_be)

class TVCFLACDict(TVCommentDict):
    uses_mmap = False

    Kind = VCFLACDict

    def test_roundtrip_vc(self):
        self.failUnlessEqual(self.c, VComment(self.c.write() + "\x01"))
add(TVCFLACDict)

class TMetadataBlock(TestCase):
    uses_mmap = False

    def test_empty(self):
        self.failUnlessEqual(MetadataBlock("").write(), "")
    def test_not_empty(self):
        self.failUnlessEqual(MetadataBlock("foobar").write(), "foobar")

    def test_change(self):
        b = MetadataBlock("foobar")
        b.data = "quux"
        self.failUnlessEqual(b.write(), "quux")

    def test_writeblocks(self):
        blocks = [Padding("\x00" * 20), Padding("\x00" * 30)]
        self.failUnlessEqual(len(MetadataBlock.writeblocks(blocks)), 58)

    def test_ctr_garbage(self):
        self.failUnlessRaises(TypeError, StreamInfo, 12)

    def test_group_padding(self):
        blocks = [Padding("\x00" * 20), Padding("\x00" * 30),
                  MetadataBlock("foobar")]
        blocks[-1].code = 0
        length1 = len(MetadataBlock.writeblocks(blocks))
        MetadataBlock.group_padding(blocks)
        length2 = len(MetadataBlock.writeblocks(blocks))
        self.failUnlessEqual(length1, length2)
        self.failUnlessEqual(len(blocks), 2)
add(TMetadataBlock)

class TStreamInfo(TestCase):
    uses_mmap = False

    data = ('\x12\x00\x12\x00\x00\x00\x0e\x005\xea\n\xc4H\xf0\x00\xca0'
            '\x14(\x90\xf9\xe1)2\x13\x01\xd4\xa7\xa9\x11!8\xab\x91')

    def setUp(self):
        self.i = StreamInfo(self.data)

    def test_blocksize(self):
        self.failUnlessEqual(self.i.max_blocksize, 4608)
        self.failUnlessEqual(self.i.min_blocksize, 4608)
        self.failUnless(self.i.min_blocksize <= self.i.max_blocksize)
    def test_framesize(self):
        self.failUnlessEqual(self.i.min_framesize, 14)
        self.failUnlessEqual(self.i.max_framesize, 13802)
        self.failUnless(self.i.min_framesize <= self.i.max_framesize)
    def test_sample_rate(self): self.failUnlessEqual(self.i.sample_rate, 44100)
    def test_channels(self): self.failUnlessEqual(self.i.channels, 5)
    def test_bps(self): self.failUnlessEqual(self.i.bits_per_sample, 16)
    def test_length(self): self.failUnlessAlmostEqual(self.i.length, 300.5, 1)
    def test_total_samples(self):
        self.failUnlessEqual(self.i.total_samples, 13250580)
    def test_md5_signature(self):
        self.failUnlessEqual(self.i.md5_signature,
                             int("2890f9e129321301d4a7a9112138ab91", 16))
    def test_eq(self): self.failUnlessEqual(self.i, self.i)
    def test_roundtrip(self):
        self.failUnlessEqual(StreamInfo(self.i.write()), self.i)
add(TStreamInfo)
        
class TSeekTable(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    uses_mmap = False

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.st = self.flac.seektable
    def test_seektable(self):
        self.failUnlessEqual(self.st.seekpoints,
                             [(0, 0, 4608),
                              (41472, 11852, 4608),
                              (50688, 14484, 4608),
                              (87552, 25022, 4608),
                              (105984, 30284, 4608),
                              (0xFFFFFFFFFFFFFFFF, 0, 0)])
    def test_eq(self): self.failUnlessEqual(self.st, self.st)
    def test_neq(self): self.failIfEqual(self.st, 12)
    def test_repr(self): repr(self.st)
    def test_roundtrip(self):
        self.failUnlessEqual(SeekTable(self.st.write()), self.st)
add(TSeekTable)

class TCueSheet(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    uses_mmap = False

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.cs = self.flac.cuesheet
    def test_cuesheet(self):
        self.failUnlessEqual(self.cs.media_catalog_number, "1234567890123")
        self.failUnlessEqual(self.cs.lead_in_samples, 88200)
        self.failUnlessEqual(self.cs.compact_disc, True)
        self.failUnlessEqual(len(self.cs.tracks), 4)
    def test_first_track(self):
        self.failUnlessEqual(self.cs.tracks[0].track_number, 1)
        self.failUnlessEqual(self.cs.tracks[0].start_offset, 0)
        self.failUnlessEqual(self.cs.tracks[0].isrc, '123456789012')
        self.failUnlessEqual(self.cs.tracks[0].type, 0)
        self.failUnlessEqual(self.cs.tracks[0].pre_emphasis, False)
        self.failUnlessEqual(self.cs.tracks[0].indexes, [(1, 0)])
    def test_second_track(self):
        self.failUnlessEqual(self.cs.tracks[1].track_number, 2)
        self.failUnlessEqual(self.cs.tracks[1].start_offset, 44100L)
        self.failUnlessEqual(self.cs.tracks[1].isrc, '')
        self.failUnlessEqual(self.cs.tracks[1].type, 1)
        self.failUnlessEqual(self.cs.tracks[1].pre_emphasis, True)
        self.failUnlessEqual(self.cs.tracks[1].indexes, [(1, 0),
                                                         (2, 588)])
    def test_lead_out(self):
        self.failUnlessEqual(self.cs.tracks[-1].track_number, 170)
        self.failUnlessEqual(self.cs.tracks[-1].start_offset, 162496)
        self.failUnlessEqual(self.cs.tracks[-1].isrc, '')
        self.failUnlessEqual(self.cs.tracks[-1].type, 0)
        self.failUnlessEqual(self.cs.tracks[-1].pre_emphasis, False)
        self.failUnlessEqual(self.cs.tracks[-1].indexes, [])
    def test_eq(self): self.failUnlessEqual(self.cs, self.cs)
    def test_neq(self): self.failIfEqual(self.cs, 12)
    def test_repr(self): repr(self.cs)
    def test_roundtrip(self):
        self.failUnlessEqual(CueSheet(self.cs.write()), self.cs)
add(TCueSheet)

class TPicture(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    uses_mmap = False

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.p = self.flac.pictures[0]
    def test_count(self):
        self.failUnlessEqual(len(self.flac.pictures), 1)
    def test_picture(self):
        self.failUnlessEqual(self.p.width, 1)
        self.failUnlessEqual(self.p.height, 1)
        self.failUnlessEqual(self.p.depth, 24)
        self.failUnlessEqual(self.p.colors, 0)
        self.failUnlessEqual(self.p.mime, u'image/png')
        self.failUnlessEqual(self.p.desc, u'A pixel.')
        self.failUnlessEqual(self.p.type, 3)
        self.failUnlessEqual(len(self.p.data), 150)
    def test_eq(self): self.failUnlessEqual(self.p, self.p)
    def test_neq(self): self.failIfEqual(self.p, 12)
    def test_repr(self): repr(self.p)
    def test_roundtrip(self):
        self.failUnlessEqual(Picture(self.p.write()), self.p)
add(TPicture)

class TPadding(TestCase):
    uses_mmap = False

    def setUp(self): self.b = Padding("\x00" * 100)
    def test_padding(self): self.failUnlessEqual(self.b.write(), "\x00" * 100)
    def test_blank(self): self.failIf(Padding().write())
    def test_empty(self): self.failIf(Padding("").write())
    def test_repr(self): repr(Padding())
    def test_change(self):
        self.b.length = 20
        self.failUnlessEqual(self.b.write(), "\x00" * 20)
add(TPadding)

class TFLAC(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    NEW = SAMPLE + ".new"
    def setUp(self):
        shutil.copy(self.SAMPLE, self.NEW)
        self.failUnlessEqual(file(self.SAMPLE).read(), file(self.NEW).read())
        self.flac = FLAC(self.NEW)

    def test_delete(self):
        self.failUnless(self.flac.tags)
        self.flac.delete()
        self.failIf(self.flac.tags)
        flac = FLAC(self.NEW)
        self.failIf(flac.tags)

    def test_module_delete(self):
        delete(self.NEW)
        flac = FLAC(self.NEW)
        self.failIf(flac.tags)

    def test_info(self):
        self.failUnlessAlmostEqual(FLAC(self.NEW).info.length, 3.7, 1)

    def test_keys(self):
        self.failUnlessEqual(self.flac.keys(), self.flac.tags.keys())

    def test_values(self):
        self.failUnlessEqual(self.flac.values(), self.flac.tags.values())

    def test_items(self):
        self.failUnlessEqual(self.flac.items(), self.flac.tags.items())

    def test_vc(self):
        self.failUnlessEqual(self.flac['title'][0], 'Silence')

    def test_write_nochange(self):
        f = FLAC(self.NEW)
        f.save()
        self.failUnlessEqual(file(self.SAMPLE).read(), file(self.NEW).read())

    def test_write_changetitle(self):
        f = FLAC(self.NEW)
        f["title"] = "A New Title"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["title"][0], "A New Title")

    def test_write_changetitle_unicode_value(self):
        f = FLAC(self.NEW)
        f["title"] = u"A Unicode Title \u2022"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["title"][0], u"A Unicode Title \u2022")

    def test_write_changetitle_unicode_key(self):
        f = FLAC(self.NEW)
        f[u"title"] = "A New Title"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f[u"title"][0], "A New Title")

    def test_write_changetitle_unicode_key_and_value(self):
        f = FLAC(self.NEW)
        f[u"title"] = u"A Unicode Title \u2022"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f[u"title"][0], u"A Unicode Title \u2022")

    def test_force_grow(self):
        f = FLAC(self.NEW)
        f["faketag"] = ["a" * 1000] * 1000
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["faketag"], ["a" * 1000] * 1000)

    def test_force_shrink(self):
        self.test_force_grow()
        f = FLAC(self.NEW)
        f["faketag"] = "foo"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["faketag"], ["foo"])

    def test_add_vc(self):
        f = FLAC(os.path.join("tests", "data", "no-tags.flac"))
        self.failIf(f.tags)
        f.add_tags()
        self.failUnless(f.tags == [])
        self.failUnlessRaises(ValueError, f.add_tags)

    def test_add_vc_implicit(self):
        f = FLAC(os.path.join("tests", "data", "no-tags.flac"))
        self.failIf(f.tags)
        f["foo"] = "bar"
        self.failUnless(f.tags == [("foo", "bar")])
        self.failUnlessRaises(ValueError, f.add_tags)

    def test_with_real_flac(self):
        if not have_flac: return
        self.flac["faketag"] = "foobar" * 1000
        self.flac.save()
        badval = os.system("tools/notarealprogram 2> %s" % devnull)
        value = os.system("flac -t %s 2> %s" % (self.flac.filename, devnull))
        self.failIf(value and value != badval)

    def test_save_unknown_block(self):
        block = MetadataBlock("test block data")
        block.code = 99
        self.flac.metadata_blocks.append(block)
        self.flac.save()

    def test_load_unknown_block(self):
        self.test_save_unknown_block()
        flac = FLAC(self.NEW)
        self.failUnlessEqual(len(flac.metadata_blocks), 7)
        self.failUnlessEqual(flac.metadata_blocks[5].code, 99)
        self.failUnlessEqual(flac.metadata_blocks[5].data, "test block data")

    def test_two_vorbis_blocks(self):
        self.flac.metadata_blocks.append(self.flac.metadata_blocks[1])
        self.flac.save()
        self.failUnlessRaises(IOError, FLAC, self.NEW)

    def test_missing_streaminfo(self):
        self.flac.metadata_blocks.pop(0)
        self.flac.save()
        self.failUnlessRaises(IOError, FLAC, self.NEW)

    def test_load_invalid_flac(self):
        self.failUnlessRaises(
            IOError, FLAC, os.path.join("tests", "data", "xing.mp3"))

    def test_save_invalid_flac(self):
        self.failUnlessRaises(
            IOError, self.flac.save, os.path.join("tests", "data", "xing.mp3"))

    def test_pprint(self):
        self.failUnless(self.flac.pprint())

    def test_double_load(self):
        blocks = list(self.flac.metadata_blocks)
        self.flac.load(self.flac.filename)
        self.failUnlessEqual(blocks, self.flac.metadata_blocks)

    def test_seektable(self):
        self.failUnless(self.flac.seektable)

    def test_cuesheet(self):
        self.failUnless(self.flac.cuesheet)

    def test_pictures(self):
        self.failUnless(self.flac.pictures)

    def test_add_picture(self):
        f = FLAC(self.NEW)
        c = len(f.pictures)
        f.add_picture(Picture())
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(len(f.pictures), c + 1)

    def test_clear_pictures(self):
        f = FLAC(self.NEW)
        c1 = len(f.pictures)
        c2 = len(f.metadata_blocks)
        f.clear_pictures()
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(len(f.metadata_blocks), c2 - c1)

    def test_ignore_id3(self):
        id3 = ID3()
        id3.add(TIT2(encoding=0, text='id3 title'))
        id3.save(self.NEW)
        f = FLAC(self.NEW)
        f['title'] = 'vc title'
        f.save()
        id3 = ID3(self.NEW)
        self.failUnlessEqual(id3['TIT2'].text, ['id3 title'])
        f = FLAC(self.NEW)
        self.failUnlessEqual(f['title'], ['vc title'])

    def test_delete_id3(self):
        id3 = ID3()
        id3.add(TIT2(encoding=0, text='id3 title'))
        id3.save(self.NEW, v1=2)
        f = FLAC(self.NEW)
        f['title'] = 'vc title'
        f.save(deleteid3=True)
        self.failUnlessRaises(ID3NoHeaderError, ID3, self.NEW)
        f = FLAC(self.NEW)
        self.failUnlessEqual(f['title'], ['vc title'])

    def test_mime(self):
        self.failUnless("audio/x-flac" in self.flac.mime)

    def test_variable_block_size(self):
        FLAC(os.path.join("tests", "data", "variable-block.flac"))

    def tearDown(self):
        os.unlink(self.NEW)

add(TFLAC)

class TFLACFile(TestCase):
    uses_mmap = False

    def test_open_nonexistant(self):
        """mutagen 1.2 raises UnboundLocalError, then it tries to open
        non-existant FLAC files"""
        filename = os.path.join("tests", "data", "doesntexist.flac")
        self.assertRaises(IOError, FLAC, filename)

add(TFLACFile)

class CVE20074619(TestCase):
    uses_mmap = True

    # Tests to ensure Mutagen is not vulnerable to a number of security
    # issues found in libFLAC.
    # http://research.eeye.com/html/advisories/published/AD20071115.html

    def test_1(self):
        # "Editing any Metadata Block Size value to a large value such
        # as 0xFFFFFFFF may result in a heap based overflow in the
        # decoding software."
        filename = os.path.join("tests", "data", "CVE-2007-4619-1.flac")
        self.failUnlessRaises(IOError, FLAC, filename)

    def test_2(self):
        # "The second vulnerability lies within the parsing of any
        # VORBIS Comment String Size fields. Settings this fields to
        # an overly large size, such as 0xFFFFFFF, could also result
        # in another heap-based overflow allowing arbitrary code to
        # execute in the content of the decoding program."
        filename = os.path.join("tests", "data", "CVE-2007-4619-2.flac")
        self.failUnlessRaises(IOError, FLAC, filename)

    # "By inserting an overly long VORBIS Comment data string along
    # with an large VORBIS Comment data string size value (such as
    # 0x000061A8 followed by 25,050 A's), applications that do not
    # properly apply boundary checks will result in a stack-based
    # buffer overflow."
    #
    # This is tested, among other places, in
    # test_save_grown_split_setup_packet_reference which saves a
    # comment field of 200K in size.

    # Vulnerabilities 4-10 are the same thing for the picture block.

    # Vulnerability 11 does not apply to Mutagen as it does not
    # download images when given a redirect MIME type.

    # "An overly large Padding length field value would set the basis
    # for another heap overflow inside a vulnerable application. By
    # setting this value to a large value such as 0xFFFFFFFF, a
    # malformed FLAC file could cause a heap based corruption scenario
    # when the memory for the Padding length is calculated without
    # proper bounds checks."
    # 
    # We should raise an IOError when trying to write such large
    # blocks, or when reading blocks with an incorrect padding length.
    # Although, I do wonder about the correctness of this
    # vulnerability, since a padding length of 0xFFFFFFFF is
    # impossible to store in a FLAC file.

    def test_12_read(self):
        filename = os.path.join("tests", "data", "CVE-2007-4619-12.flac")
        self.failUnlessRaises(IOError, FLAC, filename)

    def test_12_write_too_big(self):
        filename = os.path.join("tests", "data", "silence-44-s.flac")
        f = FLAC(filename)
        # This size is too big to be an integer.
        f.metadata_blocks[-1].length = 0xFFFFFFFFFFFFFFFF
        self.failUnlessRaises(IOError, f.metadata_blocks[-1].write)

    def test_12_write_too_big_for_flac(self):
        from mutagen.flac import MetadataBlock
        filename = os.path.join("tests", "data", "silence-44-s.flac")
        f = FLAC(filename)
        # This size is too big to be in a FLAC block but is overwise fine.
        f.metadata_blocks[-1].length = 0x1FFFFFF
        self.failUnlessRaises(
            IOError, MetadataBlock.writeblocks, [f.metadata_blocks[-1]])

    # Vulnerability 13 and 14 are specific to libFLAC and C/C++ memory
    # management schemes.

add(CVE20074619)

NOTFOUND = os.system("tools/notarealprogram 2> %s" % devnull)

have_flac = True
if os.system("flac 2> %s > %s" % (devnull, devnull)) == NOTFOUND:
    have_flac = False
    print "WARNING: Skipping FLAC reference tests."
