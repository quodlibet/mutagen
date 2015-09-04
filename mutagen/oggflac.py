# -*- coding: utf-8 -*-

# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write Ogg FLAC comments.

This module handles FLAC files wrapped in an Ogg bitstream. The first
FLAC stream found is used. For 'naked' FLACs, see mutagen.flac.

This module is based off the specification at
http://flac.sourceforge.net/ogg_mapping.html.
"""

__all__ = ["OggFLAC", "Open", "delete"]

import struct

from ._compat import cBytesIO

from mutagen import StreamInfo
from mutagen.flac import StreamInfo as FLACStreamInfo, error as FLACError
from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggPage, OggFileType, error as OggError


class error(OggError):
    pass


class OggFLACHeaderError(error):
    pass


def _find_header_page(fileobj):
    """Raises OggFLACHeaderError"""

    try:
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"\x7FFLAC"):
            page = OggPage(fileobj)
    except EOFError:
        raise OggFLACHeaderError("Couldn't find header")

    # required by the spec
    if not page.complete or not page.first:
        raise OggFLACHeaderError("Invalid header")

    return page


class OggFLACStreamInfo(StreamInfo):
    """Ogg FLAC stream info."""

    length = 0
    """File length in seconds, as a float"""

    channels = 0
    """Number of channels"""

    sample_rate = 0
    """Sample rate in Hz"""

    def __init__(self, fileobj):
        page = _find_header_page(fileobj)
        packets = OggPage.to_packets([page])
        assert len(packets)

        major, minor, self.packets, flac = struct.unpack(
            ">BBH4s", packets[0][5:13])

        if flac != b"fLaC":
            raise OggFLACHeaderError("invalid FLAC marker (%r)" % flac)

        if (major, minor) != (1, 0):
            raise OggFLACHeaderError(
                "unknown mapping version: %d.%d" % (major, minor))
        self.serial = page.serial

        # Skip over the block header.
        stringobj = cBytesIO(page.packets[0][17:])

        try:
            flac_info = FLACStreamInfo(stringobj)
        except FLACError as e:
            raise OggFLACHeaderError(e)

        for attr in ["min_blocksize", "max_blocksize", "sample_rate",
                     "channels", "bits_per_sample", "total_samples", "length"]:
            setattr(self, attr, getattr(flac_info, attr))

    def _post_tags(self, fileobj):
        if self.length:
            return
        page = OggPage.find_last(fileobj, self.serial)
        self.length = page.position / float(self.sample_rate)

    def pprint(self):
        return u"Ogg FLAC, %.2f seconds, %d Hz" % (
            self.length, self.sample_rate)


class OggFLACVComment(VCommentDict):

    def __get_flac_pages(self, fileobj, serial):
        pages = []
        for page in OggPage._iter_stream(fileobj, serial):
            if not page.continued:
                packet = page.packets[0]
                if not packet or not 0x01 <= (ord(packet[0:1]) & 0x7F) <= 0x7E:
                    break
            if page.position not in (0, -1):
                raise error("Invalid metadata ogg pages")
            pages.append(page)

        if not pages or not pages[-1].complete:
            raise error("Invalid metadata ogg pages")

        return pages

    def __init__(self, fileobj, info):
        # data should be pointing at the start of an Ogg page, after
        # the first FLAC page.
        pages = self.__get_flac_pages(fileobj, info.serial)
        comment = cBytesIO(OggPage.to_packets(pages)[0][4:])
        super(OggFLACVComment, self).__init__(comment, framing=False)

    def _inject(self, fileobj, padding_func):
        """Write tag data into the FLAC Vorbis comment packet/page."""

        fileobj.seek(0)

        # get the header page
        header = _find_header_page(fileobj)

        # get all flac frames
        old_pages = self.__get_flac_pages(fileobj, header.serial)

        # the last packet finishes the page -> strict
        packets = OggPage.to_packets(old_pages, strict=True)
        # rewrite the first one (guaranteed to be a vcomment by the spec)
        data = self.write(framing=False)
        data = packets[0][:1] + struct.pack(">I", len(data))[-3:] + data
        packets[0] = data

        # write new pages back
        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggFLAC(OggFileType):
    """An Ogg FLAC file."""

    _Info = OggFLACStreamInfo
    _Tags = OggFLACVComment
    _Error = OggFLACHeaderError
    _mimes = ["audio/x-oggflac"]

    info = None
    """A `OggFLACStreamInfo`"""

    tags = None
    """A `VCommentDict`"""

    def save(self, filename=None):
        return super(OggFLAC, self).save(filename)

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"OggS") * (
            (b"FLAC" in header) + (b"fLaC" in header)))


Open = OggFLAC


def delete(filename):
    """Remove tags from a file."""

    OggFLAC(filename).delete()
