# Ogg Vorbis support, sort of.
#
# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Read and write Ogg Vorbis comments.

This code only supports Ogg Vorbis I files, though it will probably be
able to read comments from Vorbis streams in multiplexed Ogg files (in
particular, it assumes that the identification and comment headers fit
into the first two packets).

This cannot handle very long (> 60KB or so) Vorbis comments.

Read more about Ogg Vorbis at http://vorbis.com/. This module is based
off the specification at http://www.xiph.org/ogg/doc/rfc3533.txt.
"""

from mutagen import FileType, Metadata
from mutagen._vorbis import VCommentDict
from mutagen._ogg import OggPage
from mutagen._util import cdata

class error(IOError): pass
class OggVorbisNoHeaderError(error): pass

class OggVorbisInfo(object):
    """Ogg Vorbis stream information.

    Attributes:
    length - file length in seconds, as a float
    bitrate - nominal ('average') bitrate in bits per second, as an int
    """
    def __init__(self, fileobj):
        page = OggPage(fileobj)
        while not page.data[0].startswith("\x01vorbis"):
            page = OggPage(fileobj)
        if not page.first:
            raise IOError("page has ID header, but doesn't start a packet")
        self.channels = ord(page.data[0][11])
        self.sample_rate = cdata.uint_le(page.data[0][12:16])
        self.serial = page.serial

        max_bitrate = cdata.uint_le(page.data[0][16:20])
        nominal_bitrate = cdata.uint_le(page.data[0][20:24])
        min_bitrate = cdata.uint_le(page.data[0][24:28])
        if nominal_bitrate == 0:
            self.bitrate = (max_bitrate + min_bitrate) / 2
        elif max_bitrate:
            # If the max bitrate is less than the nominal, we know
            # the nominal is wrong.
            self.bitrate = min(max_bitrate, nominal_bitrate)
        elif min_bitrate:
            self.bitrate = max(min_bitrate, nominal_bitrate)
        else:
            self.bitrate = nominal_bitrate

class OggVCommentDict(VCommentDict):
    """Vorbis comments embedded in an Ogg bitstream."""

    def __init__(self, fileobj):
        page = OggPage(fileobj)
        # Seek to the start of the comment header. We know it's got
        # to be at the start of the second page.
        while not page.data[0].startswith("\x03vorbis"):
            page = OggPage(fileobj)
        data = page.data[0][7:] # Strip off "\x03vorbis".
        super(OggVCommentDict, self).__init__(data)

    def _inject(self, fileobj, offset=0):
        """Write tag data into the Vorbis comment packet/page."""
        fileobj.seek(offset)
        page = OggPage(fileobj)
        while not page.data[0].startswith("\x03vorbis"):
            offset = fileobj.tell()
            page = OggPage(fileobj)
        oldpagesize = page.size

        page.data[0] = "\x03vorbis" + self.write()
        if page.size > 255*255:
            raise NotImplementedError(
                "repagination needed for %d bytes" % page.size)
        else:
            delta = page.size - oldpagesize
            if delta > 0:
                Metadata._insert_space(fileobj, delta, offset)
            elif delta < 0:
                Metadata._delete_bytes(fileobj, -delta, offset)
            fileobj.seek(offset)
            fileobj.write(page.write())

class OggVorbis(FileType):
    """An Ogg Vorbis file."""

    def __init__(self, filename=None):
        if filename is not None:
            self.load(filename)

    def pprint(self):
        """Print stream information and comment key=value pairs."""
        s = "Ogg Vorbis, %.2f seconds, %d bps\n" % (
            self.info.length, self.info.bitrate)
        return s + "\n".join(
            ["%s=%s" % (k.lower(), v) for k, v in (self.tags or [])])

    def load(self, filename):
        """Load file information from a filename."""

        self.filename = filename
        fileobj = file(filename, "rb")
        try:
            self.info = OggVorbisInfo(fileobj)
            self.tags = OggVCommentDict(fileobj)

            page = OggPage(fileobj)
            samples = page.position
            while not page.last:
                page = OggPage(fileobj)
                if page.serial == self.info.serial:
                    samples = max(samples, page.position)
            self.info.length = samples / float(self.info.sample_rate)

        except IOError, e:
            raise OggVorbisNoHeaderError(e)

    def delete(self, filename=None):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename

        self.tags.clear()
        fileobj = file(filename, "rb+")
        try: self.tags._inject(fileobj)
        except IOError, e:
            raise OggVorbisNoHeaderError(e)
        fileobj.close()

    def save(self, filename=None):
        """Save a tag to a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename
        self.tags.validate()
        fileobj = file(filename, "rb+")
        try: self.tags._inject(fileobj)
        except IOError, e:
            raise OggVorbisNoHeaderError(e)
        fileobj.close()

Open = OggVorbis

def delete(filename):
    """Remove tags from a file."""
    OggVorbis(filename).delete()
