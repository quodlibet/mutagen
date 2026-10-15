
import os
from io import BytesIO

from mutagen.id3 import ID3, TIT2
from mutagen.musepack import Musepack, MusepackInfo, MusepackHeaderError
from tests import TestCase, DATA_DIR, get_temp_copy


class TMusepack(TestCase):

    def setUp(self):
        self.sv8 = Musepack(os.path.join(DATA_DIR, "sv8_header.mpc"))
        self.sv7 = Musepack(os.path.join(DATA_DIR, "click.mpc"))
        self.sv5 = Musepack(os.path.join(DATA_DIR, "sv5_header.mpc"))
        self.sv4 = Musepack(os.path.join(DATA_DIR, "sv4_header.mpc"))

    def test_bad_header(self):
        self.failUnlessRaises(
            MusepackHeaderError,
            Musepack, os.path.join(DATA_DIR, "almostempty.mpc"))

    def test_channels(self):
        self.failUnlessEqual(self.sv8.info.channels, 2)
        self.failUnlessEqual(self.sv7.info.channels, 2)
        self.failUnlessEqual(self.sv5.info.channels, 2)
        self.failUnlessEqual(self.sv4.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.sv8.info.sample_rate, 44100)
        self.failUnlessEqual(self.sv7.info.sample_rate, 44100)
        self.failUnlessEqual(self.sv5.info.sample_rate, 44100)
        self.failUnlessEqual(self.sv4.info.sample_rate, 44100)

    def test_bitrate(self):
        self.failUnlessEqual(self.sv8.info.bitrate, 609)
        self.failUnlessEqual(self.sv7.info.bitrate, 194530)
        self.failUnlessEqual(self.sv5.info.bitrate, 39)
        self.failUnlessEqual(self.sv4.info.bitrate, 39)

    def test_length(self):
        self.failUnlessAlmostEqual(self.sv8.info.length, 1.49, 1)
        self.failUnlessAlmostEqual(self.sv7.info.length, 0.07, 2)
        self.failUnlessAlmostEqual(self.sv5.info.length, 26.3, 1)
        self.failUnlessAlmostEqual(self.sv4.info.length, 26.3, 1)

    def test_gain(self):
        self.failUnlessAlmostEqual(self.sv8.info.title_gain, -4.668, 3)
        self.failUnlessAlmostEqual(self.sv8.info.title_peak, 0.5288, 3)
        self.failUnlessEqual(
            self.sv8.info.title_gain, self.sv8.info.album_gain)
        self.failUnlessEqual(
            self.sv8.info.title_peak, self.sv8.info.album_peak)
        self.failUnlessAlmostEqual(self.sv7.info.title_gain, 9.27, 6)
        self.failUnlessAlmostEqual(self.sv7.info.title_peak, 0.1149, 4)
        self.failUnlessEqual(
            self.sv7.info.title_gain, self.sv7.info.album_gain)
        self.failUnlessEqual(
            self.sv7.info.title_peak, self.sv7.info.album_peak)
        self.failUnlessRaises(AttributeError, getattr, self.sv5, 'title_gain')

    def test_not_my_file(self):
        self.failUnlessRaises(
            MusepackHeaderError, Musepack,
            os.path.join(DATA_DIR, "empty.ogg"))
        self.failUnlessRaises(
            MusepackHeaderError, Musepack,
            os.path.join(DATA_DIR, "emptyfile.mp3"))

    def test_almost_my_file(self):
        self.failUnlessRaises(
            MusepackHeaderError, MusepackInfo, BytesIO(b"MP+" + b"\x00" * 32))
        self.failUnlessRaises(
            MusepackHeaderError,
            MusepackInfo,
            BytesIO(b"MP+" + b"\x00" * 100))
        self.failUnlessRaises(
            MusepackHeaderError,
            MusepackInfo,
            BytesIO(b"MPCK" + b"\x00" * 100))

    def test_pprint(self):
        self.sv8.pprint()
        self.sv7.pprint()
        self.sv5.pprint()
        self.sv4.pprint()

    def test_mime(self):
        self.failUnless("audio/x-musepack" in self.sv7.mime)

    def test_zero_padded_sh_packet(self):
        # https://github.com/quodlibet/mutagen/issues/198
        data = (b"MPCKSH\x10\x95 Q\xa2\x08\x81\xb8\xc9T\x00\x1e\x1b"
                b"\x00RG\x0c\x01A\xcdY\x06?\x80Z\x06EI")

        fileobj = BytesIO(data)
        info = MusepackInfo(fileobj)
        self.assertEqual(info.channels, 2)
        self.assertEqual(info.samples, 3024084)

    def test_packet_size_smaller_than_header(self):
        # https://github.com/quodlibet/mutagen/issues/433
        # a packet size of 0 used to seek back to the same packet key and
        # loop forever
        for size in [b"\x00", b"\x80\x00"]:
            self.failUnlessRaises(
                MusepackHeaderError,
                MusepackInfo,
                BytesIO(b"MPCK" + b"XX" + size))

    def test_packet_with_empty_payload(self):
        # a size that only covers the key and the size field is still valid
        data = (b"MPCKXX\x03SH\x10\x95 Q\xa2\x08\x81\xb8\xc9T\x00\x1e\x1b"
                b"\x00RG\x0c\x01A\xcdY\x06?\x80Z\x06EI")

        info = MusepackInfo(BytesIO(data))
        self.assertEqual(info.channels, 2)
        self.assertEqual(info.samples, 3024084)


class TMusepackWithID3(TestCase):

    def setUp(self):
        self.filename = get_temp_copy(os.path.join(DATA_DIR, "click.mpc"))

    def tearDown(self):
        os.unlink(self.filename)

    def test_ignore_id3(self):
        id3 = ID3()
        id3.add(TIT2(encoding=0, text='id3 title'))
        id3.save(self.filename)
        f = Musepack(self.filename)
        f['title'] = 'apev2 title'
        f.save()
        id3 = ID3(self.filename)
        self.failUnlessEqual(id3['TIT2'], 'id3 title')
        f = Musepack(self.filename)
        self.failUnlessEqual(f['title'], 'apev2 title')
