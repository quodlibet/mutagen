# -*- coding: utf-8 -*-
# Copyright (C) 2017  Borewit
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
    assert isinstance(id, text_type)

    return ((len(id) <= 4) and (min(id) >= u' ') and
            (max(id) <= u'~'))


class RiffChunkHeader(object):
    """Representation of a common RIFF chunk header"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    def __init__(self, fileobj):
        self.__fileobj = fileobj
        self.offset = fileobj.tell()

        header = fileobj.read(self.HEADER_SIZE)
        if len(header) < self.HEADER_SIZE:
            raise InvalidChunk()

        self.id, self.data_size = struct.unpack('>4sI', header)

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

    def _update_size(self, data_size):
        """Update the size of the chunk"""

        self.__fileobj.seek(self.offset + 4)
        self.__fileobj.write(pack('>I', data_size))
        self.data_size = data_size
        self.size = data_size + self.HEADER_SIZE

    def resize(self, new_data_size):
        """Resize the file and update the chunk sizes"""

        resize_bytes(
            self.__fileobj, self.data_size, new_data_size, self.data_offset)
        self._update_size(new_data_size)


class RiffFile(object):
    """Representation of a RIFF file

        Ref: http://www.johnloomis.org/cpe102/asgn/asgn1/riff.html
      """

    def __init__(self, fileobj):
        self.__fileobj = fileobj
        self.__riffChunks = {}

        # Reset read pointer to beginning of RIFF file
        fileobj.seek(0)

        # RIFF Files always start with the RIFF chunk
        chunk = RiffChunkHeader(fileobj)

        if (chunk.id != u'RIFF'):
            raise KeyError("First chunk should be a RIFF chunk.")

        # Read the RIFF file Type
        self.fileType = fileobj.read(4).decode('ascii')

        # Load all of the remaining RIFF-chunks
        while True:
            try:
                self.__riffChunks[chunk.id] = chunk
                self.__next_offset = chunk.offset + chunk.size
                fileobj.seek(self.__next_offset)
                chunk = RiffChunkHeader(fileobj)
            except InvalidChunk:
                break

            # Calculate the location of the next chunk,
            # considering the pad byte
            # self.__next_offset += self.__next_offset % 2

    def __contains__(self, id_):
        """Check if the IFF file contains a specific chunk"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("RIFF key must be four ASCII characters.")

        return id_ in self.__riffChunks

    def __getitem__(self, id_):
        """Get a chunk from the IFF file"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("RIFF key must be four ASCII characters.")

        try:
            return self.__riffChunks[id_]
        except KeyError:
            raise KeyError(
                "%r has no %r chunk" % (self.__fileobj, id_))

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("RIFF key must be four ASCII characters.")

        self.__riffChunks.pop(id_).delete()

    def insert_chunk(self, id_):
        """Insert a new chunk at the end of the IFF file"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("RIFF key must be four ASCII characters.")

        self.__fileobj.seek(self.__next_offset)
        self.__fileobj.write(pack('>4si', id_.ljust(4).encode('ascii'), 0))
        self.__fileobj.seek(self.__next_offset)
        chunk = RiffChunkHeader(self.__fileobj, self[u'RIFF'])
        self[u'RIFF']._update_size(self[u'RIFF'].data_size + chunk.size)

        self.__riffChunks[id_] = chunk
        self.__next_offset = chunk.offset + chunk.size
