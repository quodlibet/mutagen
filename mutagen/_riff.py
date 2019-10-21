# -*- coding: utf-8 -*-
# Copyright (C) 2017  Borewit
# Copyright (C) 2019  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Resource Interchange File Format (RIFF)."""

import struct
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

    assert isinstance(id, text_type), \
        'id is of type %s, must be text_type: %r' % (type(id), id)

    if len(id) < 3 or len(id) > 4:
        return False

    for c in id:
        if c < u'!' or c > u'~':
            return False

    return True


#  Assert FOURCC formatted valid
def assert_valid_chunk_id(id):
    if not is_valid_chunk_id(id):
        raise ValueError("Invalid RIFF-chunk-ID.")


class RiffChunkHeader(object):
    """ RIFF chunk header"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    def __init__(self, fileobj, parent_chunk):
        self.__fileobj = fileobj
        self.parent_chunk = parent_chunk
        self.offset = fileobj.tell()

        header = fileobj.read(self.HEADER_SIZE)
        if len(header) < self.HEADER_SIZE:
            raise InvalidChunk('Header size < %i' % self.HEADER_SIZE)

        self.id, self.data_size = struct.unpack('<4sI', header)
        self.data_offset = fileobj.tell()

        try:
            self.id = self.id.decode('ascii').rstrip()
        except UnicodeDecodeError as e:
            raise InvalidChunk(e)

        if not is_valid_chunk_id(self.id):
            raise InvalidChunk('Invalid chunk ID %s' % self.id)

        self._calculate_size()

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
        # Write the padding bytes
        padding = self.padding()
        if padding:
            self.__fileobj.seek(self.data_offset + self.data_size + 1)
            self.__fileobj.write(b'\x00' * padding)

    def delete(self):
        """Removes the chunk from the file"""

        delete_bytes(self.__fileobj, self.size, self.offset)
        if self.parent_chunk is not None:
            self.parent_chunk._update_size(
                self.parent_chunk.data_size - self.size)

    def _update_size(self, data_size):
        """Update the size of the chunk"""

        self.__fileobj.seek(self.offset + 4)
        self.__fileobj.write(pack('<I', data_size))
        if self.parent_chunk is not None:
            new_padding = data_size % 2
            size_diff = (self.data_size + self.padding()) \
                - (data_size + new_padding)
            self.parent_chunk._update_size(
                self.parent_chunk.data_size - size_diff)
        self.data_size = data_size
        self._calculate_size()

    def _calculate_size(self):
        self.size = self.HEADER_SIZE + self.data_size + self.padding()
        assert self.size % 2 == 0

    def resize(self, new_data_size):
        """Resize the file and update the chunk sizes"""

        padding = new_data_size % 2
        resize_bytes(self.__fileobj, self.data_size + self.padding(),
                     new_data_size + padding, self.data_offset)
        self._update_size(new_data_size)

    def padding(self):
        """Returns the number of padding bytes (0 or 1).
        IFF chunks are required to be a even number in total length. If
        data_size is odd a padding byte will be added at the end.
        """
        return self.data_size % 2


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
        self._riff_chunk = RiffChunkHeader(fileobj, parent_chunk=None)

        if (self._riff_chunk.id != 'RIFF'):
            raise KeyError("Root chunk should be a RIFF chunk.")

        # Read the RIFF file Type
        try:
            self.file_type = fileobj.read(4).decode('ascii')
        except UnicodeDecodeError as e:
            raise error(e)
        self.__next_offset = fileobj.tell()

        # Load all RIFF subchunks
        while True:
            try:
                chunk = RiffChunkHeader(fileobj, self._riff_chunk)
            except InvalidChunk:
                break
            # Normalize ID3v2-tag-chunk to lowercase
            if chunk.id == 'ID3':
                chunk.id = 'id3'
            self.__subchunks[chunk.id] = chunk

            # Calculate the location of the next chunk,
            # considering the pad byte
            self.__next_offset = chunk.offset + chunk.size
            fileobj.seek(self.__next_offset)

    def __contains__(self, id_):
        """Check if the RIFF file contains a specific chunk"""

        assert_valid_chunk_id(id_)
        return id_ in self.__subchunks

    def __getitem__(self, id_):
        """Get a chunk from the RIFF file"""

        assert_valid_chunk_id(id_)

        try:
            return self.__subchunks[id_]
        except KeyError:
            raise KeyError("%r has no %r chunk" % (self._fileobj, id_))

    def delete_chunk(self, id_):
        """Remove a chunk from the RIFF file"""

        assert_valid_chunk_id(id_)
        self.__subchunks.pop(id_).delete()

    def insert_chunk(self, id_):
        """Insert a new chunk at the end of the RIFF file"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("Invalid RIFF key.")

        self._fileobj.seek(self.__next_offset)
        self._fileobj.write(pack('<4si', id_.ljust(4).encode('ascii'), 0))
        self._fileobj.seek(self.__next_offset)
        chunk = RiffChunkHeader(self._fileobj, self._riff_chunk)
        self._riff_chunk._update_size(self._riff_chunk.data_size + chunk.size)

        self.__subchunks[id_] = chunk
        self.__next_offset = chunk.offset + chunk.size
