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

import binascii

from mutagen._util import BitSet, cdata

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

        oggs = fileobj.read(4)
        if oggs != "OggS":
            raise IOError("read %r, expected %r" % (oggs, "OggS"))

        self.version = ord(fileobj.read(1))
        if self.version != 0:
            raise IOError("version %r unsupported" % self.version)

        self.type_flags = ord(fileobj.read(1))
        self.position = cdata.longlong_le(fileobj.read(8))
        self.serial = cdata.uint_le(fileobj.read(4))
        self.sequence = cdata.uint_le(fileobj.read(4))

        crc = cdata.uint_le(fileobj.read(4))

        segments = ord(fileobj.read(1))
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
            type(self).__name__, " ".join(values), len(self.data))

    def write(self):
        """Return a string encoding of the page header and data."""

        data = [
            "OggS",
            chr(self.version),
            chr(self.type_flags),
            cdata.to_longlong_le(self.position),
            cdata.to_uint_le(self.serial),
            cdata.to_uint_le(self.sequence),
            "\x00\x00\x00\x00", # Uninitialized CRC
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

        crc = cdata.to_int_le(binascii.crc32(data))
        data = data[:22] + crc + data[26:]
        return data

    size = property(lambda self: len(self.write()), doc="Total frame size.")

    continued = property(lambda self: BitSet(self.type_flags).test(0),
                         doc="First packet continued from the previous page.")
    first = property(lambda self: BitSet(self.type_flags).test(1),
                     doc="First page of a logical bitstream.")
    last = property(lambda self: BitSet(self.type_flags).test(2),
                    doc="Last page of a logical bitstream.")

