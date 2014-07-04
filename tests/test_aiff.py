import os
import shutil

from tests import TestCase
from mutagen._compat import cBytesIO
from tests import add
from mutagen.aiff import AIFF, AIFFInfo, delete, IFFFile, IFFChunk
from mutagen.aiff import error as AIFFError
from tempfile import mkstemp

class TAIFF(TestCase):
    silence_1 = os.path.join('tests', 'data', '11k-1ch-2s-silence.aif')
    silence_2 = os.path.join('tests', 'data', '48k-2ch-s16-silence.aif')
    silence_3 = os.path.join('tests', 'data', '8k-1ch-1s-silence.aif')
    silence_4 = os.path.join('tests', 'data', '8k-1ch-3.5s-silence.aif')
    silence_5 = os.path.join('tests', 'data', '8k-4ch-1s-silence.aif')

    has_tags = os.path.join('tests', 'data', 'with-id3.aif')
    no_tags  = os.path.join('tests', 'data', '8k-1ch-1s-silence.aif')

    def setUp(self):
        fd, self.filename_1 = mkstemp(suffix='.aif')
        os.close(fd)
        shutil.copy(self.has_tags, self.filename_1)

        fd, self.filename_2 = mkstemp(suffix='.aif')
        os.close(fd)
        shutil.copy(self.no_tags, self.filename_2)

        self.aiff_tmp_id3    = AIFF(self.filename_1)
        self.aiff_tmp_no_id3 = AIFF(self.filename_2)

        self.aiff_1 = AIFF(self.silence_1)
        self.aiff_2 = AIFF(self.silence_2)
        self.aiff_3 = AIFF(self.silence_3)
        self.aiff_4 = AIFF(self.silence_4)
        self.aiff_5 = AIFF(self.silence_5)

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

    def test_sample_size(self):
        self.failUnlessEqual(self.aiff_1.info.sample_size, 16)
        self.failUnlessEqual(self.aiff_2.info.sample_size, 16)
        self.failUnlessEqual(self.aiff_3.info.sample_size, 16)
        self.failUnlessEqual(self.aiff_4.info.sample_size, 16)
        self.failUnlessEqual(self.aiff_5.info.sample_size, 16)

    def test_notaiff(self):
        self.failUnlessRaises(
            AIFFError, AIFF, os.path.join('tests', 'data', 'empty.ofr'))

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
        self.failUnlessRaises(ValueError, self.aiff_tmp_id3.save)

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
        from mutagen._id3frames import TIT1
        tags = self.aiff_tmp_id3.tags
        tags.add(TIT1(encoding=3, text="foobar"))
        tags.save()

        new = AIFF(self.aiff_tmp_id3.filename)
        self.failUnlessEqual(new["TIT1"], ["foobar"])

    def test_save_with_ID3_chunk(self):
        from mutagen._id3frames import TIT1
        self.aiff_tmp_id3["TIT1"] = TIT1(encoding=3, text="foobar")
        self.aiff_tmp_id3.save()
        self.failUnless(AIFF(self.filename_1)["TIT1"] == "foobar")
        self.failUnless(self.aiff_tmp_id3["TIT2"] == "AIFF title")

    def test_save_without_ID3_chunk(self):
        from mutagen._id3frames import TIT1
        self.aiff_tmp_no_id3["TIT1"] = TIT1(encoding=3, text="foobar")
        self.aiff_tmp_no_id3.save()
        self.failUnless(AIFF(self.filename_2)["TIT1"] == "foobar")

    def tearDown(self):
        os.unlink(self.filename_1)
        os.unlink(self.filename_2)

add(TAIFF)

class TAIFFInfo(TestCase):

    def test_empty(self):
        fileobj = cBytesIO(b"")
        self.failUnlessRaises(IOError, AIFFInfo, fileobj)

add(TAIFFInfo)

