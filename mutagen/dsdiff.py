# -*- coding: utf-8 -*-
# Copyright (C) 2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""DSDIFF audio stream information and tags."""

import struct

from mutagen import StreamInfo
from mutagen._file import FileType
from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    InvalidChunk,
    error as IffError,
)
from mutagen._util import (
    convert_error,
    loadfile,
    endswith,
)


__all__ = ["DSDIFF", "Open"]


class error(IffError):
    pass


# See
#   https://dsd-guide.com/sites/default/files/white-papers/DSDIFF_1.5_Spec.pdf
class DSDIFFChunk(IffChunk):
    """Representation of a single DSDIFF chunk"""

    HEADER_SIZE = 12

    @classmethod
    def parse_header(cls, header):
        return struct.unpack('>4sQ', header)

    @classmethod
    def get_class(cls, id):
        if id in DSDIFFListChunk.LIST_CHUNK_IDS:
            return DSDIFFListChunk
        elif id == 'DST':
            return DSTChunk
        else:
            return cls

    def write_new_header(self, id_, size):
        self._fileobj.write(struct.pack('>4sQ', id_, size))

    def write_size(self):
        self._fileobj.write(struct.pack('>Q', self.data_size))


class DSDIFFListChunk(DSDIFFChunk, IffContainerChunkMixin):
    """A DSDIFF chunk containing other chunks.
    """

    LIST_CHUNK_IDS = ['FRM8', 'PROP']

    def parse_next_subchunk(self):
        return DSDIFFChunk.parse(self._fileobj, self)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id not in self.LIST_CHUNK_IDS:
            raise InvalidChunk('Not a list chunk: %s' % id)

        DSDIFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class DSTChunk(DSDIFFChunk, IffContainerChunkMixin):
    """A DSDIFF chunk containing other chunks.
    """

    def parse_next_subchunk(self):
        return DSDIFFChunk.parse(self._fileobj, self)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id != 'DST':
            raise InvalidChunk('Not a DST chunk: %s' % id)

        DSDIFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container(name_size=0)


class DSDIFFFile(IffFile):
    """Representation of a DSDIFF file"""

    def __init__(self, fileobj):
        super().__init__(DSDIFFChunk, fileobj)

        if self.root.id != u'FRM8':
            raise InvalidChunk("Root chunk must be a FRM8 chunk, got %r"
                               % self.root)


class DSDIFFInfo(StreamInfo):

    """DSDIFF stream information.
    The length of the stream is just a guess and might not be correct.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bits_per_sample (`int`): audio sample size (for DSD this is always 1)
        bitrate (`int`): audio bitrate, in bits per second
        compression (`str`): DSD (uncompressed) or DST
    """

    channels = 0
    length = 0
    sample_rate = 0
    bits_per_sample = 1
    bitrate = 0
    compression = None

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        iff = DSDIFFFile(fileobj)
        try:
            prop_chunk = iff['PROP']
        except KeyError as e:
            raise error(str(e))

        if prop_chunk.name == 'SND ':
            for chunk in prop_chunk.subchunks():
                if chunk.id == 'FS' and chunk.data_size == 4:
                    data = chunk.read()
                    if len(data) < 4:
                        raise InvalidChunk("Not enough data in FS chunk")
                    self.sample_rate, = struct.unpack('>L', data[:4])
                elif chunk.id == 'CHNL' and chunk.data_size >= 2:
                    data = chunk.read()
                    if len(data) < 2:
                        raise InvalidChunk("Not enough data in CHNL chunk")
                    self.channels, = struct.unpack('>H', data[:2])
                elif chunk.id == 'CMPR' and chunk.data_size >= 4:
                    data = chunk.read()
                    if len(data) < 4:
                        raise InvalidChunk("Not enough data in CMPR chunk")
                    compression_id, = struct.unpack('>4s', data[:4])
                    self.compression = compression_id.decode('ascii').rstrip()

        if self.sample_rate < 0:
            raise error("Invalid sample rate")

        if self.compression == 'DSD':  # not compressed
            try:
                dsd_chunk = iff['DSD']
            except KeyError as e:
                raise error(str(e))

            # DSD data has one bit per sample. Eight samples of a channel
            # are clustered together for a channel byte. For multiple channels
            # the channel bytes are interleaved (in the order specified in the
            # CHNL chunk). See DSDIFF spec chapter 3.3.
            sample_count = dsd_chunk.data_size * 8 / (self.channels or 1)

            if self.sample_rate != 0:
                self.length = sample_count / float(self.sample_rate)
        elif self.compression == 'DST':
            try:
                dst_frame_info = iff['DST']['FRTE']
            except KeyError as e:
                raise error(str(e))

            if dst_frame_info.data_size >= 6:
                data = dst_frame_info.read()
                if len(data) < 6:
                    raise InvalidChunk("Not enough data in FRTE chunk")
                frame_count, frame_rate = struct.unpack('>LH', data[:6])
                if frame_rate:
                    self.length = frame_count / frame_rate

        self.bitrate = self.channels * self.bits_per_sample * self.sample_rate

    def pprint(self):
        return u"%d channel DSDIFF (%s) @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.compression, self.bitrate, self.sample_rate,
            self.length)


class DSDIFF(FileType):
    """DSDIFF(filething)

    Arguments:
        filething (filething)

    Load DSDIFF files.

    Tagging is not supported.

    Attributes:
        info (`DSDIFFInfo`)
    """

    _mimes = ["audio/x-dff"]

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething):
        self.info = DSDIFFInfo(filething.fileobj)

    def add_tags(self):
        raise error("doesn't support tags")

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"FRM8") * 2 + endswith(filename, ".dff")


Open = DSDIFF
