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

Read more about Ogg Vorbis at http://vorbis.com/. Mutagen uses an
external module, pyvorbis, to open Ogg Vorbis files.  Read more about
pyvorbis at http://www.andrewchatham.com/pyogg/.

Benefits of using Mutagen rather than pyvorbis directly include an API
consistent with the rest of Mutagen, a full dict-like interface to the
comment data, and the ability to properly read and write a 'vendor'
comment key.
"""

try: from ogg.vorbis import VorbisFile, VorbisError
except ImportError:
    raise ImportError("%s requires pyvorbis "
                      "(http://www.andrewchatham.com/pyogg/" % __name__)

from mutagen import FileType
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
        fileobj.seek(0)
        page = OggPage(fileobj)
        while not page.data.startswith("\x01vorbis"):
            page = OggPage(fileobj)
        if not page.first:
            raise IOError("page has ID header, but doesn't start a packet")
        channels = ord(page.data[11])
        sample_rate = cdata.uint_le(page.data[12:16])
        serial = page.serial

        max_bitrate = cdata.uint_le(page.data[16:20])
        nominal_bitrate = cdata.uint_le(page.data[20:24])
        min_bitrate = cdata.uint_le(page.data[24:28])
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

        # Store the file offset of this page to avoid rescanning it
        # when looking for comments.
        self._offset = fileobj.tell()

        samples = page.position
        while not page.last:
            page = OggPage(fileobj)
            if page.serial == serial:
                samples = max(samples, page.position)
        self.length = samples / float(sample_rate)

class OggVCommentDict(VCommentDict):
    """Vorbis comments embedded in an Ogg bitstream."""

    def __init__(self, fileobj, info):
        offset = info._offset
        fileobj.seek(info._offset)
        page = OggPage(fileobj)
        # Seek to the start of the comment header.
        while not page.data.startswith("\x03vorbis"):
            page = OggPage(fileobj)
        data = [page.data]
        # Keep seeking forward until we have the entire comment header.
        # We may accidentally grab some of the setup header at the end;
        # VComment will just ignore it.
        page = OggPage(fileobj)
        while page.continued:
            data.append(page.data)
            page = OggPage(fileobj)
        data = "".join(data)[7:] # Strip off "\x03vorbis".
        super(OggVCommentDict, self).__init__(data)

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
            self.tags = OggVCommentDict(fileobj, self.info)
        except IOError, e:
            raise OggVorbisNoHeaderError(e)

    def delete(self, filename=None):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None: filename = self.filename
        try: vorbis = VorbisFile(filename)
        except VorbisError, e: raise OggVorbisNoHeaderError(e)
        comment = vorbis.comment()
        comment.clear()
        comment.write_to(filename)

    def save(self, filename=None):
        """Save a tag to a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename
        self.tags.validate()
        try: vorbis = VorbisFile(filename)
        except VorbisError, e:
            raise OggVorbisNoHeaderError(e)
        comment = vorbis.comment()
        comment.clear()
        for key, value in self.tags:
            comment[key] = value
        comment.write_to(filename)

Open = OggVorbis

def delete(filename):
    """Remove tags from a file."""
    OggVorbis(filename).delete()
