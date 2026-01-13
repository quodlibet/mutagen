# Copyright (C) 2006  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""OptimFROG audio streams with APEv2 tags.

OptimFROG is a lossless audio compression program. Its main goal is to
reduce at maximum the size of audio files, while permitting bit
identical restoration for all input. It is similar with the ZIP
compression, but it is highly specialized to compress audio data.

Only versions 4.5 and higher are supported.

For more information, see http://www.losslessaudio.org/
"""

__all__ = ["OptimFROG", "Open", "delete"]

import struct
from io import BytesIO
from typing import cast, final, override

from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, delete, error

from ._util import convert_error, endswith

SAMPLE_TYPE_BITS = {
    0: 8,
    1: 8,
    2: 16,
    3: 16,
    4: 24,
    5: 24,
    6: 32,
    7: 32,
}


class OptimFROGHeaderError(error):
    pass

@final
class OptimFROGInfo(StreamInfo):
    """OptimFROGInfo()

    OptimFROG stream information.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bits_per_sample (`int`): the audio sample size
        encoder_info (`mutagen.text`): encoder version, e.g. "5.100"
    """

    channels: int
    length: float
    sample_rate: int
    bits_per_sample: int
    encoder_info: str

    @convert_error(IOError, OptimFROGHeaderError)
    def __init__(self, fileobj: BytesIO):
        """Raises OptimFROGHeaderError"""

        header = fileobj.read(76)
        if len(header) != 76 or not header.startswith(b"OFR "):
            raise OptimFROGHeaderError("not an OptimFROG file")
        data_size = struct.unpack("<I", header[4:8])[0]
        if data_size != 12 and data_size < 15:
            raise OptimFROGHeaderError("not an OptimFROG file")
        (total_samples, total_samples_high, sample_type, self.channels,
         self.sample_rate) = cast(tuple[int, int, int, int, int], struct.unpack("<IHBBI", header[8:20]))
        total_samples += total_samples_high << 32
        self.channels += 1
        self.bits_per_sample = SAMPLE_TYPE_BITS.get(sample_type)
        if self.sample_rate:
            self.length = float(total_samples) / (self.channels *
                                                  self.sample_rate)
        else:
            self.length = 0.0
        if data_size >= 15:
            encoder_id = cast(int, struct.unpack("<H", header[20:22])[0])
            version = str((encoder_id >> 4) + 4500)
            self.encoder_info = f"{version[0]}.{version[1:]}"
        else:
            self.encoder_info = ""

    @override
    def pprint(self):
        return "OptimFROG, %.2f seconds, %d Hz" % (self.length,
                                                    self.sample_rate)

@final
class OptimFROG(APEv2File):
    """OptimFROG(filething)

    Attributes:
        info (`OptimFROGInfo`)
        tags (`mutagen.apev2.APEv2`)
    """

    _Info: type[StreamInfo] = OptimFROGInfo

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        filename = filename.lower()

        return (header.startswith(b"OFR") + endswith(filename, b".ofr") +
                endswith(filename, b".ofs"))

Open = OptimFROG
