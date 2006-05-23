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

class LeftoverData(IOError):
    def __init__(self, value):
        self.data = value
        IOError.__init__(self, "leftover data: %r" % value)

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
    finished = True

    def __init__(self, fileobj=None):
        self.data = []

        if fileobj is None:
            return

        header = fileobj.read(27)
        if len(header) == 0:
            raise EOFError
        (oggs, self.version, self.type_flags, self.position,
         self.serial, self.sequence, crc, segments) = struct.unpack(
            "<4sBBqIIiB", header)

        if oggs != "OggS":
            raise IOError("read %r, expected %r" % (oggs, "OggS"))

        if self.version != 0:
            raise IOError("version %r unsupported" % self.version)

        total = 0
        lacings = []

        for c in map(ord, fileobj.read(segments)):
            total += c
            if c < 255:
                lacings.append(total)
                total = 0
        if total:
            lacings.append(total)
            self.finished = False

        self.data = map(fileobj.read, lacings)
        if map(len, self.data) != lacings:
            raise IOError("unable to read full data")

    def __eq__(self, other):
        try:
            return (self.version == other.version and
                    self.type_flags == other.type_flags and
                    self.finished == other.finished and
                    self.position == other.position and
                    self.serial == other.serial and
                    self.sequence == other.sequence and
                    self.data == other.data)
        except AttributeError:
            return False

    def __repr__(self):
        attrs = ['version', 'type_flags', 'position', 'serial',
                 'sequence', 'finished']
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
        if not self.finished:
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

    def __size(self):
        size = 27 # Initial header size
        for datum in self.data:
            quot, rem = divmod(len(datum), 255)
            size += quot + 1
        if not self.finished:
            # Last packet doesn't have a final lacing marker.
            size -= bool(rem)
        size += sum(map(len, self.data))
        return size

    size = property(__size, doc="Total frame size.")

    def __set_continued(self, val):
        if val: self.type_flags |= 1
        else: self.type_flags &= ~1

    def __set_first(self, val):
        if val: self.type_flags |= 2
        else: self.type_flags &= ~2

    def __set_last(self, val):
        if val: self.type_flags |= 4
        else: self.type_flags &= ~4

    continued = property(lambda self: cdata.test_bit(self.type_flags, 0),
                         __set_continued,
                         doc="First packet continued from the previous page.")
    first = property(lambda self: cdata.test_bit(self.type_flags, 1),
                     __set_first,
                     doc="First page of a logical bitstream.")
    last = property(lambda self: cdata.test_bit(self.type_flags, 2),
                    __set_last,
                    doc="Last page of a logical bitstream.")

    def renumber(klass, fileobj, serial, start):
        """Renumber pages in an Ogg file, starting at page number 'start',
        in the logical bitstream identified by 'serial'.

        fileobj must point to the start of the first Ogg page to renumber.
        No adjustment will be made to the data in the pages nor the
        granule position; only the page number, and so also the CRC.

        If an error occurs (e.g. non-Ogg data is found), fileobj will
        be left pointing to the place in the stream the error occured,
        but the invalid data will be left intact.

        This is a slow function since it must rewrite most of the file.
        Avoid renumbering pages when possible.
        """

        number = start
        while True:
            try: page = OggPage(fileobj)
            except EOFError:
                break
            else:
                if page.serial != serial:
                    # Wrong stream, skip this page.
                    continue
                # Changing the number can't change the page size,
                # so seeking back based on the current size is safe.
                fileobj.seek(-page.size, 1)
            page.sequence = number
            fileobj.write(page.write())
            number += 1
    renumber = classmethod(renumber)

    def from_pages(klass, pages, strict=False):
        """Construct a list of packet data from a list of Ogg pages.

        If strict is true, the last packet must end on the last page.
        """

        serial = pages[0].serial
        sequence = pages[0].sequence

        if strict and not pages[-1].finished:
            raise ValueError("last packet does not complete")

        packets = [[]]
        for page in pages:
            if serial != page.serial:
                raise ValueError("invalid serial number in %r" % page)
            elif sequence != page.sequence:
                raise ValueError("bad sequence number in %r" % page)
            else: sequence += 1
            for packet in page.data:
                packets[-1].append(packet)
                if page.finished:
                    packets.append([])
        if packets[-1] == []: packets.pop(-1)
        return map("".join, packets)
    from_pages = classmethod(from_pages)

    def from_packets(klass, packets, number=0):
        """Construct a list of Ogg pages from a list of packets.

        The exact packet/page segmentation chosen by this function is
        undefined, except it will be within Ogg specifications.
        (However, currently, it should not be used for many packets of
        very small data.)

        Pages are numbered started at number; other information is
        uninitialized.
        """

        pages = []
        packets = list(packets)

        while packets:
            packet = packets.pop(0)
            if len(packet) < 255*255:
                page = OggPage()
                page.data = [packet]
                page.finished = True
                pages.append(page)
            else:
                while packet:
                    page = OggPage()
                    data = packet[:8192]
                    packet = packet[8192:]
                    page.data = [data]
                    page.continued = pages and not pages[-1].finished
                    page.finished = bool(not packet)
                    pages.append(page)

        for page in pages:
            page.sequence = number
            number += 1

        return pages
    from_packets = classmethod(from_packets)
