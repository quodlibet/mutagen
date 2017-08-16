# -*- coding: utf-8 -*-

import os

from mutagen.wave import WAVE
from tests import TestCase, DATA_DIR, get_temp_copy


class TWave(TestCase):
    def setUp(self):
        fn_wav_pcm_2s_16000_08_ID3v23 = os.path.join(DATA_DIR, "silence-2s-PCM-16000-08-ID3v23.wav")
        self.wav_pcm_2s_16000_08_ID3v23 = WAVE(fn_wav_pcm_2s_16000_08_ID3v23)

        self.tmp_fn_pcm_2s_16000_08_ID3v23 = get_temp_copy(fn_wav_pcm_2s_16000_08_ID3v23)
        self.tmp_wav_pcm_2s_16000_08_ID3v23 = WAVE(self.tmp_fn_pcm_2s_16000_08_ID3v23)

        fn_wav_pcm_2s_16000_08_notags = os.path.join(DATA_DIR, "silence-2s-PCM-16000-08-notags.wav")
        self.wav_pcm_2s_16000_08_notags = WAVE(fn_wav_pcm_2s_16000_08_notags)

        self.tmp_fn_pcm_2s_16000_08_notag = get_temp_copy(fn_wav_pcm_2s_16000_08_notags)
        self.tmp_wav_pcm_2s_16000_08_notag = WAVE(self.tmp_fn_pcm_2s_16000_08_notag)

        fn_wav_pcm_2s_44100_16_ID3v23 = os.path.join(DATA_DIR, "silence-2s-PCM-44100-16-ID3v23.wav")
        self.wav_pcm_2s_44100_16_ID3v23 = WAVE(fn_wav_pcm_2s_44100_16_ID3v23)

    def test_channels(self):
        self.failUnlessEqual(self.wav_pcm_2s_16000_08_ID3v23.info.channels, 2)
        self.failUnlessEqual(self.wav_pcm_2s_44100_16_ID3v23.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.wav_pcm_2s_16000_08_ID3v23.info.sample_rate, 16000)
        self.failUnlessEqual(self.wav_pcm_2s_44100_16_ID3v23.info.sample_rate, 44100)

    def test_number_of_samples(self):
        self.failUnlessEqual(self.wav_pcm_2s_16000_08_ID3v23.info.number_of_samples, 32000)
        self.failUnlessEqual(self.wav_pcm_2s_44100_16_ID3v23.info.number_of_samples, 88200)

    def test_length(self):
        self.failUnlessAlmostEqual(self.wav_pcm_2s_16000_08_ID3v23.info.length, 2.0, 2)
        self.failUnlessAlmostEqual(self.wav_pcm_2s_44100_16_ID3v23.info.length, 2.0, 2)

    def test_not_my_file(self):
        self.failUnlessRaises(
            KeyError, WAVE, os.path.join(DATA_DIR, "empty.ogg"))

    def test_pprint(self):
        self.wav_pcm_2s_44100_16_ID3v23.pprint()

    def test_mime(self):
        self.failUnless("audio/wav" in self.wav_pcm_2s_44100_16_ID3v23.mime)
        self.failUnless("audio/wave" in self.wav_pcm_2s_44100_16_ID3v23.mime)

    def test_ID3_tags(self):
        id3 = self.wav_pcm_2s_44100_16_ID3v23.tags
        self.assertEquals(id3["TALB"], "Quod Libet Test Data")
        self.assertEquals(id3["TCON"], "Silence")
        self.assertEquals(id3["TIT2"], "Silence")
        self.assertEquals(id3["TPE1"], ["piman / jzig"])  # ToDo: split on '/'?

    def test_delete(self):
        self.tmp_wav_pcm_2s_16000_08_ID3v23.delete()

        self.failIf(self.tmp_wav_pcm_2s_16000_08_ID3v23.tags)
        self.failUnless(WAVE(self.tmp_fn_pcm_2s_16000_08_ID3v23).tags is None)

    def test_save_no_tags(self):
        self.tmp_wav_pcm_2s_16000_08_ID3v23.tags = None
        self.tmp_wav_pcm_2s_16000_08_ID3v23.save()
        self.assertTrue(self.tmp_wav_pcm_2s_16000_08_ID3v23.tags is None)

    def test_add_tags_already_there(self):
        self.failUnless(self.tmp_wav_pcm_2s_16000_08_ID3v23.tags)
        self.failUnlessRaises(Exception, self.tmp_wav_pcm_2s_16000_08_ID3v23.add_tags)

    def test_roundtrip(self):
        self.failUnlessEqual(self.tmp_wav_pcm_2s_16000_08_ID3v23["TIT2"], ["Silence"])
        self.tmp_wav_pcm_2s_16000_08_ID3v23.save()
        new = WAVE(self.tmp_wav_pcm_2s_16000_08_ID3v23.filename)
        self.failUnlessEqual(new["TIT2"], ["Silence"])

    def test_save_tags(self):
        from mutagen.id3 import TIT1
        tags = self.tmp_wav_pcm_2s_16000_08_ID3v23.tags
        tags.add(TIT1(encoding=3, text="foobar"))
        tags.save()

        new = WAVE(self.tmp_wav_pcm_2s_16000_08_ID3v23.filename)
        self.failUnlessEqual(new["TIT1"], ["foobar"])

    def test_save_without_ID3_chunk(self):
        from mutagen.id3 import TIT1
        self.tmp_wav_pcm_2s_16000_08_notag["TIT1"] = TIT1(encoding=3, text="foobar")
        self.tmp_wav_pcm_2s_16000_08_notag.save()
        self.failUnless(WAVE(self.tmp_fn_pcm_2s_16000_08_notag)["TIT1"] == "foobar")
