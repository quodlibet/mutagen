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

version = (1, 5, 1)

import mutagen._util

class Metadata(dict):
    """An abstract dict-like object.

    Metadata is the base class for most of the tag formats in Mutagen.
    """

    def __init__(self, filename=None):
        raise NotImplementedError

    def save(self, filename=None):
        raise NotImplementedError

    def delete(self, filename=None):
        raise NotImplementedError

    _insert_space = staticmethod(mutagen._util.insert_bytes)
    _delete_bytes = staticmethod(mutagen._util.delete_bytes)

class FileType(mutagen._util.DictMixin):
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

    def pprint(self):
        """Print stream information and comment key=value pairs."""
        stream = self.info.pprint()
        try: tags = self.tags.pprint()
        except AttributeError:
            return stream
        else: return stream + ((tags and "\n" + tags) or "")

def File(filename, options=None):
    """Guess the type of the file and try to open it.

    The file type is decided by several things, such as the first 128
    bytes (which usually contains a file type identifier), the
    filename extension, and the presence of existing tags.

    If no appropriate type could be found, None is returned.
    """

    if options is None:
        from mutagen.oggtheora import OggTheora
        from mutagen.oggvorbis import OggVorbis
        from mutagen.oggflac import OggFLAC
        from mutagen.flac import FLAC
        from mutagen.mp3 import MP3
        from mutagen.apev2 import APEv2File
        options = [OggTheora, OggVorbis, OggFLAC, FLAC, MP3, APEv2File]

    if not options:
        return None

    try:
        fileobj = file(filename, "rb")
        header = fileobj.read(128)
        results = [Kind.score(filename, fileobj, header) for Kind in options]
    finally:
        fileobj.close()
    results = zip(results, options)
    results.sort()
    score, Kind = results[-1]
    if score > 0: return Kind(filename)
    else: return None
