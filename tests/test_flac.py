import shutil, os
from tests import TestCase, add
from mutagen.flac import to_int_be, Padding, VCFLACDict, MetadataBlock
from mutagen.flac import StreamInfo, FLAC
from tests.test__vorbis import TVCommentDict, VComment

class Tto_int_be(TestCase):
    def test_empty(self): self.failUnlessEqual(to_int_be(""), 0)
    def test_0(self): self.failUnlessEqual(to_int_be("\x00"), 0)
    def test_1(self): self.failUnlessEqual(to_int_be("\x01"), 1)
    def test_256(self): self.failUnlessEqual(to_int_be("\x01\x00"), 256)
    def test_long(self):
        self.failUnlessEqual(to_int_be("\x01\x00\x00\x00\x00"), 2**32)
add(Tto_int_be)

class TVCFLACDict(TVCommentDict):
    Kind = VCFLACDict

    def test_roundtrip_vc(self):
        self.failUnlessEqual(self.c, VComment(self.c.write() + "\x01"))
add(TVCFLACDict)

class TMetadataBlock(TestCase):
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
    data = ("\x12\x00\x12\x00\x00\x00\x0e\x00\x35\xea\x0a\xc4\x42\xf0"
            "\x00\xca\x30\x14\x28\x90\xf9\xe1\x29\x32\x13\x01\xd4\xa7"
            "\xa9\x11\x21\x38\xab\x91")
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
    def test_channels(self): self.failUnlessEqual(self.i.channels, 2)
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
        
class TPadding(TestCase):
    def setUp(self): self.b = Padding("\x00" * 100)
    def test_padding(self): self.failUnlessEqual(self.b.write(), "\x00" * 100)
    def test_blank(self): self.failIf(Padding().write())
    def test_empty(self): self.failIf(Padding("").write())
    def test_change(self):
        self.b.length = 20
        self.failUnlessEqual(self.b.write(), "\x00" * 20)
add(TPadding)

class TFLAC(TestCase):
    SAMPLE = "tests/data/silence-44-s.flac"
    NEW = SAMPLE + ".new"
    def setUp(self):
        shutil.copy(self.SAMPLE, self.NEW)
        self.failUnlessEqual(file(self.SAMPLE).read(), file(self.NEW).read())
        self.flac = FLAC(self.NEW)

    def test_info(self):
        self.failUnlessAlmostEqual(FLAC(self.NEW).info.length, 3.7, 1)

    def test_keys(self):
        self.failUnlessEqual(self.flac.keys(), self.flac.vc.keys())

    def test_values(self):
        self.failUnlessEqual(self.flac.values(), self.flac.vc.values())

    def test_items(self):
        self.failUnlessEqual(self.flac.items(), self.flac.vc.items())

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

    def test_force_grow(self):
        f = FLAC(self.NEW)
        f["faketag"] = ["a" * 1000] * 1000
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["faketag"][0], "a" * 1000)

    def test_add_vc(self):
        f = FLAC()
        self.failIf(f.vc)
        f.add_vorbiscomment()
        self.failUnless(f.vc == [])
        self.failUnlessRaises(ValueError, f.add_vorbiscomment)

    def test_add_vc_implicit(self):
        f = FLAC()
        self.failIf(f.vc)
        f["foo"] = "bar"
        self.failUnless(f.vc == [("foo", "bar")])
        self.failUnlessRaises(ValueError, f.add_vorbiscomment)

    def tearDown(self):
        os.unlink(self.NEW)

add(TFLAC)
