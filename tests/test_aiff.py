
import os
from io import BytesIO

from mutagen.aiff import AIFF, AIFFInfo, delete, AIFFFile, AIFFChunk
from mutagen.aiff import error as AIFFError, read_float
from mutagen._iff import error as IffError

from tests import TestCase, DATA_DIR, get_temp_copy

import pytest


class TAIFF(TestCase):
    silence_1 = os.path.join(DATA_DIR, '11k-1ch-2s-silence.aif')
    silence_2 = os.path.join(DATA_DIR, '48k-2ch-s16-silence.aif')
    silence_3 = os.path.join(DATA_DIR, '8k-1ch-1s-silence.aif')
    silence_4 = os.path.join(DATA_DIR, '8k-1ch-3.5s-silence.aif')
    silence_5 = os.path.join(DATA_DIR, '8k-4ch-1s-silence.aif')

    has_tags = os.path.join(DATA_DIR, 'with-id3.aif')
    no_tags = os.path.join(DATA_DIR, '8k-1ch-1s-silence.aif')

    def setUp(self):
        self.filename_1 = get_temp_copy(self.has_tags)
        self.filename_2 = get_temp_copy(self.no_tags)

        self.aiff_tmp_id3 = AIFF(self.filename_1)
        self.aiff_tmp_no_id3 = AIFF(self.filename_2)

        self.aiff_1 = AIFF(self.silence_1)
        self.aiff_2 = AIFF(self.silence_2)
        self.aiff_3 = AIFF(self.silence_3)
        self.aiff_4 = AIFF(self.silence_4)
        self.aiff_5 = AIFF(self.silence_5)

    def test_read_float(self):
        assert read_float(b'@\x0b\xfa\x00\x00\x00\x00\x00\x00\x00') == 8000.0
        with pytest.raises(OverflowError):
            read_float(b"\xfa\x00\x00\xfa\x00\x00\x00\x00\x00\x00")
        with pytest.raises(OverflowError):
            read_float(b"\x7f\xff\x00\xfa\x00\x00\x00\x00\x00\x00")

    def test_channels(self):
        self.failUnlessEqual(self.aiff_1.info.channels, 1)
        self.failUnlessEqual(self.aiff_2.info.channels, 2)
        self.failUnlessEqual(self.aiff_3.info.channels, 1)
        self.failUnlessEqual(self.aiff_4.info.channels, 1)
        self.failUnlessEqual(self.aiff_5.info.channels, 4)

    def test_length(self):
        self.failUnlessEqual(self.aiff_1.info.length, 2)
        self.failUnlessEqual(self.aiff_2.info.length, 0.1)
        self.failUnlessEqual(self.aiff_3.info.length, 1)
        self.failUnlessEqual(self.aiff_4.info.length, 3.5)
        self.failUnlessEqual(self.aiff_5.info.length, 1)

    def test_bitrate(self):
        self.failUnlessEqual(self.aiff_1.info.bitrate, 176400)
        self.failUnlessEqual(self.aiff_2.info.bitrate, 1536000)
        self.failUnlessEqual(self.aiff_3.info.bitrate, 128000)
        self.failUnlessEqual(self.aiff_4.info.bitrate, 128000)
        self.failUnlessEqual(self.aiff_5.info.bitrate, 512000)

    def test_sample_rate(self):
        self.failUnlessEqual(self.aiff_1.info.sample_rate, 11025)
        self.failUnlessEqual(self.aiff_2.info.sample_rate, 48000)
        self.failUnlessEqual(self.aiff_3.info.sample_rate, 8000)
        self.failUnlessEqual(self.aiff_4.info.sample_rate, 8000)
        self.failUnlessEqual(self.aiff_5.info.sample_rate, 8000)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.aiff_1.info.bits_per_sample, 16)
        self.failUnlessEqual(self.aiff_2.info.bits_per_sample, 16)
        self.failUnlessEqual(self.aiff_3.info.bits_per_sample, 16)
        self.failUnlessEqual(self.aiff_4.info.bits_per_sample, 16)
        self.failUnlessEqual(self.aiff_5.info.bits_per_sample, 16)

    def test_sample_size(self):
        for test in [self.aiff_1, self.aiff_2, self.aiff_3, self.aiff_4,
                     self.aiff_5]:
            info = test.info
            self.failUnlessEqual(info.sample_size, info.bits_per_sample)

    def test_notaiff(self):
        self.failUnlessRaises(
            IffError, AIFF, os.path.join(DATA_DIR, 'empty.ofr'))

    def test_pprint(self):
        self.failUnless(self.aiff_1.pprint())
        self.failUnless(self.aiff_tmp_id3.pprint())

    def test_delete(self):
        self.aiff_tmp_id3.delete()
        self.failIf(self.aiff_tmp_id3.tags)
        self.failUnless(AIFF(self.filename_1).tags is None)

    def test_module_delete(self):
        delete(self.filename_1)
        self.failUnless(AIFF(self.filename_1).tags is None)

    def test_module_double_delete(self):
        delete(self.filename_1)
        delete(self.filename_1)

    def test_pprint_no_tags(self):
        self.aiff_tmp_id3.tags = None
        self.failUnless(self.aiff_tmp_id3.pprint())

    def test_save_no_tags(self):
        self.aiff_tmp_id3.tags = None
        self.aiff_tmp_id3.save()
        self.assertTrue(self.aiff_tmp_id3.tags is None)

    def test_add_tags_already_there(self):
        self.failUnless(self.aiff_tmp_id3.tags)
        self.failUnlessRaises(Exception, self.aiff_tmp_id3.add_tags)

    def test_mime(self):
        self.failUnless("audio/aiff" in self.aiff_1.mime)
        self.failUnless("audio/x-aiff" in self.aiff_1.mime)

    def test_loaded_tags(self):
        self.failUnless(self.aiff_tmp_id3["TIT2"] == "AIFF title")

    def test_roundtrip(self):
        self.failUnlessEqual(self.aiff_tmp_id3["TIT2"], ["AIFF title"])
        self.aiff_tmp_id3.save()
        new = AIFF(self.aiff_tmp_id3.filename)
        self.failUnlessEqual(new["TIT2"], ["AIFF title"])

    def test_save_tags(self):
        from mutagen.id3 import TIT1
        tags = self.aiff_tmp_id3.tags
        tags.add(TIT1(encoding=3, text="foobar"))
        tags.save()

        new = AIFF(self.aiff_tmp_id3.filename)
        self.failUnlessEqual(new["TIT1"], ["foobar"])

    def test_save_with_ID3_chunk(self):
        from mutagen.id3 import TIT1
        self.aiff_tmp_id3["TIT1"] = TIT1(encoding=3, text="foobar")
        self.aiff_tmp_id3.save()
        self.failUnless(AIFF(self.filename_1)["TIT1"] == "foobar")
        self.failUnless(self.aiff_tmp_id3["TIT2"] == "AIFF title")

    def test_save_without_ID3_chunk(self):
        from mutagen.id3 import TIT1
        self.aiff_tmp_no_id3["TIT1"] = TIT1(encoding=3, text="foobar")
        self.aiff_tmp_no_id3.save()
        self.failUnless(AIFF(self.filename_2)["TIT1"] == "foobar")

    def test_corrupt_tag(self):
        with open(self.filename_1, "r+b") as h:
            chunk = AIFFFile(h)[u'ID3']
            h.seek(chunk.data_offset)
            h.seek(4, 1)
            h.write(b"\xff\xff")
        self.assertRaises(AIFFError, AIFF, self.filename_1)

    def test_padding(self):
        AIFF(self.filename_1).save()
        self.assertEqual(AIFF(self.filename_1).tags._padding, 1002)
        AIFF(self.filename_1).save()
        self.assertEqual(AIFF(self.filename_1).tags._padding, 1002)

        tags = AIFF(self.filename_1)
        tags.save(padding=lambda x: 1)
        self.assertEqual(AIFF(self.filename_1).tags._padding, 1)

        tags = AIFF(self.filename_1)
        tags.save(padding=lambda x: 100)
        self.assertEqual(AIFF(self.filename_1).tags._padding, 100)

        tags = AIFF(self.filename_1)
        self.assertRaises(IffError, tags.save, padding=lambda x: -1)

    def tearDown(self):
        os.unlink(self.filename_1)
        os.unlink(self.filename_2)


