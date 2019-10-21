# -*- coding: utf-8 -*-

import os

from mutagen._riff import RiffFile, RiffChunkHeader

from tests import TestCase, DATA_DIR, get_temp_copy


class TRiffFile(TestCase):
    has_tags = os.path.join(DATA_DIR, 'silence-2s-PCM-44100-16-ID3v23.wav')
    no_tags = os.path.join(DATA_DIR, 'silence-2s-PCM-16000-08-notags.wav')

    def setUp(self):
        self.file_1 = open(self.has_tags, 'rb')
        self.riff_1 = RiffFile(self.file_1)
        self.file_2 = open(self.no_tags, 'rb')
        self.riff_2 = RiffFile(self.file_2)

        self.tmp_1_name = get_temp_copy(self.has_tags)
        self.file_1_tmp = open(self.tmp_1_name, 'rb+')
        self.riff_1_tmp = RiffFile(self.file_1_tmp)

        self.tmp_2_name = get_temp_copy(self.no_tags)
        self.file_2_tmp = open(self.tmp_2_name, 'rb+')
        self.riff_2_tmp = RiffFile(self.file_2_tmp)

    def tearDown(self):
        self.file_1.close()
        self.file_2.close()
        self.file_1_tmp.close()
        self.file_2_tmp.close()
        os.unlink(self.tmp_1_name)
        os.unlink(self.tmp_2_name)

    def test_has_chunks(self):
        self.failUnless(u'fmt' in self.riff_1)
        self.failUnless(u'data' in self.riff_1)
        self.failUnless(u'id3' in self.riff_1)

        self.failUnless(u'fmt' in self.riff_2)
        self.failUnless(u'data' in self.riff_2)

    def test_is_chunks(self):
        self.failUnless(isinstance(self.riff_1[u'fmt'], RiffChunkHeader))
        self.failUnless(isinstance(self.riff_1[u'data'], RiffChunkHeader))
        self.failUnless(isinstance(self.riff_1[u'id3'], RiffChunkHeader))

    def test_chunk_size(self):
        self.failUnlessEqual(self.riff_1[u'data'].size, 352808)
        self.failUnlessEqual(self.riff_1[u'id3'].size, 376)
        self.failUnlessEqual(self.riff_2[u'data'].size, 64008)

    def test_chunk_data_size(self):
        self.failUnlessEqual(self.riff_1[u'data'].data_size, 352800)
        self.failUnlessEqual(self.riff_1[u'id3'].data_size, 368)
        self.failUnlessEqual(self.riff_2[u'data'].data_size, 64000)

    def test_RIFF_chunk_resize(self):
        self.riff_1_tmp[u'data'].resize(17000)
        self.failUnlessEqual(
            RiffFile(self.file_1_tmp)[u'data'].data_size, 17000)
        self.riff_2_tmp[u'data'].resize(0)
        self.failUnlessEqual(RiffFile(self.file_2_tmp)[u'data'].data_size, 0)

    def test_insert_chunk(self):
        self.riff_2_tmp.insert_chunk(u'id3')

        new_riff = RiffFile(self.file_2_tmp)
        self.failUnless(u'id3' in new_riff)
        self.failUnless(isinstance(new_riff[u'id3'], RiffChunkHeader))
        self.failUnlessEqual(new_riff[u'id3'].size, 8)
        self.failUnlessEqual(new_riff[u'id3'].data_size, 0)

    def test_insert_padded_chunks(self):
        self.riff_2_tmp.insert_chunk(u'TST1')
        self.riff_2_tmp[u'TST1'].resize(3)
        self.failUnlessEqual(1, self.riff_2_tmp[u'TST1'].padding())
        self.riff_2_tmp.insert_chunk(u'TST2')
        self.riff_2_tmp[u'TST2'].resize(4)
        self.failUnlessEqual(0, self.riff_2_tmp[u'TST2'].padding())

    def test_delete_padded_chunks(self):
        self.riff_2_tmp.insert_chunk(u'TST1')
        # Resize to odd length, should insert 1 padding byte
        self.riff_2_tmp[u'TST1'].resize(3)
        # Insert another chunk after the first one
        new_riff = RiffFile(self.file_2_tmp)
        new_riff.insert_chunk(u'TST2')
        new_riff[u'TST2'].resize(2)
        new_riff = RiffFile(self.file_2_tmp)
        self.failUnlessEqual(new_riff[u'TST1'].size, 12)
        self.failUnlessEqual(new_riff[u'TST1'].data_size, 3)
        self.failUnlessEqual(new_riff[u'TST1'].data_offset, 64052)
        self.failUnlessEqual(new_riff[u'TST2'].size, 10)
        self.failUnlessEqual(new_riff[u'TST2'].data_size, 2)
        self.failUnlessEqual(new_riff[u'TST2'].data_offset, 64064)
        # Delete the odd chunk
        new_riff.delete_chunk(u'TST1')
        new_riff = RiffFile(self.file_2_tmp)
        self.failUnlessEqual(new_riff[u'TST2'].size, 10)
        self.failUnlessEqual(new_riff[u'TST2'].data_size, 2)
        self.failUnlessEqual(new_riff[u'TST2'].data_offset, 64052)
