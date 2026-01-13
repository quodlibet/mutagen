# Copyright (C) 2017  Borewit
# Copyright (C) 2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Microsoft WAVE/RIFF audio file/stream information and tags."""

import contextlib
import struct
import sys
from io import BytesIO
from typing import cast, final, override

from mutagen import FileType, StreamInfo
from mutagen._filething import FileThing
from mutagen._iff import error as IffError
from mutagen._riff import InvalidChunk, RiffChunk, RiffFile
from mutagen._tags import PaddingFunction
from mutagen._util import (
    convert_error,
    endswith,
    loadfile,
    reraise,
)
from mutagen.id3._file import ID3
from mutagen.id3._util import ID3NoHeaderError
from mutagen.id3._util import error as ID3Error

__all__ = ["WAVE", "Open", "delete"]


class error(IffError):
    """WAVE stream parsing errors."""


class _WaveFile(RiffFile):
    """Representation of a RIFF/WAVE file"""

    def __init__(self, fileobj: BytesIO):
        super().__init__(fileobj)

        if self.file_type != 'WAVE':
            raise error("Expected RIFF/WAVE.")

        # Normalize ID3v2-tag-chunk to lowercase
        if 'ID3' in self:
            self['ID3'].id = 'id3'

@final
class WaveStreamInfo(StreamInfo):
    """WaveStreamInfo()

    Microsoft WAVE file information.

    Information is parsed from the 'fmt' & 'data'chunk of the RIFF/WAVE file

    Attributes:
        length (`float`): audio length, in seconds
        bitrate (`int`): audio bitrate, in bits per second
        channels (`int`): The number of audio channels
        sample_rate (`int`): audio sample rate, in Hz
        bits_per_sample (`int`): The audio sample size
    """

    length: float = 0.0
    bitrate: int = 0
    channels: int = 0
    sample_rate: int = 0
    bits_per_sample: int = 0
    _number_of_samples: int = 0
    audio_format: int = 0

    SIZE = 16

    @convert_error(IOError, error)
    def __init__(self, fileobj: BytesIO):
        """Raises error"""

        wave_file = _WaveFile(fileobj)
        try:
            format_chunk = wave_file['fmt']
            assert isinstance(format_chunk, RiffChunk)
        except KeyError as e:
            raise error(str(e)) from e

        data: bytes = format_chunk.read()
        if len(data) < 16:
            raise InvalidChunk()

        # RIFF: http://soundfile.sapp.org/doc/WaveFormat/
        #  Python struct.unpack:
        #    https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
        info = cast(tuple[int, int, int, int, int, int], struct.unpack('<HHLLHH', data[:self.SIZE]))
        self.audio_format, self.channels, self.sample_rate, _, block_align, self.bits_per_sample = info
        self.bitrate = self.channels * self.bits_per_sample * self.sample_rate

        # Calculate duration
        self._number_of_samples = 0
        if block_align > 0:
            try:
                data_chunk = wave_file['data']
                self._number_of_samples = int(data_chunk.data_size / block_align)
            except KeyError:
                pass

        if self.sample_rate > 0:
            self.length = self._number_of_samples / self.sample_rate

    @override
    def pprint(self):
        return "%d channel RIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _WaveID3(ID3):
    """A Wave file with ID3v2 tags"""

    @override
    def _pre_load_header(self, fileobj: BytesIO):
        try:
            _ = fileobj.seek(_WaveFile(fileobj)['id3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3NoHeaderError("No ID3 chunk") from None

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething: FileThing, v1: int=1, v2_version: int=4, v23_sep: str='/', padding: PaddingFunction | None=None):
        """Save ID3v2 data to the Wave/RIFF file"""

        fileobj = filething.fileobj
        wave_file = _WaveFile(fileobj)

        if 'id3' not in wave_file:
            _ = wave_file.insert_chunk('id3')

        chunk = wave_file['id3']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        chunk.resize(len(data))
        chunk.write(data)

    @override
    def delete(self, filething: FileThing):
        """Completely removes the ID3 chunk from the RIFF/WAVE file"""

        delete(filething)
        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing):
    """Completely removes the ID3 chunk from the RIFF/WAVE file"""

    with contextlib.suppress(KeyError):
        _WaveFile(filething.fileobj).delete_chunk('id3')


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

    _mimes: list[str] = ["audio/wav", "audio/wave"]
    tags: _WaveID3 | None
    info: WaveStreamInfo | None

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        filename = filename.lower()

        return (header.startswith(b"RIFF") + (header[8:12] == b'WAVE')
                + endswith(filename, b".wav") + endswith(filename, b".wave"))

    @override
    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _WaveID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething: FileThing, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj
        self.info = WaveStreamInfo(fileobj)
        _ = fileobj.seek(0, 0)

        try:
            self.tags = _WaveID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e) from e
        else:
            assert self.tags is not None
            self.tags.filename = self.filename


type Open = WAVE
