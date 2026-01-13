
import os

from mutagen._riff import RiffChunk, RiffFile
from tests import DATA_DIR, TestCase, get_temp_copy


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
        self.assertTrue('fmt' in self.riff_1)
        self.assertTrue('data' in self.riff_1)
        self.assertTrue('id3' in self.riff_1)

        self.assertTrue('fmt' in self.riff_2)
        self.assertTrue('data' in self.riff_2)

    def test_is_chunks(self):
        self.assertTrue(isinstance(self.riff_1['fmt'], RiffChunk))
        self.assertTrue(isinstance(self.riff_1['data'], RiffChunk))
        self.assertTrue(isinstance(self.riff_1['id3'], RiffChunk))

    def test_chunk_size(self):
        self.assertEqual(self.riff_1['data'].size, 352808)
        self.assertEqual(self.riff_1['id3'].size, 376)
        self.assertEqual(self.riff_2['data'].size, 64008)

    def test_chunk_data_size(self):
        self.assertEqual(self.riff_1['data'].data_size, 352800)
        self.assertEqual(self.riff_1['id3'].data_size, 368)
        self.assertEqual(self.riff_2['data'].data_size, 64000)

    def test_RIFF_chunk_resize(self):
        self.riff_1_tmp['data'].resize(17000)
        self.assertEqual(
            RiffFile(self.file_1_tmp)['data'].data_size, 17000)
        self.riff_2_tmp['data'].resize(0)
        self.assertEqual(RiffFile(self.file_2_tmp)['data'].data_size, 0)

    def test_insert_chunk(self):
        self.riff_2_tmp.insert_chunk('id3')

        new_riff = RiffFile(self.file_2_tmp)
        self.assertTrue('id3' in new_riff)
        self.assertTrue(isinstance(new_riff['id3'], RiffChunk))
        self.assertEqual(new_riff['id3'].size, 8)
        self.assertEqual(new_riff['id3'].data_size, 0)

    def test_insert_padded_chunks(self):
        padded = self.riff_2_tmp.insert_chunk('TST1')
        unpadded = self.riff_2_tmp.insert_chunk('TST2')
        # The second chunk needs no padding
        unpadded.resize(4)
        self.assertEqual(4, unpadded.data_size)
        self.assertEqual(0, unpadded.padding())
        self.assertEqual(12, unpadded.size)
        # Resize the first chunk so it needs padding
        padded.resize(3)
        self.assertEqual(3, padded.data_size)
        self.assertEqual(1, padded.padding())
        self.assertEqual(12, padded.size)
        self.assertEqual(padded.offset + padded.size, unpadded.offset)
        # Verify the padding byte gets written correctly
        self.file_2_tmp.seek(padded.data_offset)
        self.file_2_tmp.write(b'ABCD')
        padded.write(b'ABC')
        self.file_2_tmp.seek(padded.data_offset)
        self.assertEqual(b'ABC\x00', self.file_2_tmp.read(4))
        # Verify the second chunk got not overwritten
        self.file_2_tmp.seek(unpadded.offset)
        self.assertEqual(b'TST2', self.file_2_tmp.read(4))

    def test_delete_padded_chunks(self):
        riff_file = self.riff_2_tmp
        self.assertEqual(riff_file.root.size, 64044)
        riff_file.insert_chunk('TST')
        # Resize to odd length, should insert 1 padding byte
        riff_file['TST'].resize(3)
        # Insert another chunk after the first one
        self.assertEqual(riff_file.root.size, 64056)
        riff_file.insert_chunk('TST2')
        riff_file['TST2'].resize(2)
        self.assertEqual(riff_file.root.size, 64066)
        self.assertEqual(riff_file['TST'].size, 12)
        self.assertEqual(riff_file['TST'].data_size, 3)
        self.assertEqual(riff_file['TST'].data_offset, 64052)
        self.assertEqual(riff_file['TST2'].size, 10)
        self.assertEqual(riff_file['TST2'].data_size, 2)
        self.assertEqual(riff_file['TST2'].data_offset, 64064)
        # Delete the odd chunk
        riff_file.delete_chunk('TST')
        self.assertEqual(riff_file.root.size, 64054)
        self.assertEqual(riff_file['TST2'].size, 10)
        self.assertEqual(riff_file['TST2'].data_size, 2)
        self.assertEqual(riff_file['TST2'].data_offset, 64052)
        # Reloading the file should give the same results
        new_riff_file = RiffFile(self.file_2_tmp)
        self.assertEqual(new_riff_file.root.size,
                             riff_file.root.size)
        self.assertEqual(new_riff_file['TST2'].size,
            riff_file['TST2'].size)
        self.assertEqual(new_riff_file['TST2'].data_size,
            riff_file['TST2'].data_size)
        self.assertEqual(new_riff_file['TST2'].data_offset,
            riff_file['TST2'].data_offset)

    def test_read_list_info(self):
        riff = self.riff_1_tmp
        info = riff['LIST']
        self.assertEqual(info.name, 'INFO')
        info_tags = {}
        for chunk in info.subchunks():
            info_tags[chunk.id] = chunk.read().decode().strip('\0')
        self.assertEqual(info_tags['IPRD'], 'Quod Libet Test Data')
        self.assertEqual(info_tags['IART'], 'piman, jzig')
        self.assertEqual(info_tags['IGNR'], 'Silence')
        self.assertEqual(info_tags['INAM'], 'Silence')
        self.assertEqual(info_tags['ITRK'], '02/10')
        self.assertEqual(info_tags['ICRD'], '2004')
