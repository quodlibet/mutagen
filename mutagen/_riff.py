# Copyright (C) 2017  Borewit
# Copyright (C) 2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Resource Interchange File Format (RIFF)."""

import struct
from collections import defaultdict, deque
from struct import pack

from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    InvalidChunk,
    error,
)


class RiffChunk(IffChunk):
    """Generic RIFF chunk"""

    @classmethod
    def parse_header(cls, header):
        return struct.unpack('<4sI', header)

    @classmethod
    def get_class(cls, id):
        if id == 'RF64':
            return RF64RootChunk
        if id in (u'LIST', u'RIFF'):
            return RiffListChunk
        else:
            return cls

    def write_new_header(self, id_, size):
        self._fileobj.write(pack('<4sI', id_, size))

    def write_size(self):
        self._fileobj.write(pack('<I', self.data_size))


class RiffListChunk(RiffChunk, IffContainerChunkMixin):
    """A RIFF chunk containing other chunks.
    This is either a 'LIST' or 'RIFF'
    """

    def parse_next_subchunk(self):
        return RiffChunk.parse(self._fileobj, self)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id not in (u'RIFF', u'LIST'):
            raise InvalidChunk('Expected RIFF or LIST chunk, got %s' % id)

        RiffChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class RF64Chunk(RiffChunk):
    """A RIFF chunk whose size may be stored in the RF64 ds64 chunk."""

    @classmethod
    def get_class(cls, id):
        return RF64ListChunk if id == 'LIST' else cls

    def __init__(self, fileobj, id, data_size, parent_chunk):
        root = parent_chunk
        while root.parent_chunk is not None:
            root = root.parent_chunk
        self._size_offset = None
        if id == 'data' and not root._data_seen:
            root._data_seen = True
            if data_size == 0xffffffff:
                data_size = root._data_size
                self._size_offset = root.data_offset + 20
        elif data_size == 0xffffffff:
            if not root._sizes[id]:
                raise error('Missing RF64 size for %s' % id)
            data_size, self._size_offset = root._sizes[id].popleft()
        super().__init__(fileobj, id, data_size, parent_chunk)

    def write_size(self):
        if self._size_offset is None:
            super().write_size()
        else:
            self._fileobj.seek(self._size_offset)
            self._fileobj.write(pack('<Q', self.data_size))


class RF64ListChunk(RF64Chunk, IffContainerChunkMixin):
    def __init__(self, fileobj, id, data_size, parent_chunk):
        super().__init__(fileobj, id, data_size, parent_chunk)
        self.init_container()

    def parse_next_subchunk(self):
        return RF64Chunk.parse(self._fileobj, self)


class RF64RootChunk(RiffChunk, IffContainerChunkMixin):
    """RF64 container, owning the extended sizes defined by EBU Tech 3306."""

    def __init__(self, fileobj, id, data_size, parent_chunk):
        offset = fileobj.tell()
        fileobj.seek(offset + 4)
        header = fileobj.read(8)
        if len(header) != 8:
            raise InvalidChunk('Missing RF64 ds64 chunk')
        chunk_id, size = struct.unpack('<4sI', header)
        if chunk_id != b'ds64' or size < 28:
            raise InvalidChunk('Invalid RF64 ds64 chunk')
        data = fileobj.read(28)
        if len(data) != 28:
            raise InvalidChunk('Truncated RF64 ds64 chunk')
        riff_size, self._data_size, _, count = struct.unpack('<QQQI', data)
        if count > (size - 28) // 12:
            raise InvalidChunk('Truncated RF64 size table')
        self._sizes = defaultdict(deque)
        for _ in range(count):
            entry_offset = fileobj.tell()
            entry = fileobj.read(12)
            if len(entry) != 12:
                raise InvalidChunk('Truncated RF64 size table')
            chunk_id, chunk_size = struct.unpack('<4sQ', entry)
            try:
                name = chunk_id.decode('ascii').rstrip()
            except UnicodeDecodeError as e:
                raise InvalidChunk(e)
            self._sizes[name].append((chunk_size, entry_offset + 4))
        self._data_seen = False
        self._extended_size = data_size == 0xffffffff
        if self._extended_size:
            data_size = riff_size
        fileobj.seek(offset)
        super().__init__(fileobj, id, data_size, parent_chunk)
        self.init_container()

    def parse_next_subchunk(self):
        return RF64Chunk.parse(self._fileobj, self)

    def write_size(self):
        if self.data_size >= 0xffffffff:
            self._extended_size = True
        self._fileobj.write(pack(
            '<I', 0xffffffff if self._extended_size else self.data_size))
        self._fileobj.seek(self.data_offset + 12)
        self._fileobj.write(pack('<Q', self.data_size))


class RiffFile(IffFile):
    """Representation of a RIFF file"""

    def __init__(self, fileobj):
        super().__init__(RiffChunk, fileobj)

        if self.root.id not in ('RIFF', 'RF64'):
            raise InvalidChunk("Root chunk must be a RIFF or RF64 chunk, got %s"
                               % self.root.id)

        self.file_type = self.root.name
