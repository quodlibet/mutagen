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

for more information.
"""

__all__ = ["WavPack", "Open", "delete"]

from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete
from mutagen._util import cdata, convert_error


class WavPackHeaderError(error):
    pass

RATES = [6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100,
         48000, 64000, 88200, 96000, 192000]


@convert_error(IOError, WavPackHeaderError)
def _read_sample_rate(fileobj, block_size):
    """Read ID_SAMPLE_RATE metadata without changing the header scan position."""

    position = fileobj.tell()
    remaining = block_size - 24  # ckSize excludes the first eight header bytes
    try:
        if remaining < 0:
            raise WavPackHeaderError("invalid block size")
        while remaining:
            if remaining < 2:
                raise WavPackHeaderError("truncated metadata header")
            data = fileobj.read(2)
            if len(data) != 2:
                raise WavPackHeaderError("truncated metadata header")
            id_, size = data[0], data[1] * 2
            remaining -= 2
            if id_ & 0x80:  # ID_LARGE: a 24-bit size measured in words
                if remaining < 2:
                    raise WavPackHeaderError("truncated metadata size")
                data = fileobj.read(2)
                if len(data) != 2:
                    raise WavPackHeaderError("truncated metadata size")
                size += int.from_bytes(data, "little") << 9
                remaining -= 2
            odd = bool(id_ & 0x40)
            if size > remaining or (odd and not size):
                raise WavPackHeaderError("invalid metadata size")
            if id_ & 0x3f == 0x27:  # ID_SAMPLE_RATE
                if size - odd not in (3, 4):
                    raise WavPackHeaderError("invalid sample rate metadata")
                data = fileobj.read(size)
                if len(data) != size:
                    raise WavPackHeaderError("truncated sample rate metadata")
                return (int.from_bytes(data[:size - odd], "little") &
                        0x7fffffff) or 44100
            if size:
                fileobj.seek(size - 1, 1)
                if len(fileobj.read(1)) != 1:
                    raise WavPackHeaderError("truncated metadata")
            remaining -= size
        # Match the reference decoder when no nonzero rate is specified.
        return 44100
    finally:
        fileobj.seek(position)


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


class WavPackInfo(StreamInfo):
    """WavPack stream information.

    Attributes:
        channels (int): number of audio channels (1 or 2)
        length (float): file length in seconds, as a float
        sample_rate (int): audio sampling rate in Hz
        bits_per_sample (int): audio sample size
        version (int): WavPack stream version
    """

    def __init__(self, fileobj):
        try:
            header = _WavPackHeader.from_fileobj(fileobj)
        except WavPackHeaderError:
            raise WavPackHeaderError("not a WavPack file")

        self.version = header.version
        self.channels = bool(header.flags & 4) or 2
        rate_index = (header.flags >> 23) & 0xF
        if rate_index == 0xF:
            self.sample_rate = _read_sample_rate(fileobj, header.block_size)
        else:
            self.sample_rate = RATES[rate_index]
        self.bits_per_sample = ((header.flags & 3) + 1) * 8

        # most common multiplier (DSD64)
        if (header.flags >> 31) & 1:
            self.sample_rate *= 4
            self.bits_per_sample = 1

        if header.total_samples == -1 or header.block_index != 0:
            # TODO: we could make this faster by using the tag size
            # and search backwards for the last block, then do
            # last.block_index + last.block_samples - initial.block_index
            samples = header.block_samples
            while 1:
                fileobj.seek(header.block_size - 32 + 8, 1)
                try:
                    header = _WavPackHeader.from_fileobj(fileobj)
                except WavPackHeaderError:
                    break
                samples += header.block_samples
        else:
            samples = header.total_samples

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
