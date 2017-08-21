# -*- coding: utf-8 -*-
# Copyright (C) 2017  Borewit
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Resource Interchange File Format (RIFF)."""

import struct
from abc import abstractmethod, ABCMeta
from struct import pack

from ._compat import text_type

from mutagen._util import resize_bytes, delete_bytes, MutagenError


class error(MutagenError):
    pass


class InvalidChunk(error):
    pass


def is_valid_chunk_id(id):
    """ is_valid_chunk_id(FOURCC)

    Arguments:
        id (FOURCC)
    Returns:
        true if valid; otherwise false

    Check if argument id is valid FOURCC type.
    """

    # looks like this is failing if python is not started with -bb as an argument:
    assert isinstance(id, text_type)

    return ((len(id) <= 4) and (min(id) >= u' ') and
            (max(id) <= u'~'))


def assert_valid_chunk_id(id):
    if not is_valid_chunk_id(id):
        raise ValueError("RIFF-chunk-ID must be four ASCII characters.")

class _ChunkHeader(metaclass=ABCMeta):
    """ Abstract common RIFF chunk header"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    @property
    @abstractmethod
    def _struct(self):
        """ must be implemented in order to instantiate """
        return u'xxxx'

    def __init__(self, fileobj, parent_chunk):
        self.__fileobj = fileobj
        self.parent_chunk = parent_chunk
        self.offset = fileobj.tell()

        header = fileobj.read(self.HEADER_SIZE)
        if len(header) < self.HEADER_SIZE:
            raise InvalidChunk()

        self.id, self.data_size = struct.unpack(self._struct, header)

        try:
            self.id = self.id.decode('ascii')
        except UnicodeDecodeError:
            raise InvalidChunk()

        assert_valid_chunk_id(self.id)

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


class RiffChunkHeader(_ChunkHeader):
    """Representation of the RIFF chunk header"""

    @property
    def _struct(self):
        return '>4sI'  # Size in Big-Endian

    def __init__(self, fileobj, parent_chunk=None):
        _ChunkHeader.__init__(self, fileobj, parent_chunk)


class RiffSubchunk(_ChunkHeader):
    """Representation of a RIFF Subchunk"""

    @property
    def _struct(self):
        return '<4sI'  # Size in Little-Endian

    def __init__(self, fileobj, parent_chunk=None):
        _ChunkHeader.__init__(self, fileobj, parent_chunk)


class RiffFile(object):
    """Representation of a RIFF file

        Ref: http://www.johnloomis.org/cpe102/asgn/asgn1/riff.html
      """

    def __init__(self, fileobj):
        self._fileobj = fileobj
        self.__subchunks = {}

        # Reset read pointer to beginning of RIFF file
        fileobj.seek(0)

        # RIFF Files always start with the RIFF chunk
        self._riffChunk = RiffChunkHeader(fileobj)

        if (self._riffChunk.id != u'RIFF'):
            raise KeyError("Root chunk should be a RIFF chunk.")

        # Read the RIFF file Type
        self.fileType = fileobj.read(4).decode('ascii')

        # Load all RIFF subchunks
        while True:
            try:
                chunk = RiffSubchunk(fileobj, self._riffChunk)
            except InvalidChunk:
                break
            # Normalize ID3v2-tag-chunk to lowercase
            if chunk.id == u'ID3 ':
                chunk.id = u'id3 '
            self.__subchunks[chunk.id] = chunk

            # Calculate the location of the next chunk,
            # considering the pad byte
            self.__next_offset = chunk.offset + chunk.size
            self.__next_offset += self.__next_offset % 2
            fileobj.seek(self.__next_offset)

    def __contains__(self, id_):
        """Check if the IFF file contains a specific chunk"""

        assert_valid_chunk_id(id_)

        return id_ in self.__subchunks

    def __getitem__(self, id_):
        """Get a chunk from the IFF file"""

        assert_valid_chunk_id(id_)

        try:
            return self.__subchunks[id_]
        except KeyError:
            raise KeyError(
                "%r has no %r chunk" % (self._fileobj, id_))

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""

        assert_valid_chunk_id(id_)

        self.__subchunks.pop(id_).delete()

    def insert_chunk(self, id_):
        """Insert a new chunk at the end of the IFF file"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("RIFF key must be four ASCII characters.")

        self.fileobj.seek(self.__next_offset)
        self.fileobj.write(pack('>4si', id_.ljust(4).encode('ascii'), 0))
        self.fileobj.seek(self.__next_offset)
        chunk = RiffChunkHeader(self.fileobj, self[u'RIFF'])
        self[u'RIFF']._update_size(self[u'RIFF'].data_size + chunk.size)

        self.__subchunks[id_] = chunk
        self.__next_offset = chunk.offset + chunk.size
