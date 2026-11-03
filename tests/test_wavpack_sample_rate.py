from io import BytesIO
import struct

import pytest

from mutagen import File, MutagenError
from mutagen.wavpack import RATES, WavPack, WavPackHeaderError, WavPackInfo


def block(metadata=b"", *, rate_index=15, samples=12345, total=12345,
          index=0, dsd=False):
    flags = (rate_index << 23) | 1 | 4
    if dsd:
        flags |= 1 << 31
    return struct.pack("<4sIHBBIIIII", b"wvpk", 24 + len(metadata),
                       0x410, 0, 0, total, index, samples, flags, 0) + metadata


def metadata(data, *, id_=0x27, large=False):
    odd = len(data) % 2
    words = (len(data) + odd) // 2
    flags = id_ | (0x40 if odd else 0) | (0x80 if large else 0)
    size = words.to_bytes(3 if large else 1, "little")
    return bytes([flags]) + size + data + b"\x00" * odd


@pytest.mark.parametrize("rate", [12345, 16777215, 16777216, 0x7fffffff])
@pytest.mark.parametrize("large", [False, True])
def test_custom_sample_rate(rate, large):
    data = rate.to_bytes(3 if rate < 1 << 24 else 4, "little")
    stream = BytesIO(block(metadata(data, large=large), samples=rate, total=rate))
    audio = WavPack(stream)
    assert audio.info.sample_rate == rate
    assert audio.info.length == 1.0
    assert audio.info.channels == 1
    assert audio.info.bits_per_sample == 16


def test_file_autodetection_with_custom_sample_rate():
    audio = File(BytesIO(block(metadata((12345).to_bytes(3, "little")))))
    assert isinstance(audio, WavPack)
    assert audio.info.sample_rate == 12345
    assert audio.info.length == 1.0


@pytest.mark.parametrize("large", [False, True])
@pytest.mark.parametrize("padding_size", [512, 131072])
def test_skip_unrelated_metadata(large, padding_size):
    unrelated = metadata(b"odd", id_=0x21)
    unrelated += metadata(b"x" * padding_size, id_=0x22, large=True)
    unrelated += metadata(b"", id_=0x20)
    stream = BytesIO(block(unrelated + metadata(
        (12345).to_bytes(3, "little"), large=large)))
    info = WavPackInfo(stream)
    assert info.sample_rate == 12345
    assert stream.tell() == 32


@pytest.mark.parametrize("index,rate", list(enumerate(RATES)))
def test_table_sample_rates_unchanged(index, rate):
    info = WavPackInfo(BytesIO(block(rate_index=index, samples=rate, total=rate)))
    assert info.sample_rate == rate
    assert info.length == 1.0


@pytest.mark.parametrize("data", [b"", metadata(b"", id_=0x20),
                                metadata(b"\x00\x00\x00")])
def test_unspecified_rate_defaults_like_reference_decoder(data):
    info = WavPackInfo(BytesIO(block(data, total=44100)))
    assert info.sample_rate == 44100
    assert info.length == 1.0


def test_four_byte_rate_ignores_reserved_high_bit():
    info = WavPackInfo(BytesIO(block(metadata(b"\x39\x30\x00\x80"))))
    assert info.sample_rate == 12345


def test_custom_dsd_rate_retains_existing_multiplier():
    info = WavPackInfo(BytesIO(block(metadata(
        (12345).to_bytes(3, "little")), dsd=True, total=49380)))
    assert info.sample_rate == 49380
    assert info.bits_per_sample == 1
    assert info.length == 1.0


@pytest.mark.parametrize("total,index", [(0xffffffff, 0), (999999, 12345)])
def test_custom_rate_preserves_block_scan(total, index):
    first = block(metadata((12345).to_bytes(3, "little")),
                  samples=12345, total=total, index=index)
    second = block(samples=12345, total=total, index=index + 12345)
    info = WavPackInfo(BytesIO(first + second))
    assert info.sample_rate == 12345
    assert info.length == 2.0


@pytest.mark.parametrize("data", [
    b"\x27",                         # incomplete metadata header
    b"\xa7\x02",                    # missing extended size
    b"\xa7\x02\x00",                # truncated extended size
    b"\x67\x00",                    # odd flag with zero stored bytes
    b"\x67\x03\x39\x30\x00\x00",    # payload exceeds block boundary
    metadata(b""),
    metadata(b"x"),
    metadata(b"xx"),
    metadata(b"xxxxx"),
])
def test_invalid_rate_metadata_raises_mutagen_error(data):
    stream = BytesIO(block(data))
    with pytest.raises(WavPackHeaderError) as exc:
        WavPackInfo(stream)
    assert isinstance(exc.value, MutagenError)
    assert stream.tell() == 32


@pytest.mark.parametrize("data", [
    metadata(b"\x39\x30\x00"),
    metadata(b"unknown", id_=0x21),
])
def test_truncated_payload_raises_mutagen_error(data):
    with pytest.raises(WavPackHeaderError):
        WavPackInfo(BytesIO(block(data)[:-1]))


def test_rate_metadata_cannot_be_read_from_next_block():
    # The first item claims four bytes but has only two in this block.
    first = block(b"\x67\x02\x39\x30")
    second = block(metadata((12345).to_bytes(3, "little")))
    with pytest.raises(WavPackHeaderError):
        WavPackInfo(BytesIO(first + second))


def test_invalid_block_size_raises_mutagen_error():
    data = bytearray(block())
    struct.pack_into("<I", data, 4, 23)
    with pytest.raises(WavPackHeaderError):
        WavPackInfo(BytesIO(data))
