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

This module can handle Vorbis streams in any Ogg file (though it only
finds and manipulates the first one; if you need better logical stream
control, use OggPage directly). This means it can read, tag, and get
information about e.g. OGM files with a Vorbis stream.

Read more about Ogg Vorbis at http://vorbis.com/. This module is based
off the specification at http://www.xiph.org/ogg/doc/rfc3533.txt.
"""

from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggPage, OggFileType
from mutagen._util import cdata

class error(IOError): pass
class OggVorbisHeaderError(error): pass

class OggVorbisInfo(object):
    """Ogg Vorbis stream information.

    Attributes:
    length - file length in seconds, as a float
    bitrate - nominal ('average') bitrate in bits per second, as an int
    """

    length = 0

    def __init__(self, fileobj):
        page = OggPage(fileobj)
        while not page.packets[0].startswith("\x01vorbis"):
            page = OggPage(fileobj)
        if not page.first:
            raise IOError("page has ID header, but doesn't start a packet")
        self.channels = ord(page.packets[0][11])
        self.sample_rate = cdata.uint_le(page.packets[0][12:16])
        self.serial = page.serial

        max_bitrate = cdata.uint_le(page.packets[0][16:20])
        nominal_bitrate = cdata.uint_le(page.packets[0][20:24])
        min_bitrate = cdata.uint_le(page.packets[0][24:28])
        if nominal_bitrate == 0:
            self.bitrate = (max_bitrate + min_bitrate) // 2
        elif max_bitrate:
            # If the max bitrate is less than the nominal, we know
            # the nominal is wrong.
            self.bitrate = min(max_bitrate, nominal_bitrate)
        elif min_bitrate:
            self.bitrate = max(min_bitrate, nominal_bitrate)
        else:
            self.bitrate = nominal_bitrate

    def pprint(self):
        return "Ogg Vorbis, %.2f seconds, %d bps" % (self.length, self.bitrate)

class OggVCommentDict(VCommentDict):
    """Vorbis comments embedded in an Ogg bitstream."""

    def __init__(self, fileobj, info):
        pages = []
        complete = False
        while not complete:
            page = OggPage(fileobj)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        data = OggPage.to_packets(pages)[0][7:] # Strip off "\x03vorbis".
        super(OggVCommentDict, self).__init__(data)

    def _inject(self, fileobj):
        """Write tag data into the Vorbis comment packet/page."""

        # Find the old pages in the file; we'll need to remove them,
        # plus grab any stray setup packet data out of them.
        fileobj.seek(0)
        page = OggPage(fileobj)
        while not page.packets[0].startswith("\x03vorbis"):
            page = OggPage(fileobj)

        old_pages = [page]
        while not page.packets[-1].startswith("\x05vorbis"):
            page = OggPage(fileobj)
            if page.serial == old_pages[0].serial:
                old_pages.append(page)

        # We will have the comment data, and the setup packet for sure.
        # Ogg Vorbis I says there won't be another one until at least
        # one more page.
        packets = OggPage.to_packets(old_pages)
        assert(len(packets) == 2)

        # Set the new comment packet.
        packets[0] = "\x03vorbis" + self.write()

        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        OggPage.replace(fileobj, old_pages, new_pages)

class OggVorbis(OggFileType):
    """An Ogg Vorbis file."""

    _Info = OggVorbisInfo
    _Tags = OggVCommentDict
    _Error = OggVorbisHeaderError

    def score(filename, fileobj, header):
        return (header.startswith("OggS") + ("\x01vorbis" in header))
    score = staticmethod(score)

Open = OggVorbis

def delete(filename):
    """Remove tags from a file."""
    OggVorbis(filename).delete()
