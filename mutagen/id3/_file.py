# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

import struct
from enum import IntEnum
from io import BytesIO
from typing import override

import mutagen
from mutagen._filething import FileThing
from mutagen._tags import PaddingFunction, PaddingInfo
from mutagen._util import (
    convert_error,
    delete_bytes,
    insert_bytes,
    loadfile,
    read_full,
)
from mutagen.id3._frames import Frame

from ._id3v1 import MakeID3v1, find_id3v1
from ._tags import ID3Header, ID3Tags
from ._util import BitPaddedInt, ID3NoHeaderError, ID3SaveConfig, ID3UnsupportedVersionError, error


class ID3v1SaveOptions(IntEnum):

    REMOVE = 0
    """ID3v1 tags will be removed"""

    UPDATE = 1
    """ID3v1 tags will be updated but not added"""

    CREATE = 2
    """ID3v1 tags will be created and/or updated"""


class ID3(ID3Tags, mutagen.Metadata):
    """ID3(filething=None)

    A file with an ID3v2 tag.

    If any arguments are given, the :meth:`load` is called with them. If no
    arguments are given then an empty `ID3` object is created.

    ::

        ID3("foo.mp3")
        # same as
        t = ID3()
        t.load("foo.mp3")

    Arguments:
        filething (filething): or `None`

    Attributes:
        version (tuple[int]): ID3 tag version as a tuple
        unknown_frames (list[bytes]): raw frame data of any unknown frames
            found
        size (int): the total size of the ID3 tag, including the header
    """

    __module__ = "mutagen.id3"

    _header: ID3Header | None = None
    _version: tuple[int, int, int] | tuple[int, int] = (2, 4, 0)

    unknown_frames: list[bytes]
    _padding: int | None = None
    filename: str | None = None


    @property
    def version(self):
        if self._header is not None:
            return self._header.version
        return self._version

    @version.setter
    def version(self, value: tuple[int, int, int] | tuple[int, int]):
        self._version = value

    @property
    def f_unsynch(self) -> bool:
        if self._header is not None:
            return self._header.f_unsynch
        return False

    @property
    def f_extended(self) -> bool:
        if self._header is not None:
            return self._header.f_extended
        return False

    @property
    def size(self) -> int:
        if self._header is not None:
            return self._header.size
        return 0

    def _pre_load_header(self, fileobj: BytesIO):
        # XXX: for aiff to adjust the offset..
        pass

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething: FileThing, known_frames: dict[str, type[Frame]] | None=None, translate: bool=True, v2_version: int=4,
             load_v1: bool=True, **kwargs: object):
        """Load tags from a filename.

        Args:
            filename (filething): filename or file object to load tag data from
            known_frames (Dict[`mutagen.text`, `Frame`]): dict mapping frame
                IDs to Frame objects
            translate (bool): Update all tags to ID3v2.3/4 internally. If you
                intend to save, this must be true or you have to
                call update_to_v23() / update_to_v24() manually.
            v2_version (int): if update_to_v23 or update_to_v24 get called
                (3 or 4)
            load_v1 (bool): Load tags from ID3v1 header if present. If both
                ID3v1 and ID3v2 headers are present, combine the tags from
                the two, with ID3v2 having precedence.

                .. versionadded:: 1.42

        Example of loading a custom frame::

            my_frames = dict(mutagen.id3.Frames)
            class XMYF(Frame): ...
            my_frames["XMYF"] = XMYF
            mutagen.id3.ID3(filename, known_frames=my_frames)
        """

        fileobj = filething.fileobj

        if v2_version not in (3, 4):
            raise ValueError("Only 3 and 4 possible for v2_version")

        self.unknown_frames = []
        self._header = None
        self._padding = 0

        self._pre_load_header(fileobj)

        try:
            self._header = ID3Header(fileobj)
        except (ID3NoHeaderError, ID3UnsupportedVersionError):
            if not load_v1:
                raise

            frames, offset = find_id3v1(fileobj, v2_version, known_frames)
            if frames is None:
                raise

            self.version = ID3Header._V11
            for v in frames.values():
                if len(self.getall(v.HashKey)) == 0:
                    self.add(v)
        else:
            # XXX: attach to the header object so we have it in spec parsing..
            if known_frames is not None:
                self._header._known_frames = known_frames

            size = self.size - 10
            if self.f_extended:
                size -= 4 + len(self._header._extdata)
            data = read_full(fileobj, size)
            remaining_data = self._read(self._header, data)
            self._padding = len(remaining_data)

            if load_v1:
                v1v2_ver = 4 if self.version[1] == 4 else 3
                frames, offset = find_id3v1(fileobj, v1v2_ver, known_frames)
                if frames:
                    for v in frames.values():
                        if len(self.getall(v.HashKey)) == 0:
                            self.add(v)

        if translate:
            if v2_version == 3:
                self.update_to_v23()
            else:
                self.update_to_v24()

    def _prepare_data(self, fileobj: BytesIO, start: int, available: int, v2_version: int, v23_sep: str,
                      pad_func: PaddingFunction | None):

        if v2_version not in (3, 4):
            raise ValueError("Only 3 or 4 allowed for v2_version")

        config = ID3SaveConfig(v2_version, v23_sep)
        framedata = self._write(config)

        needed = len(framedata) + 10

        _ = fileobj.seek(0, 2)
        trailing_size = fileobj.tell() - start

        info = PaddingInfo(available - needed, trailing_size)
        new_padding = info._get_padding(pad_func)
        if new_padding < 0:
            raise error("invalid padding")
        new_size = needed + new_padding

        new_framesize = BitPaddedInt.to_str(new_size - 10, width=4)
        header = struct.pack(
            '>3sBBB4s', b'ID3', v2_version, 0, 0, new_framesize)

        data = header + framedata
        assert new_size >= len(data)
        data += (new_size - len(data)) * b'\x00'
        assert new_size == len(data)

        return data

    @convert_error(IOError, error)
    @loadfile(writable=True, create=True)
    def save(self, filething: FileThing | None=None, v1: int=1, v2_version: int=4, v23_sep: str='/',
             padding: PaddingFunction | None=None, **kwargs):
        """save(filething=None, v1=1, v2_version=4, v23_sep='/', padding=None)

        Save changes to a file.

        Args:
            filething (filething):
                Filename to save the tag to. If no filename is given,
                the one most recently loaded is used.
            v1 (ID3v1SaveOptions):
                if 0, ID3v1 tags will be removed.
                if 1, ID3v1 tags will be updated but not added.
                if 2, ID3v1 tags will be created and/or updated
            v2_version (int):
                version of ID3v2 tags (3 or 4).
            v23_sep (text):
                the separator used to join multiple text values
                if v2_version == 3. Defaults to '/' but if it's None
                will be the ID3v2v2.4 null separator.
            padding (:obj:`mutagen.PaddingFunction`)

        Raises:
            mutagen.MutagenError

        By default Mutagen saves ID3v2.4 tags. If you want to save ID3v2.3
        tags, you must call method update_to_v23 before saving the file.

        The lack of a way to update only an ID3v1 tag is intentional.
        """
        assert filething is not None
        f = filething.fileobj

        try:
            header = ID3Header(filething.fileobj)
        except ID3NoHeaderError:
            old_size = 0
        else:
            old_size = header.size

        data = self._prepare_data(
            f, 0, old_size, v2_version, v23_sep, padding)
        new_size = len(data)

        if (old_size < new_size):
            insert_bytes(f, new_size - old_size, old_size)
        elif (old_size > new_size):
            delete_bytes(f, old_size - new_size, new_size)
        _ = f.seek(0)
        _ = f.write(data)

        self.__save_v1(f, v1)

    def __save_v1(self, f: BytesIO, v1: ID3v1SaveOptions):
        tag, offset = find_id3v1(f)
        has_v1 = tag is not None

        _ = f.seek(offset, 2)
        if v1 == ID3v1SaveOptions.UPDATE and has_v1 or v1 == ID3v1SaveOptions.CREATE:
            f.write(MakeID3v1(self))
        else:
            f.truncate()

    @loadfile(writable=True)
    def delete(self, filething: FileThing | None =None, delete_v1: bool=True, delete_v2: bool=True):
        """delete(filething=None, delete_v1=True, delete_v2=True)

        Remove tags from a file.

        Args:
            filething (filething): A filename or `None` to use the one used
                when loading.
            delete_v1 (bool): delete any ID3v1 tag
            delete_v2 (bool): delete any ID3v2 tag

        If no filename is given, the one most recently loaded is used.
        """

        delete(filething, delete_v1, delete_v2)
        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing, delete_v1: bool=True, delete_v2: bool=True):
    """Remove tags from a file.

    Args:
        delete_v1 (bool): delete any ID3v1 tag
        delete_v2 (bool): delete any ID3v2 tag

    Raises:
        mutagen.MutagenError: In case deleting failed
    """

    f = filething.fileobj

    if delete_v1:
        tag, offset = find_id3v1(f)
        if tag is not None:
            f.seek(offset, 2)
            f.truncate()

    # technically an insize=0 tag is invalid, but we delete it anyway
    # (primarily because we used to write it)
    if delete_v2:
        f.seek(0, 0)
        idata = f.read(10)
        try:
            id3, vmaj, vrev, flags, insize = struct.unpack('>3sBBB4s', idata)
        except struct.error:
            pass
        else:
            insize = BitPaddedInt(insize)
            if id3 == b'ID3' and insize >= 0:
                delete_bytes(f, insize + 10, 0)


