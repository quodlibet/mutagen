# -*- coding: utf-8 -*-
# Copyright (C) 2017  Borewit
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Microsoft WAVE/RIFF audio file/stream information and tags."""

import sys
import struct

from ._compat import endswith, reraise

from mutagen import StreamInfo, FileType

from mutagen.id3 import ID3
from mutagen._riff import RiffFile, InvalidChunk, error
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import loadfile, \
    convert_error, MutagenError

__all__ = ["WAVE", "Open", "delete"]


class error(MutagenError):
    """WAVE stream parsing errors."""


class WaveFile(RiffFile):
    """Representation of a RIFF/WAVE file"""

    def __init__(self, fileobj):
        RiffFile.__init__(self, fileobj)

        if self.fileType != u'WAVE':
            raise error("Expected RIFF/WAVE.")


class WaveStreamInfo(StreamInfo):
    """WaveStreamInfo()

    Microsoft WAVE file information.

    Information is parsed from the 'fmt' & 'data'chunk of the RIFF/WAVE file

    Attributes:
        length (`float`): audio length, in seconds
        bitrate (`int`): audio bitrate, in bits per second
        channels (`int`): The number of audio channels
        sample_rate (`int`): audio sample rate, in Hz
        sample_size (`int`): The audio sample size
    """

    length = 0
    bitrate = 0
    channels = 0
    sample_rate = 0

    SIZE = 16

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        waveFile = WaveFile(fileobj)
        try:
            waveFormatChunk = waveFile['fmt']
        except KeyError as e:
            raise error(str(e))

        data = waveFormatChunk.read()

        header = fileobj.read(self.SIZE)
        if len(header) < self.SIZE:
            raise InvalidChunk()

        # RIFF: http://soundfile.sapp.org/doc/WaveFormat/
        #  Python struct.unpack:
        #    https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
        info = struct.unpack('<hhLLhh', data[:self.SIZE])
        self.audioFormat, self.channels, self.sample_rate, byte_rate, \
        block_align, self.sample_size = info
        self.bitrate = self.channels * block_align * self.sample_rate

        # Calculate duration
        try:
            waveDataChunk = waveFile['data']
            self.number_of_samples = waveDataChunk.data_size / block_align
        except KeyError:
            self.number_of_samples = 0

        if self.sample_rate > 0:
            self.length = self.number_of_samples / self.sample_rate

    def pprint(self):
        return u"%d channel AIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _WaveID3(ID3):
    """A Wave file with ID3v2 tags"""

    print("RIFF/WAVE_WaveID3(ID3)")

    def _pre_load_header(self, fileobj):
        try:
            fileobj.seek(WaveFile(fileobj)['id3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3NoHeaderError("No ID3 chunk")

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething, v1=1, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the Wave/RIFF file"""

        fileobj = filething.fileobj

        wave_file = WaveFile(fileobj)

        if 'id3' not in wave_file:
            wave_file.insert_chunk('id3')

        chunk = wave_file['id3']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        chunk.resize(len(data))
        chunk.write(data)

    @loadfile(writable=True)
    def delete_chunk(self, filething):
        """Completely removes the ID3 chunk from the RIFF/WAVE file"""

        fileobj = filething.fileobj

        waveFile = WaveFile(fileobj)

        if 'id3' in waveFile:
            try:
                waveFile['id3'].delete_chunk()
            except ValueError:
                pass

        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Completely removes the ID3 chunk from the RIFF file"""

    try:
        del RiffFile(filething.fileobj)['id3']
    except KeyError:
        pass


class WAVE(FileType):
    """WAVE(filething)

    A Waveform Audio File Format
    (WAVE, or more commonly known as WAV due to its filename extension)

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`WaveStreamInfo`)
    """

    _mimes = ["audio/wav", "audio/wave"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"RIFF") * 2 + endswith(filename, b".wav") +
                endswith(filename, b".wave"))

    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _WaveID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj

        try:
            self.info = WaveStreamInfo(fileobj)
        except ValueError as e:
            raise error(e)

        fileobj.seek(0, 0)

        try:
            self.tags = _WaveID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename


Open = WAVE
