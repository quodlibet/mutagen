# Simpler (but far more limited) API for ID3 editing
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id: id3.py 3086 2006-04-04 02:13:21Z piman $

"""Easier access to ID3 tags.

EasyID3 is a wrapper around mutagen.id3.ID3 to make ID3 tags appear
more like Vorbis or APEv2 tags.
"""

import mutagen.id3
from mutagen import Metadata
from mutagen._util import DictMixin
from mutagen.id3 import ID3, error

__all__ = ['EasyID3', 'Open', 'delete']

class EasyID3(DictMixin, Metadata):
    """A file with an ID3 tag.

    Like Vorbis comments, EasyID3 keys are case-insensitive ASCII
    values. Only a subset of ID3 frames (those with simple text keys)
    are supported; EasyID3.valid_keys maps human-readable EasyID3
    names to ID3 frame IDs.

    To use an EasyID3 class with mutagen.mp3.MP3:
        from mutagen.mp3 import MP3
        from mutagen.easyid3 import EasyID3
        MP3(filename, ID3=EasyID3)
    """

    valid_keys = {
        "album": "TALB",
        "composer": "TCOM",
        "genre": "TCON",
        "date": "TDRC",
        "lyricist": "TEXT",
        "title": "TIT2",
        "version": "TIT3",
        "artist": "TPE1",
        "tracknumber": "TRCK",
        }
    """Valid keys for EasyID3 instances."""

    def __init__(self, filename=None):
        self.__id3 = ID3()
        self.load = self.__id3.load
        self.save = self.__id3.save
        self.delete = self.__id3.delete
        if filename is not None:
            self.load(filename)

    filename = property(lambda s: s.__id3.filename,
                        lambda s, fn: setattr(s.__id3, 'filename', fn))

    _size = property(lambda s: s._id3.size,
                     lambda s, fn: setattr(s.__id3, '_size', fn))

    def __TCON_get(self, frame):
        return frame.genres

    def __TCON_set(self, frame, value):
        frame.encoding = 3
        if not isinstance(value, list):
            value = [value]
        frame.genres = value

    def __TDRC_get(self, frame):
        return [stamp.text for stamp in frame.text]

    def __TDRC_set(self, frame, value):
        self.__id3.add(mutagen.id3.TDRC(encoding=3, text=value))

    def __text_get(self, frame):
        return list(frame)

    def __text_set(self, frame, value):
        frame.encoding = 3
        if not isinstance(value, list):
            value = [value]
        frame.text = value

    def __getitem__(self, key):
        key = key.lower()
        if key in self.valid_keys:
            frame = self.valid_keys[key]
            getter = self.__mungers.get(frame, self.__default)[0]
            return getter(self, self.__id3[frame])
        else: raise ValueError("%r is not a valid key" % key)

    def __setitem__(self, key, value):
        key = key.lower()
        if key in self.valid_keys:
            frame = self.valid_keys[key]
            setter = self.__mungers.get(frame, self.__default)[1]
            if frame not in self.__id3:
                frame = mutagen.id3.Frames[frame](encoding=3, text=value)
                self.__id3.loaded_frame(frame)
            else:
                setter(self, self.__id3[frame], value)
        else: raise ValueError("%r is not a valid key" % key)

    def __delitem__(self, key):
        key = key.lower()
        if key in self.valid_keys:
            del(self.__id3[self.valid_keys[key]])
        else: raise ValueError("%r is not a valid key" % key)

    def keys(self):
        return [k for (k, v) in self.valid_keys.items() if v in self.__id3]

    def pprint(self):
        """Print tag key=value pairs."""
        strings = []
        for key in self.keys():
            values = self[key]
            for value in values:
                strings.append("%s=%s" % (key, value))
        return "\n".join(strings)

    __mungers = {
        "TCON": (__TCON_get, __TCON_set),
        "TDRC": (__TDRC_get, __TDRC_set),
        }

    __default = (__text_get, __text_set)

def delete(filename):
    """Remove tags from a file."""
    mutagen.id3.delete(filename)

Open = EasyID3
