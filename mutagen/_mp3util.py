# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""
http://www.codeproject.com/Articles/8295/MPEG-Audio-Frame-Header
http://wiki.hydrogenaud.io/index.php?title=MP3
"""

from functools import partial

from ._util import cdata
from ._compat import xrange


class XingHeaderError(Exception):
    pass


class XingHeaderFlags(object):
    FRAMES = 0x1
    BYTES = 0x2
    TOC = 0x4
    VBR_SCALE = 0x8


class XingHeader(object):

    frames = -1
    """Number of frames, -1 if unknown"""

    bytes = -1
    """Number of bytes, -1 if unknown"""

    toc = []
    """List of 100 file offsets in percent encoded as 0-255. E.g. entry
    50 contains the file offset in percent at 50% play time.
    Empty if unknown.
    """

    vbr_scale = -1
    """VBR quality indicator 0-100. -1 if unknown"""

    def __init__(self, fileobj):
        """Parses the Xing header or raises XingHeaderError.

        The file position after this returns is undefined.
        """

        data = fileobj.read(8)
        if len(data) != 8 or data[:4] not in (b"Xing", b"Info"):
            raise XingHeaderError("Not a Xing header")

        flags = cdata.uint32_be_from(data, 4)[0]

        if flags & XingHeaderFlags.FRAMES:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.frames = cdata.uint32_be(data)

        if flags & XingHeaderFlags.BYTES:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.bytes = cdata.uint32_be(data)

        if flags & XingHeaderFlags.TOC:
            data = fileobj.read(100)
            if len(data) != 100:
                raise XingHeaderError("Xing header truncated")
            self.toc = list(bytearray(data))

        if flags & XingHeaderFlags.VBR_SCALE:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.vbr_scale = cdata.uint32_be(data)

    @classmethod
    def get_offset(cls, info):
        """Calculate the offset to the Xing header from the start of the
        MPEG header including sync based on the MPEG header's content.
        """

        assert info.layer == 3

        if info.version == 1:
            if info.mode != 3:
                return 36
            else:
                return 21
        else:
            if info.mode != 3:
                return 21
            else:
                return 13


class VBRIHeaderError(Exception):
    pass


class VBRIHeader(object):

    version = 0
    """VBRI header version"""

    quality = 0
    """Quality indicator"""

    bytes = 0
    """Number of bytes"""

    frames = 0
    """Number of frames"""

    toc_scale_factor = 0
    """Scale factor of TOC entries"""

    toc_frames = 0
    """Number of frames per table entry"""

    toc = []
    """TOC"""

    def __init__(self, fileobj):
        """Reads the VBRI header or raises VBRIHeaderError.

        The file position is undefined after this returns
        """

        data = fileobj.read(26)
        if len(data) != 26 or not data.startswith(b"VBRI"):
            raise VBRIHeaderError("Not a VBRI header")

        offset = 4
        self.version, offset = cdata.uint16_be_from(data, offset)
        if self.version != 1:
            raise VBRIHeaderError(
                "Unsupported header version: %r" % self.version)

        offset += 2  # float16.. can't do
        self.quality, offset = cdata.uint16_be_from(data, offset)
        self.bytes, offset = cdata.uint32_be_from(data, offset)
        self.frames, offset = cdata.uint32_be_from(data, offset)

        toc_num_entries, offset = cdata.uint16_be_from(data, offset)
        self.toc_scale_factor, offset = cdata.uint16_be_from(data, offset)
        toc_entry_size, offset = cdata.uint16_be_from(data, offset)
        self.toc_frames, offset = cdata.uint16_be_from(data, offset)
        toc_size = toc_entry_size * toc_num_entries
        toc_data = fileobj.read(toc_size)
        if len(toc_data) != toc_size:
            raise VBRIHeaderError("VBRI header truncated")

        self.toc = []
        if toc_entry_size == 2:
            unpack = partial(cdata.uint16_be_from, toc_data)
        elif toc_entry_size == 4:
            unpack = partial(cdata.uint32_be_from, toc_data)
        else:
            raise VBRIHeaderError("Invalid TOC entry size")

        self.toc = [unpack(i)[0] for i in xrange(0, toc_size, toc_entry_size)]

    @classmethod
    def get_offset(cls, info):
        """Offset in bytes from the start of the MPEG header including sync"""

        assert info.layer == 3

        return 36
