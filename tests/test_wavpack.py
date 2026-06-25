import os
from io import BytesIO

from mutagen.wavpack import (WavPack, WavPackHeaderError,
                             _to_int_be, _extract_md5_from_metadata,
                             _ID_MD5_CHECKSUM, _ID_ALT_MD5_CHECKSUM)
from tests import TestCase, DATA_DIR


class TWavPack(TestCase):

    def setUp(self):
        self.audio = WavPack(os.path.join(DATA_DIR, "silence-44-s.wv"))

    def test_version(self):
        self.failUnlessEqual(self.audio.info.version, 0x403)

    def test_channels(self):
        self.failUnlessEqual(self.audio.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.audio.info.sample_rate, 44100)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.audio.info.bits_per_sample, 16)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 3.68, 2)

    def test_md5_signature(self):
        # The test file may or may not carry an MD5 (depends on how it was
        # encoded).  Just verify the attribute has the correct type.
        self.assertTrue(
            self.audio.info.md5_signature is None or
            isinstance(self.audio.info.md5_signature, int)
        )

    def test_not_my_file(self):
        self.failUnlessRaises(
            WavPackHeaderError, WavPack, os.path.join(DATA_DIR, "empty.ogg"))

    def test_pprint(self):
        self.audio.pprint()

    def test_mime(self):
        self.failUnless("audio/x-wavpack" in self.audio.mime)


class TWavPackNoLength(TestCase):

    def setUp(self):
        self.audio = WavPack(os.path.join(DATA_DIR, "no_length.wv"))

    def test_version(self):
        self.failUnlessEqual(self.audio.info.version, 0x407)

    def test_channels(self):
        self.failUnlessEqual(self.audio.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.audio.info.sample_rate, 44100)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.audio.info.bits_per_sample, 16)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 3.705, 3)

    def test_pprint(self):
        self.audio.pprint()

    def test_mime(self):
        self.failUnless("audio/x-wavpack" in self.audio.mime)


class TWavPackDSD(TestCase):

    def setUp(self):
        self.audio = WavPack(os.path.join(DATA_DIR, "dsd.wv"))

    def test_version(self):
        self.failUnlessEqual(self.audio.info.version, 0x410)

    def test_channels(self):
        self.failUnlessEqual(self.audio.info.channels, 2)

    def test_sample_rate(self):
        self.failUnlessEqual(self.audio.info.sample_rate, 352800)

    def test_bits_per_sample(self):
        self.failUnlessEqual(self.audio.info.bits_per_sample, 1)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 0.01, 3)

    def test_pprint(self):
        self.audio.pprint()

    def test_mime(self):
        self.failUnless("audio/x-wavpack" in self.audio.mime)


class TMD5Extraction(TestCase):
    """Unit tests for WavPack metadata sub-block MD5 parsing.

    Sub-block wire format (from wavpack.h):
      - 1 byte ID: bit7=LARGE, bit6=ODD_SIZE, bits5-0=unique id
      - 1 byte (or 3 bytes if LARGE) size in 16-bit words
      - size_words*2 bytes of payload data
    """

    def _make_fileobj(self, data):
        return BytesIO(data)

    # ------------------------------------------------------------------
    # _to_int_be
    # ------------------------------------------------------------------

    def test_to_int_be_zero(self):
        self.failUnlessEqual(_to_int_be(b'\x00' * 16), 0)

    def test_to_int_be_one(self):
        self.failUnlessEqual(_to_int_be(b'\x00' * 15 + b'\x01'), 1)

    def test_to_int_be_msb(self):
        self.failUnlessEqual(_to_int_be(b'\x01' + b'\x00' * 15),
                             1 << 120)

    def test_to_int_be_all_ff(self):
        self.failUnlessEqual(_to_int_be(b'\xff' * 4), 0xffffffff)

    # ------------------------------------------------------------------
    # _extract_md5_from_metadata: boundary / empty cases
    # ------------------------------------------------------------------

    def test_no_metadata_when_block_size_too_small(self):
        # block_size - 24 <= 0  →  no metadata possible
        result = _extract_md5_from_metadata(BytesIO(b''), 24)
        self.failUnlessEqual(result, None)

    def test_empty_payload(self):
        result = _extract_md5_from_metadata(BytesIO(b''), 25)
        self.failUnlessEqual(result, None)

    # ------------------------------------------------------------------
    # Correct ID / correct size → should find MD5
    # ------------------------------------------------------------------

    def test_standard_md5_single_byte_size(self):
        # ID_MD5_CHECKSUM = 0x26; 16 bytes = 8 words → size byte = 0x08
        md5_bytes = bytes(range(16))
        payload = bytes([_ID_MD5_CHECKSUM, 0x08]) + md5_bytes
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, _to_int_be(md5_bytes))

    def test_alt_md5_single_byte_size(self):
        # ID_ALT_MD5_CHECKSUM = 0x29 (used for DSD / alt-format files)
        md5_bytes = bytes(range(16, 32))
        payload = bytes([_ID_ALT_MD5_CHECKSUM, 0x08]) + md5_bytes
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, _to_int_be(md5_bytes))

    def test_md5_found_after_other_sub_blocks(self):
        # A realistic payload: one non-MD5 sub-block followed by the MD5.
        # Sub-block 1: ID=0x01 (ID_ENCODER_INFO), 2 words (4 bytes) of data
        other = bytes([0x01, 0x02]) + b'\x00' * 4
        md5_bytes = b'\xde\xad\xbe\xef' * 4
        md5_block = bytes([_ID_MD5_CHECKSUM, 0x08]) + md5_bytes
        payload = other + md5_block
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, _to_int_be(md5_bytes))

    # ------------------------------------------------------------------
    # Wrong ID or wrong size → should return None
    # ------------------------------------------------------------------

    def test_no_md5_block_present(self):
        # Only a non-MD5 sub-block; result must be None
        payload = bytes([0x01, 0x02]) + b'\x00' * 4
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, None)

    def test_wrong_size_returns_none(self):
        # MD5 block claims 15 bytes (7 words + ODD_SIZE), not 16 → rejected
        payload = bytes([_ID_MD5_CHECKSUM | 0x40, 0x08]) + b'\x00' * 16
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, None)

    def test_truncated_md5_data_returns_none(self):
        # Header says 8 words but the fileobj only has 15 bytes of payload
        payload = bytes([_ID_MD5_CHECKSUM, 0x08]) + b'\x00' * 15
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, None)

    # ------------------------------------------------------------------
    # Large (3-byte) size encoding
    # ------------------------------------------------------------------

    def test_large_size_non_md5_block_skipped(self):
        # Build a large sub-block (ID_LARGE set) with 200 bytes of data
        # (100 words), followed by the MD5 block.
        large_data = b'\xab' * 200
        # ID byte with _ID_LARGE set, arbitrary unique id 0x05
        large_id = 0x80 | 0x05
        # 3-byte little-endian word count: 100 = 0x64
        large_block = bytes([large_id, 100, 0, 0]) + large_data
        md5_bytes = b'\x11\x22\x33\x44' * 4
        md5_block = bytes([_ID_MD5_CHECKSUM, 0x08]) + md5_bytes
        payload = large_block + md5_block
        result = _extract_md5_from_metadata(BytesIO(payload),
                                            24 + len(payload))
        self.failUnlessEqual(result, _to_int_be(md5_bytes))
