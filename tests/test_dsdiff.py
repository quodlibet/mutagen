# -*- coding: utf-8 -*-

import os

from mutagen.dsdiff import DSDIFF, IffError

from tests import TestCase, DATA_DIR


class TDSDIFF(TestCase):
    silence_1 = os.path.join(DATA_DIR, '2822400-1ch-0s-silence.dff')
    silence_2 = os.path.join(DATA_DIR, '5644800-2ch-s01-silence.dff')
    silence_dst = os.path.join(DATA_DIR, '5644800-2ch-s01-silence-dst.dff')

    def setUp(self):
        self.dff_1 = DSDIFF(self.silence_1)
        self.dff_2 = DSDIFF(self.silence_2)
        self.dff_dst = DSDIFF(self.silence_dst)

    def test_channels(self):
        self.failUnlessEqual(self.dff_1.info.channels, 1)
        self.failUnlessEqual(self.dff_2.info.channels, 2)
        self.failUnlessEqual(self.dff_dst.info.channels, 2)

    def test_length(self):
        self.failUnlessEqual(self.dff_1.info.length, 0)
        self.failUnlessEqual(self.dff_2.info.length, 0.01)
        self.failUnlessEqual(self.dff_dst.info.length, 0)

    def test_sampling_frequency(self):
        self.failUnlessEqual(self.dff_1.info.sample_rate, 2822400)
        self.failUnlessEqual(self.dff_2.info.sample_rate, 5644800)
        self.failUnlessEqual(self.dff_dst.info.sample_rate, 5644800)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.dff_1.info.bits_per_sample, 1)

    def test_notdsf(self):
        self.failUnlessRaises(IffError, DSDIFF, os.path.join(
            DATA_DIR, '2822400-1ch-0s-silence.dsf'))

    def test_pprint(self):
        self.failUnless(self.dff_1.pprint())

    def test_mime(self):
        self.failUnless("audio/x-dff" in self.dff_1.mime)
