# Copyright (C) 2017  Boris Pruessmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write DSF audio stream information and tags."""


import struct
import sys
from io import BytesIO
from typing import Literal, override

from mutagen import FileType, StreamInfo
from mutagen._filething import FileThing
from mutagen._tags import PaddingFunction
from mutagen._util import (
    MutagenError,
    cdata,
    convert_error,
    endswith,
    loadfile,
    reraise,
)
from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError
from mutagen.id3._util import error as ID3Error

__all__ = ["DSF", "Open", "delete"]


class error(MutagenError):
    pass


class DSFChunk:
    """A generic chunk of a DSFFile."""

    chunk_offset: int = 0
    chunk_header: bytes = b"    "
    chunk_size: int = -1

    fileobj: BytesIO

    def __init__(self, fileobj: BytesIO, create: bool=False):
        self.fileobj = fileobj

        if not create:
            self.chunk_offset = fileobj.tell()
            self.load()

    def load(self) -> None:
        raise NotImplementedError

    def write(self) -> None:
        raise NotImplementedError


class DSDChunk(DSFChunk):
    """Represents the first chunk of a DSF file"""

    CHUNK_SIZE: int = 28

    chunk_header: bytes
    chunk_size: int

    total_size: int = 0
    offset_metdata_chunk: int = 0

    def __init__(self, fileobj: BytesIO, create: bool =False):
        super().__init__(fileobj, create)

        if create:
            self.chunk_header = b"DSD "
            self.chunk_size = DSDChunk.CHUNK_SIZE

    @override
    def load(self):
        data = self.fileobj.read(DSDChunk.CHUNK_SIZE)
        if len(data) != DSDChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"DSD ":
            raise error("DSF dsd header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size != DSDChunk.CHUNK_SIZE:
            raise error("DSF dsd header size mismatch")

        self.total_size = cdata.ulonglong_le(data[12:20])
        self.offset_metdata_chunk = cdata.ulonglong_le(data[20:28])

    @override
    def write(self):
        f = BytesIO()
        _ = f.write(self.chunk_header)
        _ = f.write(struct.pack("<Q", DSDChunk.CHUNK_SIZE))
        _ = f.write(struct.pack("<Q", self.total_size))
        _ = f.write(struct.pack("<Q", self.offset_metdata_chunk))

        _ = self.fileobj.seek(self.chunk_offset)
        _ = self.fileobj.write(f.getvalue())

    def pprint(self):
        return (f"DSD Chunk (Total file size = {self.total_size}, Pointer to Metadata chunk = {self.offset_metdata_chunk})")


class FormatChunk(DSFChunk):

    CHUNK_SIZE: Literal[52] = 52

    VERSION: Literal[1] = 1

    FORMAT_DSD_RAW: Literal[0] = 0
    """Format ID: DSD Raw"""

    format_version: int = VERSION
    format_id: int = FORMAT_DSD_RAW
    channel_type: int = 1
    channel_num: int = 1
    sampling_frequency: int = 2822400
    bits_per_sample: int = 1
    sample_count: int = 0
    block_size_per_channel: int = 4096

    chunk_header: bytes
    chunk_size: int
    length: float


    def __init__(self, fileobj: BytesIO, create: bool =False):
        super().__init__(fileobj, create)

        if create:
            self.chunk_header = b"fmt "
            self.chunk_size = FormatChunk.CHUNK_SIZE

    @override
    def load(self):
        data = self.fileobj.read(FormatChunk.CHUNK_SIZE)
        if len(data) != FormatChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"fmt ":
            raise error("DSF fmt header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size != FormatChunk.CHUNK_SIZE:
            raise error("DSF dsd header size mismatch")

        self.format_version = cdata.uint_le(data[12:16])
        if self.format_version != FormatChunk.VERSION:
            raise error("Unsupported format version")

        self.format_id = cdata.uint_le(data[16:20])
        if self.format_id != FormatChunk.FORMAT_DSD_RAW:
            raise error("Unsupported format ID")

        self.channel_type = cdata.uint_le(data[20:24])
        self.channel_num = cdata.uint_le(data[24:28])
        self.sampling_frequency = cdata.uint_le(data[28:32])
        self.bits_per_sample = cdata.uint_le(data[32:36])
        self.sample_count = cdata.ulonglong_le(data[36:44])

    def pprint(self):
        return f"fmt Chunk (Channel Type = {self.channel_type}, Channel Num = {self.channel_num}, Sampling Frequency = {self.sampling_frequency}, {self.length:.2f} seconds)"


class DataChunk(DSFChunk):

    CHUNK_SIZE: Literal[12] = 12

    data: str = ""
    chunk_header: bytes
    chunk_size: int

    def __init__(self, fileobj: BytesIO, create: bool =False):
        super().__init__(fileobj, create)

        if create:
            self.chunk_header = b"data"
            self.chunk_size = DataChunk.CHUNK_SIZE

    @override
    def load(self):
        data = self.fileobj.read(DataChunk.CHUNK_SIZE)
        if len(data) != DataChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"data":
            raise error("DSF data header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size < DataChunk.CHUNK_SIZE:
            raise error("DSF data header size mismatch")

    def pprint(self):
        return "data Chunk (Chunk Offset = %d, Chunk Size = %d)" % (
            self.chunk_offset, self.chunk_size)


class _DSFID3(ID3):
    """A DSF file with ID3v2 tags"""

    @convert_error(IOError, error)
    def _pre_load_header(self, fileobj: BytesIO):
        _ = fileobj.seek(0)
        id3_location = DSDChunk(fileobj).offset_metdata_chunk
        if id3_location == 0:
            raise ID3NoHeaderError("File has no existing ID3 tag")

        _ = fileobj.seek(id3_location)

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething: FileThing | None=None, v2_version: int=4, v23_sep: str='/', padding: PaddingFunction | None=None):
        """Save ID3v2 data to the DSF file"""

        assert filething is not None
        fileobj = filething.fileobj
        _ = fileobj.seek(0)

        dsd_header = DSDChunk(fileobj)
        if dsd_header.offset_metdata_chunk == 0:
            # create a new ID3 chunk at the end of the file
            _ = fileobj.seek(0, 2)

            # store reference to ID3 location
            dsd_header.offset_metdata_chunk = fileobj.tell()
            dsd_header.write()

        try:
            data = self._prepare_data(
                fileobj, dsd_header.offset_metdata_chunk, self.size,
                v2_version, v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        _ = fileobj.seek(dsd_header.offset_metdata_chunk)
        _ = fileobj.write(data)
        _ = fileobj.truncate()

        # Update total file size
        dsd_header.total_size = fileobj.tell()
        dsd_header.write()


class DSFInfo(StreamInfo):
    """DSF audio stream information.

    Information is parsed from the fmt chunk of the DSF file.

    Attributes:
        length (`float`): audio length, in seconds.
        channels (`int`): The number of audio channels.
        sample_rate (`int`):
            Sampling frequency, in Hz.
            (2822400, 5644800, 11289600, or 22579200)
        bits_per_sample (`int`): The audio sample size.
        bitrate (`int`): The audio bitrate.
    """

    def __init__(self, fmt_chunk: FormatChunk):
        self.fmt_chunk: FormatChunk = fmt_chunk

    @property
    @override
    def length(self) -> float:
        return float(self.fmt_chunk.sample_count) / self.sample_rate

    @property
    def channels(self)-> int:
        return self.fmt_chunk.channel_num

    @property
    def sample_rate(self) -> int:
        return self.fmt_chunk.sampling_frequency

    @property
    def bits_per_sample(self) -> int:
        return self.fmt_chunk.bits_per_sample

    @property
    def bitrate(self) -> int:
        return self.sample_rate * self.bits_per_sample * self.channels

    @override
    def pprint(self) -> str:
        return "%d channel DSF @ %d bits, %s Hz, %.2f seconds" % (
            self.channels, self.bits_per_sample, self.sample_rate, self.length)


class DSFFile:

    dsd_chunk: DSDChunk
    fmt_chunk: FormatChunk
    data_chunk: DataChunk

    def __init__(self, fileobj: BytesIO):
        self.dsd_chunk = DSDChunk(fileobj)
        self.fmt_chunk = FormatChunk(fileobj)
        self.data_chunk = DataChunk(fileobj)


class DSF(FileType):
    """An DSF audio file.

    Arguments:
        filething (filething)

    Attributes:
        info (`DSFInfo`)
        tags (`mutagen.id3.ID3Tags` or `None`)
    """

    _mimes: list[str] = ["audio/dsf"]
    info: DSFInfo | None
    tags: ID3 | None

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        return header.startswith(b"DSD ") * 2 + \
            endswith(filename.lower(), ".dsf")

    @override
    def add_tags(self):
        """Add a DSF tag block to the file."""

        if self.tags is None:
            self.tags = _DSFID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething: FileThing, **kwargs):
        dsf_file = DSFFile(filething.fileobj)

        try:
            self.tags = _DSFID3(filething.fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e) from e
        else:
            assert self.tags is not None
            self.tags.filename = self.filename

        self.info = DSFInfo(dsf_file.fmt_chunk)

    @loadfile(writable=True)
    def delete(self, filething: FileThing | None=None):
        self.tags = None
        delete(filething)


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing):
    """Remove tags from a file.

    Args:
        filething (filething)
    Raises:
        mutagen.MutagenError
    """

    dsf_file = DSFFile(filething.fileobj)

    assert dsf_file.dsd_chunk is not None

    if dsf_file.dsd_chunk.offset_metdata_chunk != 0:
        id3_location = dsf_file.dsd_chunk.offset_metdata_chunk
        dsf_file.dsd_chunk.offset_metdata_chunk = 0
        dsf_file.dsd_chunk.write()

        _ = filething.fileobj.seek(id3_location)
        _ = filething.fileobj.truncate()


Open = DSF
