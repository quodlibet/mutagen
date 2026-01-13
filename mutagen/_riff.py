# Copyright (C) 2017  Borewit
# Copyright (C) 2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Resource Interchange File Format (RIFF)."""

import struct
from io import BytesIO
from struct import pack
from typing import override

from _typeshed import ReadableBuffer

from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    InvalidChunk,
)


class RiffChunk(IffChunk):
    """Generic RIFF chunk"""

    name: str

    @classmethod
    @override
    def parse_header(cls, header: ReadableBuffer):
        return struct.unpack('<4sI', header)

    @classmethod
    @override
    def get_class(cls, id: str):
        if id in ('LIST', 'RIFF'):
            return RiffListChunk
        else:
            return cls

    @override
    def write_new_header(self, id_: bytes | str, size: int) -> None:
        _ = self._fileobj.write(pack('<4sI', id_, size))

    @override
    def write_size(self) -> None:
        _ = self._fileobj.write(pack('<I', self.data_size))


class RiffListChunk(RiffChunk, IffContainerChunkMixin):
    """A RIFF chunk containing other chunks.
    This is either a 'LIST' or 'RIFF'
    """

    @override
    def parse_next_subchunk(self) -> RiffChunk:
        return RiffChunk.parse(self._fileobj, self)

    def __init__(self, fileobj: BytesIO, id: str, data_size: int, parent_chunk: RiffChunk | None) -> None:
        if id not in ('RIFF', 'LIST'):
            raise InvalidChunk(f'Expected RIFF or LIST chunk, got {id}')

        RiffChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class RiffFile(IffFile):
    """Representation of a RIFF file"""

    file_type: str

    def __init__(self, fileobj: BytesIO) -> None:
        super().__init__(RiffChunk, fileobj)

        if self.root.id != 'RIFF':
            raise InvalidChunk(f"Root chunk must be a RIFF chunk, got {self.root.id}")

        assert isinstance(self.root, RiffListChunk)

        self.file_type = self.root.name
