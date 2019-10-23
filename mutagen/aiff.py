# -*- coding: utf-8 -*-
# Copyright (C) 2014  Evan Purkhiser
#               2014  Ben Ockmore
#               2019  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""AIFF audio stream information and tags."""

import sys
import struct
from struct import pack

from ._compat import endswith, text_type, reraise
from mutagen import StreamInfo, FileType

from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import (
    MutagenError,
    convert_error,
    delete_bytes,
    insert_bytes,
    loadfile,
    resize_bytes,
)

__all__ = ["AIFF", "Open", "delete"]


class error(MutagenError):
    pass


class InvalidChunk(error):
    pass


# based on stdlib's aifc
_HUGE_VAL = 1.79769313486231e+308


def is_valid_chunk_id(id):
    assert isinstance(id, text_type)

    return ((len(id) <= 4) and (min(id) >= u' ') and
            (max(id) <= u'~'))


def assert_valid_chunk_id(id):

    assert isinstance(id, text_type)

    if not is_valid_chunk_id(id):
        raise ValueError("AIFF key must be four ASCII characters.")


def read_float(data):  # 10 bytes
    expon, himant, lomant = struct.unpack('>hLL', data)
    sign = 1
    if expon < 0:
        sign = -1
        expon = expon + 0x8000
    if expon == himant == lomant == 0:
        f = 0.0
    elif expon == 0x7FFF:
        f = _HUGE_VAL
    else:
        expon = expon - 16383
        f = (himant * 0x100000000 + lomant) * pow(2.0, expon - 63)
    return sign * f


class IFFChunk(object):
    """Representation of a single IFF chunk"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    @classmethod
    def parse(cls, fileobj, parent_chunk=None):
        header = fileobj.read(cls.HEADER_SIZE)
        if len(header) < cls.HEADER_SIZE:
            raise InvalidChunk('Header size < %i' % cls.HEADER_SIZE)

        id, data_size = struct.unpack('>4sI', header)
        try:
            id = id.decode('ascii').rstrip()
        except UnicodeDecodeError as e:
            raise InvalidChunk(e)

        if not is_valid_chunk_id(id):
            raise InvalidChunk('Invalid chunk ID %s' % id)

        return cls.get_class(id)(fileobj, id, data_size, parent_chunk)

    @classmethod
    def get_class(cls, id):
        if id == 'FORM':
            return FormIFFChunk
        else:
            return cls

    def __init__(self, fileobj, id, data_size, parent_chunk):
        self._fileobj = fileobj
        self.id = id
        self.data_size = data_size
        self.parent_chunk = parent_chunk
        self.data_offset = fileobj.tell()
        self.offset = self.data_offset - self.HEADER_SIZE
        self._calculate_size()

    def read(self):
        """Read the chunks data"""

        self._fileobj.seek(self.data_offset)
        return self._fileobj.read(self.data_size)

    def write(self, data):
        """Write the chunk data"""

        if len(data) > self.data_size:
            raise ValueError

        self._fileobj.seek(self.data_offset)
        self._fileobj.write(data)
        # Write the padding bytes
        padding = self.padding()
        if padding:
            self._fileobj.seek(self.data_offset + self.data_size)
            self._fileobj.write(b'\x00' * padding)

    def delete(self):
        """Removes the chunk from the file"""

        delete_bytes(self._fileobj, self.size, self.offset)
        if self.parent_chunk is not None:
            self.parent_chunk._remove_subchunk(self)
        self._fileobj.flush()

    def _update_size(self, size_diff, changed_subchunk=None):
        """Update the size of the chunk"""

        old_size = self.size
        self.data_size += size_diff
        self._fileobj.seek(self.offset + 4)
        self._fileobj.write(pack('>I', self.data_size))
        self._calculate_size()
        if self.parent_chunk is not None:
            self.parent_chunk._update_size(self.size - old_size, self)
        if changed_subchunk:
            self._update_sibling_offsets(
                changed_subchunk, old_size - self.size)

    def _calculate_size(self):
        self.size = self.HEADER_SIZE + self.data_size + self.padding()
        assert self.size % 2 == 0

    def resize(self, new_data_size):
        """Resize the file and update the chunk sizes"""

        padding = new_data_size % 2
        resize_bytes(self._fileobj, self.data_size + self.padding(),
                     new_data_size + padding, self.data_offset)
        size_diff = new_data_size - self.data_size
        self._update_size(size_diff)
        self._fileobj.flush()

    def padding(self):
        """Returns the number of padding bytes (0 or 1).
        IFF chunks are required to be a even number in total length. If
        data_size is odd a padding byte will be added at the end.
        """
        return self.data_size % 2


class FormIFFChunk(IFFChunk):
    """A IFF chunk containing other chunks.
    This is either a 'LIST' or 'RIFF'
    """

    MIN_DATA_SIZE = 4

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id != u'FORM':
            raise InvalidChunk('Expected FORM chunk, got %s' % id)

        IFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)

        # Lists always store an addtional identifier as 4 bytes
        if data_size < self.MIN_DATA_SIZE:
            raise InvalidChunk('FORM data size < %i' % self.MIN_DATA_SIZE)

        # Read the FORM id (usually AIFF)
        try:
            self.name = fileobj.read(4).decode('ascii')
        except UnicodeDecodeError as e:
            raise error(e)

        # Load all IFF subchunks
        self.__subchunks = []

    def subchunks(self):
        """Returns a list of all subchunks.
        The list is lazily loaded on first access.
        """
        if not self.__subchunks:
            next_offset = self.data_offset + 4
            while next_offset < self.offset + self.size:
                self._fileobj.seek(next_offset)
                try:
                    chunk = IFFChunk.parse(self._fileobj, self)
                except InvalidChunk:
                    break
                self.__subchunks.append(chunk)

                # Calculate the location of the next chunk
                next_offset = chunk.offset + chunk.size
        return self.__subchunks

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the FORM chunk"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("Invalid IFF key.")

        next_offset = self.offset + self.size
        size = self.HEADER_SIZE
        data_size = 0
        if data:
            data_size = len(data)
            padding = data_size % 2
            size += data_size + padding
        insert_bytes(self._fileobj, size, next_offset)
        self._fileobj.seek(next_offset)
        self._fileobj.write(
            pack('>4si', id_.ljust(4).encode('ascii'), data_size))
        self._fileobj.seek(next_offset)
        chunk = IFFChunk.parse(self._fileobj, self)
        self._update_size(chunk.size)
        if data:
            chunk.write(data)
        self.subchunks().append(chunk)
        self._fileobj.flush()
        return chunk

    def _remove_subchunk(self, chunk):
        assert chunk in self.__subchunks
        self._update_size(-chunk.size, chunk)
        self.__subchunks.remove(chunk)

    def _update_sibling_offsets(self, changed_subchunk, size_diff):
        """Update the offsets of subchunks after `changed_subchunk`.
        """
        index = self.__subchunks.index(changed_subchunk)
        sibling_chunks = self.__subchunks[index + 1:len(self.__subchunks)]
        for sibling in sibling_chunks:
            sibling.offset -= size_diff
            sibling.data_offset -= size_diff


class IFFFile(object):
    """Representation of a IFF file"""

    def __init__(self, fileobj):
        # AIFF Files always start with the FORM chunk which contains a 4 byte
        # ID before the start of other chunks
        fileobj.seek(0)
        self.root = IFFChunk.parse(fileobj)

        if self.root.id != u'FORM':
            raise InvalidChunk("Root chunk must be a RIFF chunk, got %s"
                               % self.root.id)

    def __contains__(self, id_):
        """Check if the IFF file contains a specific chunk"""

        assert_valid_chunk_id(id_)
        try:
            self[id_]
            return True
        except KeyError:
            return False

    def __getitem__(self, id_):
        """Get a chunk from the IFF file"""

        assert_valid_chunk_id(id_)
        if id_ == 'FORM':  # For backwards compatibility
            return self.root
        found_chunk = None
        for chunk in self.root.subchunks():
            if chunk.id == id_:
                found_chunk = chunk
                break
        else:
            raise KeyError("No %r chunk found" % id_)
        return found_chunk

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""

        assert_valid_chunk_id(id_)
        self.delete_chunk(id_)

    def delete_chunk(self, id_):
        """Remove a chunk from the RIFF file"""

        assert_valid_chunk_id(id_)
        self[id_].delete()

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the IFF file"""

        assert_valid_chunk_id(id_)
        return self.root.insert_chunk(id_, data)


