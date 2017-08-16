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
from struct import pack

from ._compat import endswith, text_type, reraise

from mutagen import StreamInfo, FileType

from mutagen.id3 import ID3
from mutagen._riff import RiffFile, RiffChunkHeader
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import resize_bytes, delete_bytes, MutagenError, loadfile, \
    convert_error

__all__ = ["WAVE", "Open", "delete"]


class error(MutagenError):
    pass


class InvalidChunk(error):
    pass


def is_valid_chunk_id(id_):
    assert isinstance(id_, text_type)

    return ((len(id_) <= 4) and (min(id_) >= u' ') and
            (max(id_) <= u'~'))


def check_id(id_):
    if not is_valid_chunk_id(id_):
           raise KeyError("RIFF/WAVE-chunk-Id must be four ASCII characters.")


class WaveChunk(object):
    """Representation of a common WaveChunk"""

    #  Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    def __init__(self, fileobj, parent_chunk=None):
        self.__fileobj = fileobj
        self.parent_chunk = parent_chunk
        self.offset = fileobj.tell()

        header = fileobj.read(self.HEADER_SIZE)
        if len(header) < self.HEADER_SIZE:
            raise InvalidChunk()

        self.id, self.data_size = struct.unpack('<4sI', header)

        try:
            self.id = self.id.decode('ascii')
        except UnicodeDecodeError:
            raise InvalidChunk()

        if not is_valid_chunk_id(self.id):
            raise InvalidChunk()

        self.size = self.HEADER_SIZE + self.data_size
        self.data_offset = fileobj.tell()

    def read(self):
        """Read the chunks data"""

        self.__fileobj.seek(self.data_offset)
        return self.__fileobj.read(self.data_size)

    def write(self, data):
        """Write the chunk data"""

        if len(data) > self.data_size:
            raise ValueError

        self.__fileobj.seek(self.data_offset)
        self.__fileobj.write(data)

    def delete(self):
        """Removes the chunk from the file"""

        delete_bytes(self.__fileobj, self.size, self.offset)
        if self.parent_chunk is not None:
            self.parent_chunk._update_size(
                self.parent_chunk.data_size - self.size)

    def _update_size(self, data_size):
        """Update the size of the chunk"""

        self.__fileobj.seek(self.offset + 4)
        self.__fileobj.write(pack('>I', data_size))
        if self.parent_chunk is not None:
            size_diff = self.data_size - data_size
            self.parent_chunk._update_size(
                self.parent_chunk.data_size - size_diff)
        self.data_size = data_size
        self.size = data_size + self.HEADER_SIZE

    def resize(self, new_data_size):
        """Resize the file and update the chunk sizes"""

        resize_bytes(
            self.__fileobj, self.data_size, new_data_size, self.data_offset)
        self._update_size(new_data_size)


