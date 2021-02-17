
import os

from mutagen._riff import RiffFile, RiffChunk

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
        self.failUnless(isinstance(self.riff_1[u'fmt'], RiffChunk))
        self.failUnless(isinstance(self.riff_1[u'data'], RiffChunk))
        self.failUnless(isinstance(self.riff_1[u'id3'], RiffChunk))

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
        self.failUnless(isinstance(new_riff[u'id3'], RiffChunk))
        self.failUnlessEqual(new_riff[u'id3'].size, 8)
        self.failUnlessEqual(new_riff[u'id3'].data_size, 0)

    def test_insert_padded_chunks(self):
        padded = self.riff_2_tmp.insert_chunk(u'TST1')
        unpadded = self.riff_2_tmp.insert_chunk(u'TST2')
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
        riff_file = self.riff_2_tmp
        self.failUnlessEqual(riff_file.root.size, 64044)
        riff_file.insert_chunk(u'TST')
        # Resize to odd length, should insert 1 padding byte
        riff_file[u'TST'].resize(3)
        # Insert another chunk after the first one
        self.failUnlessEqual(riff_file.root.size, 64056)
        riff_file.insert_chunk(u'TST2')
        riff_file[u'TST2'].resize(2)
        self.failUnlessEqual(riff_file.root.size, 64066)
        self.failUnlessEqual(riff_file[u'TST'].size, 12)
        self.failUnlessEqual(riff_file[u'TST'].data_size, 3)
        self.failUnlessEqual(riff_file[u'TST'].data_offset, 64052)
        self.failUnlessEqual(riff_file[u'TST2'].size, 10)
        self.failUnlessEqual(riff_file[u'TST2'].data_size, 2)
        self.failUnlessEqual(riff_file[u'TST2'].data_offset, 64064)
        # Delete the odd chunk
        riff_file.delete_chunk(u'TST')
        self.failUnlessEqual(riff_file.root.size, 64054)
        self.failUnlessEqual(riff_file[u'TST2'].size, 10)
        self.failUnlessEqual(riff_file[u'TST2'].data_size, 2)
        self.failUnlessEqual(riff_file[u'TST2'].data_offset, 64052)
        # Reloading the file should give the same results
        new_riff_file = RiffFile(self.file_2_tmp)
        self.failUnlessEqual(new_riff_file.root.size,
                             riff_file.root.size)
        self.failUnlessEqual(new_riff_file[u'TST2'].size,
            riff_file[u'TST2'].size)
        self.failUnlessEqual(new_riff_file[u'TST2'].data_size,
            riff_file[u'TST2'].data_size)
        self.failUnlessEqual(new_riff_file[u'TST2'].data_offset,
            riff_file[u'TST2'].data_offset)

    def test_read_list_info(self):
        riff = self.riff_1_tmp
        info = riff[u'LIST']
        self.failUnlessEqual(info.name, 'INFO')
        info_tags = {}
        for chunk in info.subchunks():
            info_tags[chunk.id] = chunk.read().decode().strip('\0')
        self.failUnlessEqual(info_tags['IPRD'], 'Quod Libet Test Data')
        self.failUnlessEqual(info_tags['IART'], 'piman, jzig')
        self.failUnlessEqual(info_tags['IGNR'], 'Silence')
        self.failUnlessEqual(info_tags['INAM'], 'Silence')
        self.failUnlessEqual(info_tags['ITRK'], '02/10')
        self.failUnlessEqual(info_tags['ICRD'], '2004')