class TAIFFInfo(TestCase):

    def test_empty(self):
        fileobj = BytesIO(b"")
        self.failUnlessRaises(IffError, AIFFInfo, fileobj)


class TAIFFFile(TestCase):
    has_tags = os.path.join(DATA_DIR, 'with-id3.aif')
    no_tags = os.path.join(DATA_DIR, '8k-1ch-1s-silence.aif')

    def setUp(self):
        self.file_1 = open(self.has_tags, 'rb')
        self.iff_1 = AIFFFile(self.file_1)
        self.file_2 = open(self.no_tags, 'rb')
        self.iff_2 = AIFFFile(self.file_2)

        self.tmp_1_name = get_temp_copy(self.has_tags)
        self.file_1_tmp = open(self.tmp_1_name, 'rb+')
        self.iff_1_tmp = AIFFFile(self.file_1_tmp)

        self.tmp_2_name = get_temp_copy(self.no_tags)
        self.file_2_tmp = open(self.tmp_2_name, 'rb+')
        self.iff_2_tmp = AIFFFile(self.file_2_tmp)

    def tearDown(self):
        self.file_1.close()
        self.file_2.close()
        self.file_1_tmp.close()
        self.file_2_tmp.close()
        os.unlink(self.tmp_1_name)
        os.unlink(self.tmp_2_name)

    def test_has_chunks(self):
        self.failUnless(u'FORM' in self.iff_1)
        self.failUnless(u'COMM' in self.iff_1)
        self.failUnless(u'SSND' in self.iff_1)
        self.failUnless(u'ID3' in self.iff_1)

        self.failUnless(u'FORM' in self.iff_2)
        self.failUnless(u'COMM' in self.iff_2)
        self.failUnless(u'SSND' in self.iff_2)

    def test_is_chunks(self):
        self.failUnless(isinstance(self.iff_1[u'FORM'], AIFFChunk))
        self.failUnless(isinstance(self.iff_1[u'COMM'], AIFFChunk))
        self.failUnless(isinstance(self.iff_1[u'SSND'], AIFFChunk))
        self.failUnless(isinstance(self.iff_1[u'ID3'], AIFFChunk))

    def test_chunk_size(self):
        self.failUnlessEqual(self.iff_1[u'FORM'].size, 17096)
        self.failUnlessEqual(self.iff_2[u'FORM'].size, 16054)

    def test_chunk_data_size(self):
        self.failUnlessEqual(self.iff_1[u'FORM'].data_size, 17088)
        self.failUnlessEqual(self.iff_2[u'FORM'].data_size, 16046)

    def test_FORM_chunk_resize(self):
        self.iff_1_tmp[u'FORM'].resize(17000)
        self.failUnlessEqual(
            AIFFFile(self.file_1_tmp)[u'FORM'].data_size, 17000)
        self.iff_2_tmp[u'FORM'].resize(4)
        self.failUnlessEqual(AIFFFile(self.file_2_tmp)[u'FORM'].data_size, 4)

    def test_child_chunk_resize(self):
        self.iff_1_tmp[u'ID3'].resize(128)

        id3 = self.iff_1_tmp[u'ID3']
        id3.write(b"\xff" * 128)
        self.assertEqual(id3.read(), b"\xff" * 128)

        self.failUnlessEqual(AIFFFile(self.file_1_tmp)[u'ID3'].data_size, 128)
        self.failUnlessEqual(
            AIFFFile(self.file_1_tmp)[u'FORM'].data_size, 16182)

    def test_chunk_delete(self):
        del self.iff_1_tmp[u'ID3']
        self.failIf(u'ID3' in self.iff_1_tmp)
        self.failIf(u'ID3' in AIFFFile(self.file_1_tmp))
        self.failUnlessEqual(AIFFFile(self.file_1_tmp)[u'FORM'].size, 16054)
        del self.iff_2_tmp[u'SSND']
        self.failIf(u'SSND' in self.iff_2_tmp)
        self.failIf(u'SSND' in AIFFFile(self.file_2_tmp))
        self.failUnlessEqual(AIFFFile(self.file_2_tmp)[u'FORM'].size, 38)

    def test_insert_chunk(self):
        self.iff_2_tmp.insert_chunk(u'ID3')

        new_iff = AIFFFile(self.file_2_tmp)
        self.failUnless(u'ID3' in new_iff)
        self.failUnless(isinstance(new_iff[u'ID3'], AIFFChunk))
        self.failUnlessEqual(new_iff[u'FORM'].size, 16062)
        self.failUnlessEqual(new_iff[u'FORM'].data_size, 16054)
        self.failUnlessEqual(new_iff[u'ID3'].size, 8)
        self.failUnlessEqual(new_iff[u'ID3'].data_size, 0)

    def test_insert_padded_chunks(self):
        padded = self.iff_2_tmp.insert_chunk(u'TST1')
        unpadded = self.iff_2_tmp.insert_chunk(u'TST2')
        # The second chunk needs no padding
        unpadded.resize(4)
        self.failUnlessEqual(4, unpadded.data_size)
        self.failUnlessEqual(0, unpadded.padding())
        self.failUnlessEqual(12, unpadded.size)
        # Resize the first chunk so it needs padding
        padded.resize(3)
        self.failUnlessEqual(3, padded.data_size)
        self.failUnlessEqual(1, padded.padding())
        self.failUnlessEqual(12, padded.size)
        self.failUnlessEqual(padded.offset + padded.size, unpadded.offset)
        # Verify the padding byte gets written correctly
        self.file_2_tmp.seek(padded.data_offset)
        self.file_2_tmp.write(b'ABCD')
        padded.write(b'ABC')
        self.file_2_tmp.seek(padded.data_offset)
        self.failUnlessEqual(b'ABC\x00', self.file_2_tmp.read(4))
        # Verify the second chunk got not overwritten
        self.file_2_tmp.seek(unpadded.offset)
        self.failUnlessEqual(b'TST2', self.file_2_tmp.read(4))

    def test_delete_padded_chunks(self):
        iff_file = self.iff_2_tmp
        iff_file.insert_chunk(u'TST')
        # Resize to odd length, should insert 1 padding byte
        iff_file[u'TST'].resize(3)
        # Insert another chunk after the first one
        iff_file.insert_chunk(u'TST2')
        iff_file[u'TST2'].resize(2)
        self.failUnlessEqual(iff_file[u'FORM'].size, 16076)
        self.failUnlessEqual(iff_file[u'FORM'].data_size, 16068)
        self.failUnlessEqual(iff_file[u'TST'].size, 12)
        self.failUnlessEqual(iff_file[u'TST'].data_size, 3)
        self.failUnlessEqual(iff_file[u'TST'].data_offset, 16062)
        self.failUnlessEqual(iff_file[u'TST2'].size, 10)
        self.failUnlessEqual(iff_file[u'TST2'].data_size, 2)
        self.failUnlessEqual(iff_file[u'TST2'].data_offset, 16074)
        # Delete the odd chunk
        iff_file.delete_chunk(u'TST')
        self.failUnlessEqual(iff_file[u'FORM'].size, 16064)
        self.failUnlessEqual(iff_file[u'FORM'].data_size, 16056)
        self.failUnlessEqual(iff_file[u'TST2'].size, 10)
        self.failUnlessEqual(iff_file[u'TST2'].data_size, 2)
        self.failUnlessEqual(iff_file[u'TST2'].data_offset, 16062)
        # Reloading the file should give the same results
        new_iff_file = AIFFFile(self.file_2_tmp)
        self.failUnlessEqual(new_iff_file[u'FORM'].size,
                             iff_file[u'FORM'].size)
        self.failUnlessEqual(new_iff_file[u'TST2'].size,
            iff_file[u'TST2'].size)
        self.failUnlessEqual(new_iff_file[u'TST2'].data_size,
            iff_file[u'TST2'].data_size)
        self.failUnlessEqual(new_iff_file[u'TST2'].data_offset,
            iff_file[u'TST2'].data_offset)
