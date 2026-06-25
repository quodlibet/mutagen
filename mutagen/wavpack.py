# Copyright 2006 Joe Wreschnig
#           2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""WavPack reading and writing.

WavPack is a lossless format that uses APEv2 tags. Read

* http://www.wavpack.com/
* http://www.wavpack.com/file_format.txt
* http://www.wavpack.com/WavPack5FileFormat.pdf

for more information.
"""

__all__ = ["WavPack", "Open", "delete"]

from functools import reduce

from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete
from mutagen._util import cdata, convert_error


class WavPackHeaderError(error):
    pass

RATES = [6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100,
         48000, 64000, 88200, 96000, 192000]

# Metadata sub-block ID flags (from wavpack.h)
_ID_LARGE = 0x80         # size field is 3 bytes instead of 1
_ID_ODD_SIZE = 0x40      # actual data is 1 byte less than size_words*2
_ID_UNIQUE = 0x3f        # mask for the unique sub-block identifier

# MD5 sub-block identifiers (ID_OPTIONAL_DATA | n, see wavpack.h)
_ID_MD5_CHECKSUM = 0x26      # standard PCM files
_ID_ALT_MD5_CHECKSUM = 0x29  # DSD / alternate-format files (WavPack 5)


def _to_int_be(data):
    """Convert a byte string to a long using big-endian byte order."""
    return reduce(lambda a, b: (a << 8) + b, bytearray(data), 0)


class _WavPackHeader(object):

    def __init__(self, block_size, version, track_no, index_no, total_samples,
                 block_index, block_samples, flags, crc):

        self.block_size = block_size
        self.version = version
        self.track_no = track_no
        self.index_no = index_no
        self.total_samples = total_samples
        self.block_index = block_index
        self.block_samples = block_samples
        self.flags = flags
        self.crc = crc

    @classmethod
    @convert_error(IOError, WavPackHeaderError)
    def from_fileobj(cls, fileobj):
        """A new _WavPackHeader or raises WavPackHeaderError"""

        header = fileobj.read(32)
        if len(header) != 32 or not header.startswith(b"wvpk"):
            raise WavPackHeaderError("not a WavPack header: %r" % header)

        block_size = cdata.uint_le(header[4:8])
        version = cdata.ushort_le(header[8:10])
        track_no = ord(header[10:11])
        index_no = ord(header[11:12])
        samples = cdata.uint_le(header[12:16])
        if samples == 2 ** 32 - 1:
            samples = -1
        block_index = cdata.uint_le(header[16:20])
        block_samples = cdata.uint_le(header[20:24])
        flags = cdata.uint_le(header[24:28])
        crc = cdata.uint_le(header[28:32])

        return _WavPackHeader(block_size, version, track_no, index_no,
                              samples, block_index, block_samples, flags, crc)


def _extract_md5_from_metadata(fileobj, block_size):
    """Extract MD5 signature from WavPack metadata sub-blocks.

    Parses the metadata sub-blocks that follow the 32-byte frame header in
    the initial audio block, looking for the MD5 checksum sub-block
    (ID 0x26 for standard PCM files, ID 0x29 for DSD / alternate-format
    files). Returns None if no MD5 sub-block is present or if parsing fails.

    Each sub-block is laid out as follows (from wavpack.h):

      - 1 byte : ID byte
          bit 7 (_ID_LARGE)    - if set, size field is 3 bytes; else 1 byte
          bit 6 (_ID_ODD_SIZE) - if set, actual data is size_words*2 - 1 bytes
          bits 5-0             - unique sub-block identifier (_ID_UNIQUE mask)
      - 1 or 3 bytes : size in 16-bit words (little-endian for 3-byte form)
      - size_words*2 bytes : data payload (last byte is padding if _ID_ODD_SIZE)

    Args:
        fileobj: file-like object positioned immediately after the 32-byte
            frame header
        block_size (int): ckSize field from the frame header, which counts
            bytes from offset 8 to the end of the block; the metadata
            payload remaining after the 32-byte header is block_size - 24

    Returns:
        int or None: MD5 signature as a big-endian integer, or None if the
            sub-block is absent or the data is malformed
    """
    # The ckSize field covers everything after the first 8 bytes of the block.
    # We have already consumed the full 32-byte header, so the remaining
    # metadata payload is:  ckSize - (32 - 8) = block_size - 24 bytes.
    # (This matches the seek expression used elsewhere: block_size - 32 + 8.)
    metadata_size = block_size - 24
    if metadata_size <= 0:
        return None

    try:
        metadata_data = fileobj.read(metadata_size)
        if len(metadata_data) != metadata_size:
            return None
    except IOError:
        return None

    offset = 0
    while offset < len(metadata_data):
        if offset >= len(metadata_data):
            break

        id_byte = metadata_data[offset]
        offset += 1

        is_large = bool(id_byte & _ID_LARGE)
        is_odd = bool(id_byte & _ID_ODD_SIZE)
        unique_id = id_byte & _ID_UNIQUE

        # Size is stored in 16-bit words (not bytes).
        # _ID_LARGE in the ID byte selects 3-byte vs 1-byte size encoding.
        if is_large:
            if offset + 3 > len(metadata_data):
                break
            word_count = (metadata_data[offset] |
                          (metadata_data[offset + 1] << 8) |
                          (metadata_data[offset + 2] << 16))
            offset += 3
        else:
            if offset >= len(metadata_data):
                break
            word_count = metadata_data[offset]
            offset += 1

        # The block always occupies word_count*2 bytes on disk; _ID_ODD_SIZE
        # means the last byte of that allocation is padding, not payload.
        data_size = word_count * 2 - (1 if is_odd else 0)

        if unique_id in (_ID_MD5_CHECKSUM, _ID_ALT_MD5_CHECKSUM):
            if data_size == 16:
                md5_data = metadata_data[offset:offset + 16]
                if len(md5_data) == 16:
                    return _to_int_be(md5_data)
            return None

        # Advance past the full word-aligned block payload
        offset += word_count * 2

    return None


class WavPackInfo(StreamInfo):
    """WavPack stream information.

    Attributes:
        channels (int): number of audio channels (1 or 2)
        length (float): file length in seconds, as a float
        sample_rate (int): audio sampling rate in Hz
        bits_per_sample (int): audio sample size
        version (int): WavPack stream version
        md5_signature (int or None): MD5 checksum of the original
            uncompressed audio as an integer, or None if not present.
            The value matches the representation used by
            `mutagen.flac.StreamInfo.md5_signature`.
    """

    md5_signature = None

    def __init__(self, fileobj):
        try:
            header = _WavPackHeader.from_fileobj(fileobj)
        except WavPackHeaderError:
            raise WavPackHeaderError("not a WavPack file")

        self.version = header.version
        self.channels = bool(header.flags & 4) or 2
        self.sample_rate = RATES[(header.flags >> 23) & 0xF]
        self.bits_per_sample = ((header.flags & 3) + 1) * 8

        # most common multiplier (DSD64)
        if (header.flags >> 31) & 1:
            self.sample_rate *= 4
            self.bits_per_sample = 1

        # Parse metadata from the first block.
        self.md5_signature = _extract_md5_from_metadata(fileobj,
                                                        header.block_size)

        need_samples = header.total_samples == -1 or header.block_index != 0
        if need_samples:
            samples = header.block_samples
        else:
            samples = header.total_samples

        # Continue scanning blocks if we still need stream length or if MD5
        # wasn't present in the first block.
        while need_samples or self.md5_signature is None:
            try:
                header = _WavPackHeader.from_fileobj(fileobj)
            except WavPackHeaderError:
                break

            if self.md5_signature is None:
                self.md5_signature = _extract_md5_from_metadata(
                    fileobj, header.block_size)
            else:
                fileobj.seek(header.block_size - 32 + 8, 1)

            if need_samples:
                samples += header.block_samples

        self.length = float(samples) / self.sample_rate

    def pprint(self):
        return u"WavPack, %.2f seconds, %d Hz" % (self.length,
                                                  self.sample_rate)


class WavPack(APEv2File):
    """WavPack(filething)

    Arguments:
        filething (filething)

    Attributes:
        info (`WavPackInfo`)
    """

    _Info = WavPackInfo
    _mimes = ["audio/x-wavpack"]

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"wvpk") * 2


Open = WavPack
