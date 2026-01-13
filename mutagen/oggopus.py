# Copyright (C) 2012, 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write Ogg Opus comments.

This module handles Opus files wrapped in an Ogg bitstream. The
first Opus stream found is used.

Based on http://tools.ietf.org/html/draft-terriberry-oggopus-01
"""

__all__ = ["OggOpus", "Open", "delete"]

import struct
from io import BytesIO
from typing import override

from mutagen import StreamInfo
from mutagen._filething import FileThing
from mutagen._tags import PaddingFunction, PaddingInfo
from mutagen._util import convert_error, get_size, loadfile
from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggFileType, OggPage
from mutagen.ogg import error as OggError


class error(OggError):
    pass


class OggOpusHeaderError(error):
    pass


class OggOpusInfo(StreamInfo):
    """OggOpusInfo()

    Ogg Opus stream information.

    Attributes:
        length (`float`): File length in seconds, as a float
        channels (`int`): Number of channels
    """

    length: float = 0.0
    channels: int = 0

    serial: int
    __pre_skip: int

    def __init__(self, fileobj: BytesIO):
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"OpusHead"):
            page = OggPage(fileobj)

        self.serial = page.serial

        if not page.first:
            raise OggOpusHeaderError(
                "page has ID header, but doesn't start a stream")

        (version, self.channels, pre_skip, orig_sample_rate, output_gain,
         channel_map) = struct.unpack("<BBHIhB", page.packets[0][8:19])

        self.__pre_skip = pre_skip

        # only the higher 4 bits change on incombatible changes
        major = version >> 4
        if major != 0:
            raise OggOpusHeaderError(f"version {major!r} unsupported")

    def _post_tags(self, fileobj: BytesIO):
        page = OggPage.find_last(fileobj, self.serial, finishing=True)
        if page is None:
            raise OggOpusHeaderError
        self.length = (page.position - self.__pre_skip) / float(48000)

    @override
    def pprint(self):
        return f"Ogg Opus, {self.length:.2f} seconds"


class OggOpusVComment(VCommentDict):
    """Opus comments embedded in an Ogg bitstream."""

    _padding: int
    _pad_data: bytes

    def __get_comment_pages(self, fileobj: BytesIO, info: OggOpusInfo):
        # find the first tags page with the right serial
        page = OggPage(fileobj)
        while ((info.serial != page.serial) or
                not page.packets[0].startswith(b"OpusTags")):
            page = OggPage(fileobj)

        # get all comment pages
        pages = [page]
        while not (pages[-1].complete or len(pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == pages[0].serial:
                pages.append(page)

        return pages

    def __init__(self, fileobj: BytesIO, info: OggOpusInfo):
        pages = self.__get_comment_pages(fileobj, info)
        data = OggPage.to_packets(pages)[0][8:]  # Strip OpusTags
        fileobj = BytesIO(data)
        super().__init__(fileobj, framing=False)
        self._padding = len(data) - self._size

        # in case the LSB of the first byte after v-comment is 1, preserve the
        # following data
        padding_flag = fileobj.read(1)
        if padding_flag and ord(padding_flag) & 0x1:
            self._pad_data = padding_flag + fileobj.read()
            self._padding = 0  # we have to preserve, so no padding
        else:
            self._pad_data = b""

    def _inject(self, fileobj: BytesIO, padding_func: PaddingFunction | None):
        _ = fileobj.seek(0)
        info = OggOpusInfo(fileobj)
        old_pages = self.__get_comment_pages(fileobj, info)

        packets = OggPage.to_packets(old_pages)
        vcomment_data = b"OpusTags" + self.write(framing=False)

        if self._pad_data:
            # if we have padding data to preserver we can't add more padding
            # as long as we don't know the structure of what follows
            packets[0] = vcomment_data + self._pad_data
        else:
            content_size = get_size(fileobj) - len(packets[0])  # approx
            padding_left = len(packets[0]) - len(vcomment_data)
            info = PaddingInfo(padding_left, content_size)
            new_padding = info._get_padding(padding_func)
            packets[0] = vcomment_data + b"\x00" * new_padding

        new_pages = OggPage._from_packets_try_preserve(packets, old_pages)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggOpus(OggFileType):
    """OggOpus(filething)

    An Ogg Opus file.

    Arguments:
        filething (filething)

    Attributes:
        info (`OggOpusInfo`)
        tags (`mutagen._vorbis.VCommentDict`)

    """

    _Info: type[StreamInfo] = OggOpusInfo
    _Tags = OggOpusVComment
    _Error = OggOpusHeaderError
    _mimes: list[str] = ["audio/ogg", "audio/ogg; codecs=opus"]

    info: OggOpusInfo | None = None
    tags : OggOpusVComment | None = None

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        return (header.startswith(b"OggS") * (b"OpusHead" in header))


Open = OggOpus


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing) -> None:
    """ delete(filething)

    Arguments:
        filething (filething)
    Raises:
        mutagen.MutagenError

    Remove tags from a file.
    """

    t = OggOpus(filething)
    _ = filething.fileobj.seek(0)
    t.delete(filething)
