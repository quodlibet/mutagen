#! /usr/bin/env python
#
# mutagen aims to be an all purpose media tagging library
# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id$
#

version = (0, 0, -1)

"""
mutagen aims to be an all purpose tagging library.

    import mutagen.[format]
    metadata = mutagen.[format].Open(filename)

metadata is now acts like a dictionary of tags in the file. tags are
generally a list of string-like values, but may have additional methods
available depending on tag or format. They may also be entirely different
objects for certain keys, again depending on format.
"""

class Metadata(dict):
    """Abstract dict-like object that each format inherits for managing
    metadata."""

    def __init__(self, filename=None, fileobj=None):
        """Initializes a tag structure. If fileobj is specified it is the
        source and must include a "read" method or an AttributeError will be
        raised. Otherwise if filename is specified it must exist and be
        readable or normal exceptions will be thrown. Finally for various kinds
        of bad data, a subclass of ValueError may be thrown."""
        raise NotImplementedError

    def save(self, filename=None):
        """Save metadata to previously referenced or newly specified file"""
        raise NotImplementedError

    def delete(self):
        """Remove tags from the open file"""
        raise NotImplementedError

    def _insert_space(fobj, size, offset):
        """insert size bytes of empty space starting at offset. fobj must be
        an open file object, open rb+ or equivalent."""
        from mmap import mmap
        assert 0 < size
        assert 0 <= offset
        fobj.seek(0, 2)
        filesize = fobj.tell()
        movesize = filesize - offset
        fobj.write('\x00' * size)
        fobj.flush()
        map = mmap(fobj.fileno(), filesize + size)
        map.move(offset+size, offset, movesize)
    _insert_space = staticmethod(_insert_space)

    def _delete_bytes(fobj, size, offset):
        """delete size bytes of data starting at offset. fobj must be
        an open file object, open rb+ or equivalent."""
        from mmap import mmap
        assert 0 < size
        assert 0 <= offset
        fobj.seek(0, 2)
        filesize = fobj.tell()
        movesize = filesize - offset - size
        assert 0 <= movesize
        if movesize > 0:
            fobj.flush()
            map = mmap(fobj.fileno(), filesize)
            map.move(offset, offset+size, movesize)
        fobj.truncate(filesize - size)
        fobj.flush()
    _delete_bytes = staticmethod(_delete_bytes)