class AIFFInfo(StreamInfo):
    """AIFFInfo()

    AIFF audio stream information.

    Information is parsed from the COMM chunk of the AIFF file

    Attributes:
        length (`float`): audio length, in seconds
        bitrate (`int`): audio bitrate, in bits per second
        channels (`int`): The number of audio channels
        sample_rate (`int`): audio sample rate, in Hz
        bits_per_sample (`int`): The audio sample size
    """

    length = 0
    bitrate = 0
    channels = 0
    sample_rate = 0

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        iff = IFFFile(fileobj)
        try:
            common_chunk = iff[u'COMM']
        except KeyError as e:
            raise error(str(e))

        data = common_chunk.read()
        if len(data) < 18:
            raise error

        info = struct.unpack('>hLh10s', data[:18])
        channels, frame_count, sample_size, sample_rate = info

        self.sample_rate = int(read_float(sample_rate))
        self.bits_per_sample = sample_size
        self.sample_size = sample_size  # For backward compatibility
        self.channels = channels
        self.bitrate = channels * sample_size * self.sample_rate
        self.length = frame_count / float(self.sample_rate)

    def pprint(self):
        return u"%d channel AIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _IFFID3(ID3):
    """A AIFF file with ID3v2 tags"""

    def _pre_load_header(self, fileobj):
        try:
            fileobj.seek(IFFFile(fileobj)[u'ID3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3NoHeaderError("No ID3 chunk")

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething=None, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the AIFF file"""

        fileobj = filething.fileobj

        iff_file = IFFFile(fileobj)

        if u'ID3' not in iff_file:
            iff_file.insert_chunk(u'ID3')

        chunk = iff_file[u'ID3']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        chunk.resize(len(data))
        chunk.write(data)

    @loadfile(writable=True)
    def delete(self, filething=None):
        """Completely removes the ID3 chunk from the AIFF file"""

        delete(filething)
        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Completely removes the ID3 chunk from the AIFF file"""

    try:
        del IFFFile(filething.fileobj)[u'ID3']
    except KeyError:
        pass


class AIFF(FileType):
    """AIFF(filething)

    An AIFF audio file.

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`AIFFInfo`)
    """

    _mimes = ["audio/aiff", "audio/x-aiff"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"FORM") * 2 + endswith(filename, b".aif") +
                endswith(filename, b".aiff") + endswith(filename, b".aifc"))

    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _IFFID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj

        try:
            self.tags = _IFFID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename

        fileobj.seek(0, 0)
        self.info = AIFFInfo(fileobj)


Open = AIFF
