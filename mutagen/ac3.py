# -*- coding: utf-8 -*-
# Copyright (C) 2019 Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Pure AC3 file information.
"""

__all__ = ["AC3", "Open"]

from mutagen._file import FileType
from mutagen._util import (
    BitReader,
    BitReaderError,
    MutagenError,
    convert_error,
    loadfile,
)


AC3_HEADER_SIZE = 7

AC3_CHMODE_DUALMONO = 0
AC3_CHMODE_MONO = 1
AC3_CHMODE_STEREO = 2
AC3_CHMODE_3F = 3
AC3_CHMODE_2F1R = 4
AC3_CHMODE_3F1R = 5
AC3_CHMODE_2F2R = 6
AC3_CHMODE_3F2R = 7

AC3_CHANNELS = {
    AC3_CHMODE_DUALMONO: 2,
    AC3_CHMODE_MONO: 1,
    AC3_CHMODE_STEREO: 2,
    AC3_CHMODE_3F: 3,
    AC3_CHMODE_2F1R: 3,
    AC3_CHMODE_3F1R: 4,
    AC3_CHMODE_2F2R: 4,
    AC3_CHMODE_3F2R: 5
}

AC3_SAMPLE_RATES = [48000, 44100, 32000]

AC3_BITRATES = [
    32, 40, 48, 56, 64, 80, 96, 112, 128,
    160, 192, 224, 256, 320, 384, 448, 512, 576, 640
]

EAC3_FRAME_TYPE_INDEPENDENT = 0
EAC3_FRAME_TYPE_DEPENDENT = 1
EAC3_FRAME_TYPE_AC3_CONVERT = 2
EAC3_FRAME_TYPE_RESERVED = 3

EAC3_BLOCKS = [1, 2, 3, 6]


class AC3Error(MutagenError):
    pass


class AC3Info(object):

    """AC3 stream information.
    The length of the stream is just a guess and might not be correct.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bitrate (`int`): audio bitrate, in bits per second
        type_ (`str`): AC3 or EAC3
    """

    channels = 0
    length = 0
    sample_rate = 0
    bitrate = 0
    type_ = 'AC3'

    @convert_error(IOError, AC3Error)
    @convert_error(IndexError, AC3Error)
    def __init__(self, fileobj):
        """Raises AC3Error"""
        header = fileobj.read(6)
        if not header.startswith(b"\x0b\x77"):
            raise AC3Error("not a AC3 file")

        bitstream_id = header[5] >> 3
        if bitstream_id > 16:
            raise AC3Error("invalid bitstream_id %i" % bitstream_id)

        fileobj.seek(2)
        self._read_header(fileobj, bitstream_id)

    def _read_header(self, fileobj, bitstream_id):
        bitreader = BitReader(fileobj)
        try:
            # This is partially based on code from
            # https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/ac3_parser.c
            if bitstream_id <= 10:  # Normal AC-3
                self._read_header_normal(bitreader, bitstream_id)
            else:  # Enhanced AC-3
                self._read_header_enhanced(bitreader)
        except (BitReaderError, KeyError) as e:
            raise AC3Error(e)

        self.length = self._guess_length(fileobj)

    def _read_header_normal(self, bitreader, bitstream_id):
        r = bitreader
        r.skip(16)  # 16 bit CRC
        sr_code = r.bits(2)
        if sr_code == 3:
            raise AC3Error("invalid sample rate code %i" % sr_code)

        frame_size_code = r.bits(6)
        if frame_size_code > 37:
            raise AC3Error("invalid frame size code %i" % frame_size_code)

        r.skip(5)  # bitstream ID, already read
        r.skip(3)  # bitstream mode, not needed
        channel_mode = r.bits(3)
        r.skip(2)  # dolby surround mode or surround mix level
        lfe_on = r.bits(1)

        sr_shift = max(bitstream_id, 8) - 8
        self.sample_rate = AC3_SAMPLE_RATES[sr_code] >> sr_shift
        self.bitrate = (AC3_BITRATES[frame_size_code >> 1] * 1000) >> sr_shift
        self.channels = self._get_channels(channel_mode, lfe_on)

    def _read_header_enhanced(self, bitreader):
        r = bitreader
        self.type_ = "EAC3"
        frame_type = r.bits(2)
        if frame_type == EAC3_FRAME_TYPE_RESERVED:
            raise AC3Error("invalid frame type %i" % frame_type)

        r.skip(3)  # substream ID, not needed

        frame_size = (r.bits(11) + 1) << 1
        if frame_size < AC3_HEADER_SIZE:
            raise AC3Error("invalid frame size %i" % frame_size)

        sr_code = r.bits(2)
        if sr_code == 3:
            sr_code2 = r.bits(2)
            if sr_code2 == 3:
                raise AC3Error("invalid sample rate code %i" % sr_code2)

            numblocks_code = 3
            self.sample_rate = AC3_SAMPLE_RATES[sr_code2] / 2
        else:
            numblocks_code = r.bits(2)
            self.sample_rate = AC3_SAMPLE_RATES[sr_code]

        channel_mode = r.bits(3)
        lfe_on = r.bits(1)
        self.bitrate = 8 * frame_size * self.sample_rate / (
            EAC3_BLOCKS[numblocks_code] * 256)
        r.skip(5)  # bitstream ID, already read
        self.channels = self._get_channels(channel_mode, lfe_on)

    @staticmethod
    def _get_channels(channel_mode, lfe_on):
        return AC3_CHANNELS[channel_mode] + lfe_on

    def _guess_length(self, fileobj):
        # use bitrate + data size to guess length
        if self.bitrate == 0:
            return
        start = fileobj.tell()
        fileobj.seek(0, 2)
        length = fileobj.tell() - start
        return 8 * length / self.bitrate

    def pprint(self):
        return "%s, %d Hz, %.2f seconds, %d channel(s), %d bps" % (
            self.type_, self.sample_rate, self.length, self.channels,
            self.bitrate)


class AC3(FileType):
    """AC3(filething)

    Arguments:
        filething (filething)

    Load AC3 or EAC3 files.

    Tagging is not supported.
    Use the ID3/APEv2 classes directly instead.

    Attributes:
        info (`AC3Info`)
    """

    _mimes = ["audio/ac3"]

    @loadfile()
    def load(self, filething):
        self.info = AC3Info(filething.fileobj)

    def add_tags(self):
        raise AC3Error("doesn't support tags")

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"\x0b\x77") * 2 \
            + filename.lower().endswith(".ac3")


Open = AC3
error = AC3Error
