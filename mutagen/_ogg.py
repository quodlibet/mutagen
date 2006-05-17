# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Read and write Ogg bitstreams and pages.

This module reads and writes a subset of the Ogg bitstream format
version 0 (notably, the subset required to tag Ogg Vorbis I files).

This implementation is based on the RFC 3533 standard found at
http://www.xiph.org/ogg/doc/rfc3533.txt.
"""

import struct
import zlib

from mutagen._util import cdata

class OggPage(object):
    """A single Ogg page (not necessarily a single encoded packet).

    A page is a header of 26 bytes, followed by the length of the
    data, followed by the data.

    The constructor is givin a file-like object pointing to the start
    of an Ogg page. After the constructor is finished it is pointing
    to the start of the next page.

    Attributes:
    version -- Stream structure version (currently always 0).
    position -- Absolute stream position (codec-depdendent semantics).
    serial -- Logical stream serial number.
    sequence -- Page sequence number within logical stream.
    data -- Raw page data.
    """

    version = 0
    type_flags = 0
    position = -1L
    serial = 0
    sequence = 0
    data = []

    def __init__(self, fileobj=None):
        if fileobj is None:
            return

        (oggs, self.version, self.type_flags, self.position,
         self.serial, self.sequence, crc, segments) = struct.unpack(
            "<4sBBqIIiB", fileobj.read(27))

        if oggs != "OggS":
            raise IOError("read %r, expected %r" % (oggs, "OggS"))

        if self.version != 0:
            raise IOError("version %r unsupported" % self.version)

        total = 0
        lacings = []
        self.finished = []
        for c in map(ord, fileobj.read(segments)):
            total += c
            if c < 255:
                lacings.append(total)
                total = 0
                self.finished.append(True)
        if total:
            lacings.append(total)
            self.finished.append(False)
        self.data = map(fileobj.read, lacings)
        if map(len, self.data) != lacings:
            raise IOError("unable to read full data")

    def __eq__(self, other):
        try:
            return (self.version == other.version and
                    self.type_flags == other.type_flags and
                    self.position == other.position and
                    self.serial == other.serial and
                    self.sequence == other.sequence and
                    self.data == other.data)
        except AttributeError:
            return False

    def __repr__(self):
        attrs = ['version', 'type_flags', 'position', 'serial',
                 'sequence']
        values = ["%s=%r" % (attr, getattr(self, attr)) for attr in attrs]
        return "<%s %s, %d bytes>" % (
            type(self).__name__, " ".join(values), sum(map(len, self.data)))

    def write(self):
        """Return a string encoding of the page header and data."""

        data = [
            struct.pack("<4sBBqIIi", "OggS", self.version, self.type_flags,
                        self.position, self.serial, self.sequence, 0)
            ]

        lacing_data = []
        for datum in self.data:
            quot, rem = divmod(len(datum), 255)
            lacing_data.append("\xff" * quot + chr(rem))
        lacing_data = "".join(lacing_data)
        if self.finished[-1] is False:
            lacing_data = lacing_data.rstrip("\x00")
        data.append(chr(len(lacing_data)))
        data.append(lacing_data)
        data.extend(self.data)
        data = "".join(data)

        # Python's CRC is swapped relative to Ogg's needs.
        crc = ~zlib.crc32(data.translate(cdata.bitswap), -1)
        # Although we're using to_int_be, this actually makes the CRC
        # a proper le integer, since Python's CRC is byteswapped.
        crc = cdata.to_int_be(crc).translate(cdata.bitswap)
        data = data[:22] + crc + data[26:]
        return data

    size = property(lambda self: len(self.write()), doc="Total frame size.")

    continued = property(lambda self: cdata.test_bit(self.type_flags, 0),
                         doc="First packet continued from the previous page.")
    first = property(lambda self: cdata.test_bit(self.type_flags, 1),
                     doc="First page of a logical bitstream.")
    last = property(lambda self: cdata.test_bit(self.type_flags, 2),
                    doc="Last page of a logical bitstream.")