class ID3FileType(mutagen.FileType):
    """ID3FileType(filething, ID3=None, **kwargs)

    An unknown type of file with ID3 tags.

    Args:
        filething (filething): A filename or file-like object
        ID3 (ID3): An ID3 subclass to use for tags.

    Raises:
        mutagen.MutagenError: In case loading the file failed

    Load stream and tag information from a file.

    A custom tag reader may be used in instead of the default
    mutagen.id3.ID3 object, e.g. an EasyID3 reader.
    """

    __module__ = "mutagen.id3"

    ID3 = ID3

    class _Info(mutagen.StreamInfo):
        length: float = 0.0

        def __init__(self, fileobj: BytesIO, offset: int | None =None):
            pass

        @staticmethod
        def pprint():
            return "Unknown format with ID3 tag"

    info: type[mutagen.StreamInfo] | None = None

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes) -> int:
        return header.startswith(b"ID3")

    @override
    def add_tags(self, ID3=None):
        """Add an empty ID3 tag to the file.

        Args:
            ID3 (ID3): An ID3 subclass to use or `None` to use the one
                that used when loading.

        A custom tag reader may be used in instead of the default
        `ID3` object, e.g. an `mutagen.easyid3.EasyID3` reader.
        """

        if ID3 is None:
            ID3 = self.ID3
        if self.tags is None:
            self.ID3 = ID3
            self.tags = ID3()
        else:
            raise error("an ID3 tag already exists")

    @loadfile()
    def load(self, filething: FileThing, ID3=None, **kwargs):
        # see __init__ for docs

        fileobj = filething.fileobj

        if ID3 is None:
            ID3 = self.ID3
        else:
            # If this was initialized with EasyID3, remember that for
            # when tags are auto-instantiated in add_tags.
            self.ID3 = ID3

        try:
            self.tags = ID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None

        if self.tags is not None:
            try:
                offset = self.tags.size
            except AttributeError:
                offset = None
        else:
            offset = None

        self.info = self._Info(fileobj, offset)
