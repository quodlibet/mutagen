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

from mutagen._util import (
    MutagenError,
    delete_bytes,
    insert_bytes,
    resize_bytes,
)


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


class RiffChunk(object):
    """Generic RIFF chunk"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    @classmethod
    def parse(cls, fileobj, parent_chunk=None):
        header = fileobj.read(cls.HEADER_SIZE)
        if len(header) < cls.HEADER_SIZE:
            raise InvalidChunk('Header size < %i' % cls.HEADER_SIZE)

        id, data_size = struct.unpack('<4sI', header)
        try:
            id = id.decode('ascii').rstrip()
        except UnicodeDecodeError as e:
            raise InvalidChunk(e)

        if not is_valid_chunk_id(id):
            raise InvalidChunk('Invalid chunk ID %s' % id)

        return cls.get_class(id)(fileobj, id, data_size, parent_chunk)

    @classmethod
    def get_class(cls, id):
        if id in (u'LIST', u'RIFF'):
            return ListRiffChunk
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
        self._fileobj.write(pack('<I', self.data_size))
        self._calculate_size()
        if self.parent_chunk is not None:
            self.parent_chunk._update_size(self.size - old_size, self)
        if changed_subchunk:
            self._update_sibling_offsets(
                changed_subchunk, old_size - self.size)

    def _calculate_size(self):
        # Consider the padding byte for the total size of this chunk
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
        RIFF chunks are required to be a even number in total length. If
        data_size is odd a padding byte will be added at the end.
        """
        return self.data_size % 2


class ListRiffChunk(RiffChunk):
    """A RIFF chunk containing other chunks.
    This is either a 'LIST' or 'RIFF'
    """

    MIN_DATA_SIZE = 4

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id not in (u'RIFF', u'LIST'):
            raise InvalidChunk('Expected RIFF or LIST chunk, got %s' % id)

        RiffChunk.__init__(self, fileobj, id, data_size, parent_chunk)

        # Lists always store an addtional identifier as 4 bytes
        if data_size < self.MIN_DATA_SIZE:
            raise InvalidChunk('List data size < %i' % self.MIN_DATA_SIZE)

        # Read the list name (e.g. WAVE for RIFF chunks, or INFO for LIST)
        try:
            self.name = fileobj.read(4).decode('ascii')
        except UnicodeDecodeError as e:
            raise error(e)

        # Load all RIFF subchunks
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
                    chunk = RiffChunk.parse(self._fileobj, self)
                except InvalidChunk:
                    break
                self.__subchunks.append(chunk)

                # Calculate the location of the next chunk
                next_offset = chunk.offset + chunk.size
        return self.__subchunks

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the RIFF or LIST"""

        assert isinstance(id_, text_type)

        if not is_valid_chunk_id(id_):
            raise KeyError("Invalid RIFF key.")

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
            pack('<4si', id_.ljust(4).encode('ascii'), data_size))
        self._fileobj.seek(next_offset)
        chunk = RiffChunk.parse(self._fileobj, self)
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


class RiffFile(object):
    """Representation of a RIFF file

        Ref: http://www.johnloomis.org/cpe102/asgn/asgn1/riff.html
      """

    def __init__(self, fileobj):
        # Reset read pointer to beginning of RIFF file
        fileobj.seek(0)

        # RIFF Files always start with the RIFF chunk
        self.root = RiffChunk.parse(fileobj)

        if self.root.id != u'RIFF':
            raise InvalidChunk("Root chunk must be a RIFF chunk, got %s"
                               % self.root.id)

        self.file_type = self.root.name

    def __contains__(self, id_):
        """Check if the RIFF file contains a specific chunk"""

        assert_valid_chunk_id(id_)
        try:
            self[id_]
            return True
        except KeyError:
            return False

    def __getitem__(self, id_):
        """Get a chunk from the RIFF file"""

        assert_valid_chunk_id(id_)
        found_chunk = None
        for chunk in self.root.subchunks():
            if chunk.id == id_:
                found_chunk = chunk
                break
        else:
            raise KeyError("No %r chunk found" % id_)
        return found_chunk

    def delete_chunk(self, id_):
        """Remove a chunk from the RIFF file"""

        assert_valid_chunk_id(id_)
        self[id_].delete()

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the RIFF file"""
        return self.root.insert_chunk(id_, data)
