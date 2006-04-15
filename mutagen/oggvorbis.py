# Ogg Vorbis support, sort of.
#
# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Read and write Ogg Vorbis files (http://vorbis.com/).

Mutagen uses an external module, pyvorbis, to open Ogg Vorbis files.
Read more about pyvorbis at http://www.andrewchatham.com/pyogg/.
"""

try: from ogg.vorbis import VorbisFile, VorbisError
except ImportError:
    raise ImportError("%s requires pyvorbis "
                      "(http://www.andrewchatham.com/pyogg/" % __name__)

from mutagen import FileType
from mutagen._vorbis import VCommentDict

class error(IOError): pass
class OggVorbisNoHeaderError(error): pass

__all__ = ["Open", "OggVorbis"]

class OggVorbisInfo(object):
    """The 'info' attribute of OggVorbis objects. It has two attributes:
    length - file length in seconds, as a float
    bitrate - nominal ("average") bitrate in bits per second, as an int
    """

    __slots__ = ["length", "bitrate"]

class OggVorbis(FileType):
    def __init__(self, filename=None):
        if filename is not None: self.load(filename)

    def pprint(self):
        s = "Ogg Vorbis, %.2f seconds, %d bps\n" % (
            self.info.length, self.info.bitrate)
        return s + "\n".join(
            ["%s=%s" % (k.lower(), v) for k, v in (self.tags or [])])

    def load(self, filename):
        """Load file information from a filename."""
        self.filename = filename
        try: vorbis = VorbisFile(filename)
        except VorbisError, e: raise OggVorbisNoHeaderError(e)

        self.info = OggVorbisInfo()
        self.info.length = vorbis.time_total(-1)
        self.info.bitrate = vorbis.bitrate(-1)

        self.tags = VCommentDict()
        for k, v in vorbis.comment().as_dict().iteritems():
            if not isinstance(v, list):
                v = [v]
            v = map(unicode, v)
            if k.lower() == "vendor":
                # The first item in the vendor list is the actual vendor
                # data, which is not a tag, and also not editable.
                self.tags.vendor = v.pop(0)
            if v: self.tags[k] = v

    def delete(self, filename=None):
        """Remove tags from a file.

        If no filename is given, the one passed to the constructor is used.
        """

        if filename is None: filename = self.filename
        try: vorbis = VorbisFile(filename)
        except VorbisError, e: raise OggVorbisNoHeaderError(e)
        comment = vorbis.comment()
        comment.clear()
        comment.write_to(filename)

    def save(self, filename=None):
        """Save a tag to a file.

        If no filename is given, the one passed to the constructor is used.
        """

        if filename is None: filename = self.filename
        self.tags.validate()
        try: vorbis = VorbisFile(filename)
        except VorbisError, e: raise OggVorbisNoHeaderError(e)
        comment = vorbis.comment()
        comment.clear()
        for key, value in self.tags:
            comment[key] = value
        comment.write_to(filename)

Open = OggVorbis

def delete(filename):
    """Remove tags from a file."""
    OggVorbis(filename).delete()
