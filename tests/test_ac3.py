
import os
import io

from mutagen.ac3 import AC3, AC3Error, AC3Info

from tests import TestCase, DATA_DIR


class _BitWriter(object):

    def __init__(self):
        self._bits = []

    def write(self, value, count):
        for i in range(count - 1, -1, -1):
            self._bits.append((value >> i) & 1)

    def bytes(self):
        bits = self._bits + [0] * (-len(self._bits) % 8)
        return bytes(int("".join(map(str, bits[i:i + 8])), 2)
                     for i in range(0, len(bits), 8))


def _ac3_frame(acmod, lfeon, cmixlev=0, surmixlev=0, dsurmod=0, dialnorm=31):
    """An AC-3 syncframe header built from ATSC A/52 5.3.2, plus enough
    padding for the bit reader.
    """

    w = _BitWriter()
    w.write(0x0B77, 16)  # syncword
    w.write(0, 16)  # crc1
    w.write(0, 2)  # fscod, 48 kHz
    w.write(32, 6)  # frmsizecod
    w.write(8, 5)  # bsid
    w.write(0, 3)  # bsmod
    w.write(acmod, 3)
    if acmod & 0x1 and acmod != 0x1:
        w.write(cmixlev, 2)
    if acmod & 0x4:
        w.write(surmixlev, 2)
    if acmod == 0x2:
        w.write(dsurmod, 2)
    w.write(lfeon, 1)
    w.write(dialnorm, 5)
    w.write(0, 3)  # compre, langcode, audprodie
    if acmod == 0:
        w.write(dialnorm, 5)  # dialnorm2
        w.write(0, 3)  # compr2e, langcod2e, audprodi2e
    w.write(0, 5)  # copyrightb, origbs, timecod1e, timecod2e, addbsie
    w.write(0, 64)
    return w.bytes()


class TAC3Header(TestCase):

    # A/52 Table 5.8, full bandwidth channels per acmod
    NFCHANS = [2, 1, 2, 3, 3, 4, 4, 5]

    def test_channels_all_channel_modes(self):
        for acmod in range(8):
            for lfeon in (0, 1):
                data = _ac3_frame(acmod, lfeon)
                info = AC3Info(io.BytesIO(data))
                self.assertEqual(
                    info.channels, self.NFCHANS[acmod] + lfeon,
                    "acmod=%d lfeon=%d" % (acmod, lfeon))

    def test_channels_ignore_mix_levels(self):
        # The mix level fields sit between acmod and lfeon, so their values
        # must not reach the channel count.
        for acmod in range(8):
            for lfeon in (0, 1):
                expected = self.NFCHANS[acmod] + lfeon
                for cmixlev in range(4):
                    for surmixlev in range(4):
                        for dsurmod in range(4):
                            data = _ac3_frame(acmod, lfeon, cmixlev,
                                              surmixlev, dsurmod)
                            info = AC3Info(io.BytesIO(data))
                            self.assertEqual(
                                info.channels, expected,
                                "acmod=%d lfeon=%d cmixlev=%d surmixlev=%d "
                                "dsurmod=%d" % (acmod, lfeon, cmixlev,
                                                surmixlev, dsurmod))


class TAC3(TestCase):

    def setUp(self):
        self.ac3 = AC3(os.path.join(DATA_DIR, "silence-44-s.ac3"))
        self.eac3 = AC3(os.path.join(DATA_DIR, "silence-44-s.eac3"))

    def test_channels(self):
        self.failUnlessEqual(self.ac3.info.channels, 2)
        self.failUnlessEqual(self.eac3.info.channels, 2)

    def test_bitrate(self):
        self.failUnlessEqual(self.ac3.info.bitrate, 192000)
        self.failUnlessAlmostEqual(self.eac3.info.bitrate, 192000, delta=500)

    def test_sample_rate(self):
        self.failUnlessEqual(self.ac3.info.sample_rate, 44100)
        self.failUnlessEqual(self.eac3.info.sample_rate, 44100)

    def test_length(self):
        self.failUnlessAlmostEqual(self.ac3.info.length, 3.70, delta=0.009)
        self.failUnlessAlmostEqual(self.eac3.info.length, 3.70, delta=0.009)

    def test_type(self):
        self.failUnlessEqual(self.ac3.info.codec, "ac-3")
        self.failUnlessEqual(self.eac3.info.codec, "ec-3")

    def test_not_my_file(self):
        self.failUnlessRaises(
            AC3Error, AC3,
            os.path.join(DATA_DIR, "empty.ogg"))

        self.failUnlessRaises(
            AC3Error, AC3,
            os.path.join(DATA_DIR, "silence-44-s.mp3"))

    def test_pprint(self):
        self.assertTrue("ac-3" in self.ac3.pprint())
        self.assertTrue("ec-3" in self.eac3.pprint())

    def test_fuzz_extra_bitstream_info(self):
        with self.assertRaises(AC3Error):
            AC3(io.BytesIO(b'\x0bwII\x00\x00\xe3\xe3//'))
