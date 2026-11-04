# Tests for the bounded decompression of compressed ID3 frames (zlib "bomb"
# protection). See mutagen/id3/_frames.py:_inflate_bounded.

import struct
import zlib

from tests import TestCase

from mutagen.id3 import _frames, Frames
from mutagen.id3 import _tags
from mutagen.id3._frames import TIT2, _inflate_bounded
from mutagen.id3._tags import ID3Header, read_frames
from mutagen.id3._util import ID3JunkFrameError


# A minimal, valid TIT2 body: encoding byte 0 (latin-1) + text.
def _tit2_body(text=b"ok"):
    return b"\x00" + text


def _header(version):
    h = ID3Header()
    h.version = version
    return h


def _syncsafe4(n):
    return bytes([(n >> 21) & 0x7f, (n >> 14) & 0x7f, (n >> 7) & 0x7f, n & 0x7f])


def _v23_frame(frame_id, declared, payload, flags=0x0080):
    # v2.3 compressed frame data = [4-byte big-endian uncompressed size][zlib]
    framedata = struct.pack(">L", declared) + zlib.compress(payload)
    # v2.3 frame size is a plain uint32.
    return (frame_id + struct.pack(">L", len(framedata)) +
            struct.pack(">H", flags) + framedata)


class TDecompressBound(TestCase):

    CAP = 64  # tiny cap keeps the tests fast; the real default is 64 MiB

    def setUp(self):
        # _tags imported the constant by value, so patch both namespaces.
        self._orig = _frames.MAX_DECOMPRESSED_SIZE
        _frames.MAX_DECOMPRESSED_SIZE = self.CAP
        _tags.MAX_DECOMPRESSED_SIZE = self.CAP

    def tearDown(self):
        _frames.MAX_DECOMPRESSED_SIZE = self._orig
        _tags.MAX_DECOMPRESSED_SIZE = self._orig

    # ---- the helper directly (cap boundary) ----

    def test_helper_at_cap_ok_over_cap_rejected(self):
        out = _inflate_bounded(zlib.compress(b"\x00" * self.CAP), _header((2, 4, 0)))
        self.assertEqual(len(out), self.CAP)
        self.assertRaises(
            ID3JunkFrameError, _inflate_bounded,
            zlib.compress(b"\x00" * (self.CAP + 1)), _header((2, 4, 0)))

    def test_helper_truncated_raises_zlib_error(self):
        comp = zlib.compress(b"\x00" * 8)
        self.assertRaises(zlib.error, _inflate_bounded, comp[:-2], _header((2, 4, 0)))

    # ---- v2.3 ----

    def test_v23_legit_small_decodes(self):
        body = _tit2_body(b"ok")
        data = struct.pack(">L", len(body)) + zlib.compress(body)
        tag = TIT2._fromData(_header((2, 3, 0)), 0x0080, data)
        self.assertEqual(tag.text, [u"ok"])

    def test_v23_bomb_rejected(self):
        data = struct.pack(">L", 1) + zlib.compress(b"\x00" * 1000)
        self.assertRaises(ID3JunkFrameError, TIT2._fromData,
                          _header((2, 3, 0)), 0x0080, data)

    def test_v23_declared_size_early_reject(self):
        # The declared size alone exceeds the cap: rejected before inflating.
        data = struct.pack(">L", self.CAP + 1) + zlib.compress(b"\x00" * 4)
        self.assertRaises(ID3JunkFrameError, TIT2._fromData,
                          _header((2, 3, 0)), 0x0080, data)

    # ---- v2.4 ----

    def test_v24_legit_small_decodes(self):
        body = _tit2_body(b"ok")
        data = struct.pack(">L", len(body)) + zlib.compress(body)  # 4 bytes stripped
        tag = TIT2._fromData(_header((2, 4, 0)), 0x08, data)
        self.assertEqual(tag.text, [u"ok"])

    def test_v24_bomb_rejected(self):
        data = _syncsafe4(1) + zlib.compress(b"\x00" * 1000)
        self.assertRaises(ID3JunkFrameError, TIT2._fromData,
                          _header((2, 4, 0)), 0x08, data)

    def test_v24_datalen_early_reject(self):
        # FLAG24_DATALEN (0x01): the syncsafe data-length indicator exceeds the
        # cap, so the frame is rejected before inflating.
        data = _syncsafe4(self.CAP + 1) + zlib.compress(b"\x00" * 4)
        self.assertRaises(ID3JunkFrameError, TIT2._fromData,
                          _header((2, 4, 0)), 0x08 | 0x01, data)

    def test_v24_ql012_retry_preserved(self):
        # QL 0.12 wrote the compressed data WITHOUT the 4-byte size prefix, so
        # the first decompress fails and the retry prepends the stripped bytes.
        body = _tit2_body(b"ok")
        comp = zlib.compress(body)  # no 4-byte prefix
        tag = TIT2._fromData(_header((2, 4, 0)), 0x08, comp)
        self.assertEqual(tag.text, [u"ok"])

    # ---- aggregate across frames ----

    def test_aggregate_budget_across_frames(self):
        # Two compressed frames, each under the cap, but together over it: the
        # first survives, the second is dropped (budget exhausted).
        n = self.CAP * 3 // 4  # 48 of a 64 cap; two of them = 96 > 64
        data = (_v23_frame(b"TIT2", n, _tit2_body(b"a" * (n - 1))) +
                _v23_frame(b"TPE1", n, _tit2_body(b"b" * (n - 1))))
        id3 = _header((2, 3, 0))
        result, unknown, _ = read_frames(id3, data, Frames)
        self.assertEqual([f.FrameID for f in result], ["TIT2"])

    def test_default_cap_is_64_mib(self):
        self.assertEqual(self._orig, 64 * 1024 * 1024)
