# Copyright (C) 2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""DSDIFF audio stream information and tags."""

import contextlib
import struct
from io import BytesIO
from typing import Literal, cast, final, override

from mutagen import StreamInfo
from mutagen._file import FileType
from mutagen._filething import FileThing
from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    IffID3,
    InvalidChunk,
)
from mutagen._iff import (
    error as IffError,
)
from mutagen._util import (
    convert_error,
    endswith,
    loadfile,
)
from mutagen.id3._util import ID3NoHeaderError
from mutagen.id3._util import error as ID3Error

__all__ = ["DSDIFF", "Open", "delete"]


class error(IffError):
    pass


# See
#   https://dsd-guide.com/sites/default/files/white-papers/DSDIFF_1.5_Spec.pdf
class DSDIFFChunk(IffChunk):
    """Representation of a single DSDIFF chunk"""

    HEADER_SIZE: int = 12

    @override
    @classmethod
    def parse_header(cls, header: bytes):
        return struct.unpack('>4sQ', header)

    @override
    @classmethod
    def get_class(cls, id: str):
        if id in DSDIFFListChunk.LIST_CHUNK_IDS:
            return DSDIFFListChunk
        elif id == 'DST':
            return DSTChunk
        else:
            return cls

    @override
    def write_new_header(self, id_: str, size: int):
        _ = self._fileobj.write(struct.pack('>4sQ', id_, size))

    @override
    def write_size(self):
        _ = self._fileobj.write(struct.pack('>Q', self.data_size))

@final
class DSDIFFListChunk(DSDIFFChunk, IffContainerChunkMixin):
    """A DSDIFF chunk containing other chunks.
    """

    LIST_CHUNK_IDS: list[Literal['FRM8', 'PROP']] = ['FRM8', 'PROP']

    @override
    def parse_next_subchunk(self):
        return DSDIFFChunk.parse(self._fileobj, self)

    def __init__(self, fileobj: BytesIO, id: Literal['FRM8', 'PROP'], data_size: int, parent_chunk: DSDIFFChunk | None):
        if id not in self.LIST_CHUNK_IDS:
            raise InvalidChunk(f'Not a list chunk: {id}')

        DSDIFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class DSTChunk(DSDIFFChunk, IffContainerChunkMixin):
    """A DSDIFF chunk containing other chunks.
    """

    @override
    def parse_next_subchunk(self):
        return DSDIFFChunk.parse(self._fileobj, self)

    def __init__(self, fileobj: BytesIO, id: Literal['DST'] | str, data_size: int, parent_chunk: DSDIFFChunk | None):
        if id != 'DST':
            raise InvalidChunk(f'Not a DST chunk: {id}')

        DSDIFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container(name_size=0)


class DSDIFFFile(IffFile):
    """Representation of a DSDIFF file"""

    def __init__(self, fileobj: BytesIO):
        super().__init__(DSDIFFChunk, fileobj)

        if self.root.id != 'FRM8':
            raise InvalidChunk(f"Root chunk must be a FRM8 chunk, got {self.root!r}")

@final
class DSDIFFInfo(StreamInfo):

    """DSDIFF stream information.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bits_per_sample (`int`): audio sample size (for DSD this is always 1)
        bitrate (`int`): audio bitrate, in bits per second
        compression (`str`): DSD (uncompressed) or DST
    """

    channels: int = 0
    length: float = 0.0
    sample_rate: int = 0
    bits_per_sample = 1
    bitrate: int = 0
    compression: str | None = None

    @convert_error(IOError, error)
    def __init__(self, fileobj: BytesIO):
        """Raises error"""

        iff = DSDIFFFile(fileobj)
        try:
            prop_chunk: DSDIFFListChunk = iff['PROP']
        except KeyError as e:
            raise error(str(e)) from e

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
                    compression_id, = cast(tuple[bytes],struct.unpack('>4s', data[:4]))
                    self.compression = compression_id.decode('ascii').rstrip()

        if self.sample_rate < 0:
            raise error("Invalid sample rate")

        if self.compression == 'DSD':  # not compressed
            try:
                dsd_chunk: DSDIFFChunk = iff['DSD']
            except KeyError as e:
                raise error(str(e)) from e

            # DSD data has one bit per sample. Eight samples of a channel
            # are clustered together for a channel byte. For multiple channels
            # the channel bytes are interleaved (in the order specified in the
            # CHNL chunk). See DSDIFF spec chapter 3.3.
            sample_count = dsd_chunk.data_size * 8 / (self.channels or 1)

            if self.sample_rate != 0:
                self.length = sample_count / float(self.sample_rate)

            self.bitrate = (self.channels * self.bits_per_sample
                            * self.sample_rate)
        elif self.compression == 'DST':
            try:
                dst_frame = iff['DST']
                dst_frame_info = dst_frame['FRTE']
            except KeyError as e:
                raise error(str(e)) from e

            if dst_frame_info.data_size >= 6:
                data = dst_frame_info.read()
                if len(data) < 6:
                    raise InvalidChunk("Not enough data in FRTE chunk")
                frame_count, frame_rate = cast(tuple[int, int], struct.unpack('>LH', data[:6]))
                if frame_rate:
                    self.length = frame_count / frame_rate

                if frame_count:
                    dst_data_size = dst_frame.data_size - dst_frame_info.size
                    avg_frame_size = dst_data_size / frame_count
                    self.bitrate = avg_frame_size * 8 * frame_rate

    @override
    def pprint(self) -> str:
        return "%d channel DSDIFF (%s) @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.compression, self.bitrate, self.sample_rate,
            self.length)


class _DSDIFFID3(IffID3):
    """A DSDIFF file with ID3v2 tags"""

    @override
    def _load_file(self, fileobj: BytesIO):
        return DSDIFFFile(fileobj)


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing):
    """Completely removes the ID3 chunk from the DSDIFF file"""

    with contextlib.suppress(KeyError):
        del DSDIFFFile(filething.fileobj)['ID3']

@final
class DSDIFF(FileType):
    """DSDIFF(filething)

    An DSDIFF audio file.

    For tagging ID3v2 data is added to a chunk with the ID "ID3 ".

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`DSDIFFInfo`)
    """

    _mimes = ["audio/x-dff"]
    info: DSDIFFInfo
    tags: _DSDIFFID3 | None = None


    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething: FileThing, **kwargs):
        fileobj = filething.fileobj

        try:
            self.tags = _DSDIFFID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e) from e
        else:
            assert self.tags is not None
            self.tags.filename = self.filename

        _ = fileobj.seek(0, 0)
        self.info = DSDIFFInfo(fileobj)

    @override
    def add_tags(self):
        """Add empty ID3 tags to the file."""
        if self.tags is None:
            self.tags = _DSDIFFID3()
        else:
            raise error("an ID3 tag already exists")

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        return header.startswith(b"FRM8") * 2 + endswith(filename, ".dff")


type Open = DSDIFF
