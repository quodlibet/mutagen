
import os
import struct
from io import BytesIO

from mutagen.smf import SMF, SMFError
from tests import TestCase, DATA_DIR


class TSMFDuration(TestCase):

    def _length(self, *tracks, format_=0):
        data = b'MThd' + struct.pack('>IHHH', 6, format_, len(tracks), 480)
        for track in tracks:
            data += b'MTrk' + struct.pack('>I', len(track)) + track
        return SMF(BytesIO(data)).info.length

    def test_silent_track(self):
        self.assertAlmostEqual(self._length(b'\x83\x60\xff\x2f\x00'), 0.5)

    def test_end_of_track_delay(self):
        track = (b'\x00\x90\x3c\x40' + b'\x83\x60\x80\x3c\x00' +
                 b'\x83\x60\xff\x2f\x00')
        self.assertAlmostEqual(self._length(track), 1.0)

    def test_non_midi_event_delays(self):
        for event in (b'\xff\x01\x01A', b'\xf0\x01\xf7'):
            with self.subTest(event=event):
                track = (b'\x83\x60' + event + b'\x83\x60\x90\x3c\x40' +
                         b'\x00\xff\x2f\x00')
                self.assertAlmostEqual(self._length(track), 1.0)

    def test_tempo_change_after_delay(self):
        track = (b'\x83\x60\xff\x51\x03\x0f\x42\x40' +
                 b'\x83\x60\x90\x3c\x40' + b'\x00\xff\x2f\x00')
        self.assertAlmostEqual(self._length(track), 1.5)

    def test_same_tick_tempo_order(self):
        track = (b'\x00\xff\x51\x03\x0f\x42\x40' +
                 b'\x00\xff\x51\x03\x07\xa1\x20' +
                 b'\x83\x60\x90\x3c\x40' + b'\x00\xff\x2f\x00')
        self.assertAlmostEqual(self._length(track), 0.5)

    def test_format_one_shared_tempo(self):
        conductor = (b'\x83\x60\xff\x51\x03\x0f\x42\x40' +
                     b'\x83\x60\xff\x2f\x00')
        notes = (b'\x00\x90\x3c\x40' + b'\x87\x40\x80\x3c\x00' +
                 b'\x00\xff\x2f\x00')
        self.assertAlmostEqual(self._length(conductor, notes, format_=1), 1.5)


class TSMF(TestCase):

    def setUp(self):
        self.audio = SMF(os.path.join(DATA_DIR, "sample.mid"))

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 127.997, 2)

    def test_not_my_file(self):
        self.failUnlessRaises(
            SMFError, SMF, os.path.join(DATA_DIR, "empty.ogg"))

    def test_pprint(self):
        self.audio.pprint()
        self.audio.info.pprint()

    def test_mime(self):
        self.assertTrue("audio/x-midi" in self.audio.mime)
        self.assertTrue("audio/midi" in self.audio.mime)
