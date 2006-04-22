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

"""Mutagen aims to be an all purpose tagging library.

    import mutagen.[format]
    metadata = mutagen.[format].Open(filename)

metadata acts like a dictionary of tags in the file. Tags are generally a
list of string-like values, but may have additional methods available
depending on tag or format. They may also be entirely different objects
for certain keys, again depending on format.
"""

version = (1, 1, 0)

from mutagen._util import DictMixin

class Metadata(dict):
    """An abstract dict-like object.

    Metadata is the base class for most of the tag formats in Mutagen.
    """

    def __init__(self, filename=None):
        raise NotImplementedError

    def save(self, filename=None):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def _insert_space(fobj, size, offset):
        """Insert size bytes of empty space starting at offset.

        fobj must be an open file object, open rb+ or
        equivalent. Mutagen tries to use mmap to resize the file, but
        falls back to a significantly slower method if mmap fails.
        """
        from mmap import mmap
        assert 0 < size
        assert 0 <= offset
        fobj.seek(0, 2)
        filesize = fobj.tell()
        movesize = filesize - offset
        fobj.write('\x00' * size)
        fobj.flush()
        map = mmap(fobj.fileno(), filesize + size)
        try:
            map.move(offset+size, offset, movesize)
        except ValueError: # handle broken python on 64bit
            map.close()
            fobj.truncate(filesize)

            fobj.seek(offset)
            backbuf = fobj.read(size)
            if len(backbuf) < size:
                fobj.write('\x00' * (size - len(backbuf)))
            while len(backbuf) == size:
                frontbuf = fobj.read(size)
                fobj.seek(-len(frontbuf), 1)
                fobj.write(backbuf)
                backbuf = frontbuf
            fobj.write(backbuf)

    _insert_space = staticmethod(_insert_space)

    def _delete_bytes(fobj, size, offset):
        """Delete size bytes of empty space starting at offset.

        fobj must be an open file object, open rb+ or
        equivalent. Mutagen tries to use mmap to resize the file, but
        falls back to a significantly slower method if mmap fails.
        """
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
            try:
                map.move(offset, offset+size, movesize)
            except ValueError: # handle broken python on 64bit
                fobj.seek(offset + size)
                buf = fobj.read(size)
                while len(buf):
                    fobj.seek(-len(buf) - size, 1)
                    fobj.write(buf)
                    fobj.seek(size, 1)
                    buf = fobj.read(size)
        fobj.truncate(filesize - size)
        fobj.flush()
    _delete_bytes = staticmethod(_delete_bytes)

class FileType(DictMixin):
    """An abstract object wrapping tags and audio stream information.

    Attributes:
    info -- stream information (length, bitrate, sample rate)
    tags -- metadata tags, if any

    Each file format has different potential tags and stream
    information.

    FileTypes implement an interface very similar to Metadata; the
    dict interface, save, load, and delete calls on a FileType call
    the appropriate methods on its tag data.
    """

    info = None
    tags = None

    def __getitem__(self, key):
        """Look up a metadata tag key.

        If the file has no tags at all, a KeyError is raised.
        """
        if self.tags is None: raise KeyError, key
        else: return self.tags[key]

    def __setitem__(self, key, value):
        """Set a metadata tag.

        If the file has no tags, an appropriate format is added (but
        not written until save is called).
        """
        if self.tags is None: self.add_tags()
        self.tags[key] = value

    def __delitem__(self, key):
        """Delete a metadata tag key.

        If the file has no tags at all, a KeyError is raised.
        """
        if self.tags is None: raise KeyError, key
        else: del(self.tags[key])

    def keys(self):
        """Return a list of keys in the metadata tag.

        If the file has no tags at all, an empty list is returned.
        """
        if self.tags is None: return []
        else: return self.tags.keys()

    def delete(self, filename=None):
        """Remove tags from a file."""
        if self.tags is not None:
            if filename is None: filename = self.filename
            self.tags.delete(filename)

    def save(self, filename=None, **kwargs):
        """Save metadata tags.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None: filename = self.filename
        if self.tags is not None:
            self.tags.save(filename, **kwargs)
        else: raise ValueError("no tags in file")