class TIFFFile(TestCase):
    has_tags = os.path.join('tests', 'data', 'with-id3.aif')
    no_tags  = os.path.join('tests', 'data', '8k-1ch-1s-silence.aif')

    def setUp(self):
        self.file_1 = open(self.has_tags, 'rb')
        self.iff_1  = IFFFile(self.file_1)
        self.file_2 = open(self.no_tags, 'rb')
        self.iff_2  = IFFFile(self.file_2)

        fd_1, tmp_1_name = mkstemp(suffix='.aif')
        shutil.copy(self.has_tags, tmp_1_name)
        self.file_1_tmp = open(tmp_1_name, 'rb+')
        self.iff_1_tmp  = IFFFile(self.file_1_tmp)

        fd_2, tmp_2_name = mkstemp(suffix='.aif')
        shutil.copy(self.no_tags, tmp_2_name)
        self.file_2_tmp = open(tmp_2_name, 'rb+')
        self.iff_2_tmp  = IFFFile(self.file_2_tmp)

    def test_has_chunks(self):
        self.failUnless('FORM' in self.iff_1)
        self.failUnless('COMM' in self.iff_1)
        self.failUnless('SSND' in self.iff_1)
        self.failUnless('ID3'  in self.iff_1)

        self.failUnless('FORM' in self.iff_2)
        self.failUnless('COMM' in self.iff_2)
        self.failUnless('SSND' in self.iff_2)

    def test_is_chunks(self):
        self.failUnless(isinstance(self.iff_1['FORM'], IFFChunk))
        self.failUnless(isinstance(self.iff_1['COMM'], IFFChunk))
        self.failUnless(isinstance(self.iff_1['SSND'], IFFChunk))
        self.failUnless(isinstance(self.iff_1['ID3'],  IFFChunk))

    def test_chunk_size(self):
        self.failUnlessEqual(self.iff_1['FORM'].size, 17096)
        self.failUnlessEqual(self.iff_2['FORM'].size, 16054)

    def test_chunk_data_size(self):
        self.failUnlessEqual(self.iff_1['FORM'].data_size, 17088)
        self.failUnlessEqual(self.iff_2['FORM'].data_size, 16046)

    def test_FORM_chunk_resize(self):
        self.iff_1_tmp['FORM'].resize(17000)
        self.failUnlessEqual(IFFFile(self.file_1_tmp)['FORM'].data_size, 17000)
        self.iff_2_tmp['FORM'].resize(0)
        self.failUnlessEqual(IFFFile(self.file_2_tmp)['FORM'].data_size, 0)

    def test_child_chunk_resize(self):
        self.iff_1_tmp['ID3'].resize(128)
        self.failUnlessEqual(IFFFile(self.file_1_tmp)['ID3'].data_size, 128)
        self.failUnlessEqual(IFFFile(self.file_1_tmp)['FORM'].data_size, 16182)

    def test_chunk_delete(self):
        del self.iff_1_tmp['ID3']
        self.failIf('ID3' in self.iff_1_tmp)
        self.failIf('ID3' in IFFFile(self.file_1_tmp))
        self.failUnlessEqual(IFFFile(self.file_1_tmp)['FORM'].size, 16054)
        del self.iff_2_tmp['SSND']
        self.failIf('SSND' in self.iff_2_tmp)
        self.failIf('SSND' in IFFFile(self.file_2_tmp))
        self.failUnlessEqual(IFFFile(self.file_2_tmp)['FORM'].size, 38)

    def test_insert_chunk(self):
        self.iff_2_tmp.insert_chunk('ID3')

        new_iff = IFFFile(self.file_2_tmp)
        self.failUnless('ID3' in new_iff)
        self.failUnless(isinstance(new_iff['ID3'], IFFChunk))
        self.failUnlessEqual(new_iff['FORM'].size, 16062)
        self.failUnlessEqual(new_iff['FORM'].data_size, 16054)
        self.failUnlessEqual(new_iff['ID3'].size, 8)
        self.failUnlessEqual(new_iff['ID3'].data_size, 0)

    def tearDown(self):
        self.file_1.close()
        self.file_2.close()
        self.file_1_tmp.close()
        self.file_2_tmp.close()

add(TIFFFile)