class WaveFile(RiffFile):
    """Representation of a RIFF/WAVE file"""

    def __init__(self, fileobj):
        RiffFile.__init__(self, fileobj)

        if self.fileType != u'WAVE':
            raise KeyError("Expected RIFF/WAVE.")

        self.__wavChunks = {}

        # RIFF Files always start with the RIFF chunk which contains a 4 byte
        # ID before the start of other chunks
        fileobj.seek(0)
        self.__wavChunks[u'RIFF'] = RiffChunkHeader(fileobj)

        # Skip past the 4 byte chunk id ('RIFF')
        fileobj.seek(RiffChunkHeader.HEADER_SIZE + 4)

        # Where the next chunk can be located. We need to keep track of this
        # since the size indicated in the RIFF header may not match up with the
        # offset determined from the size of the last chunk in the file
        self.__next_offset = fileobj.tell()

        # Load all of the chunks
        while True:
            try:
                chunk = WaveChunk(fileobj, self[u'RIFF'])
            except InvalidChunk:
                break
            self.__wavChunks[chunk.id] = chunk

            # Calculate the location of the next chunk,
            # considering the pad byte
            self.__next_offset = chunk.offset + chunk.size
            self.__next_offset += self.__next_offset % 2
            fileobj.seek(self.__next_offset)

    def __contains__(self, id_):
        """Check if the RIFF/WAVE file contains a specific chunk"""

        check_id(id_)

        return id_ in self.__wavChunks

    def __getitem__(self, id_):
        """Get a chunk from the RIFF/WAVE file"""

        check_id(id_)

        try:
            return self.__wavChunks[id_]
        except KeyError:
            raise KeyError(
                "%r has no %r chunk" % (self.__fileobj, id_))

    def __delitem__(self, id_):
        """Remove a chunk from the RIFF/WAVE file"""

        check_id(id_)

        self.__wavChunks.pop(id_).delete()

    def insert_chunk(self, id_):
        """Insert a new chunk at the end of the RIFF/WAVE file"""

        check_id(id_)

        self._RiffFile__fileobj.seek(self.__next_offset)
        self._RiffFile__fileobj.write(pack('<4si', id_.ljust(4).encode('ascii'), 0))
        self._RiffFile__fileobj.seek(self.__next_offset)
        chunk = RiffChunkHeader(self._RiffFile__fileobj)
        self[u'RIFF']._update_size(self[u'RIFF'].data_size + chunk.size)

        self.__wavChunks[id_] = chunk
        self.__next_offset = chunk.offset + chunk.size


class WaveStreamInfo(StreamInfo):
    """RiffWave()

    Microsoft WAVE soundfile information.

    Information is parsed from the 'data' & 'id3 ' / 'ID3 ' chunk of the RIFF/WAVE file

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

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        waveFile = WaveFile(fileobj)
        try:
            waveFormatChunk = waveFile[u'fmt ']
        except KeyError as e:
            raise error(str(e))

        data = waveFormatChunk.read()

        #  RIFF: http://soundfile.sapp.org/doc/WaveFormat/
        #  Python struct.unpack:
        #    https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
        info = struct.unpack('<hhLLhh', data[:16])
        self.audioFormat, self.channels, self.sample_rate, byte_rate, \
            block_align, self.sample_size = info
        self.bitrate = self.channels * block_align * self.sample_rate

        try:
            waveDataChunk = waveFile[u'data']
        except KeyError as e:
            raise error(str(e))

        self.number_of_samples = waveDataChunk.data_size / block_align
        self.length = self.number_of_samples / self.sample_rate

    def pprint(self):
        return u"%d channel AIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _WaveID3(ID3):
    """A Wave file with ID3v2 tags"""

    def _pre_load_header(self, fileobj):
        waveFile = WaveFile(fileobj)
        if 'id3 ' in waveFile:
            fileobj.seek(waveFile['id3 '].data_offset)
        elif 'ID3 ' in waveFile:
            fileobj.seek(waveFile['ID3 '].data_offset)
        else:
            raise ID3NoHeaderError("No ID3 chunk")
    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the Wave/RIFF file"""

        fileobj = filething.fileobj

        wave_file = WaveFile(fileobj)

        if u'id3 ' not in wave_file:
            wave_file.insert_chunk(u'id3 ')

        chunk = wave_file[u'id3 ']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        new_size = len(data)
        new_size += new_size % 2  # pad byte
        assert new_size % 2 == 0
        chunk.resize(new_size)
        data += (new_size - len(data)) * b'\x00'
        assert new_size == len(data)
        chunk.write(data)

    @loadfile(writable=True)
    def delete(self, filething):
        """Completely removes the ID3 chunk from the RIFF/WAVE file"""

        fileobj = filething.fileobj

        waveFile = WaveFile(fileobj)

        if 'id3 ' in waveFile:
            waveFile['id3 '].delete()
        if 'ID3 ' in waveFile:
            waveFile['ID3 '].delete()

        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Completely removes the ID3 chunk from the AIFF file"""

    try:
        del RiffFile(filething.fileobj)[u'ID3']
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
            self.tags = _WaveID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename

        fileobj.seek(0, 0)
        self.info = WaveStreamInfo(fileobj)


Open = WAVE
