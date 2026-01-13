# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write Ogg Vorbis comments.

This module handles Vorbis files wrapped in an Ogg bitstream. The
first Vorbis stream found is used.

Read more about Ogg Vorbis at http://vorbis.com/. This module is based
on the specification at http://www.xiph.org/vorbis/doc/Vorbis_I_spec.html.
"""

__all__ = ["OggVorbis", "Open", "delete"]

import struct
from io import BytesIO
from typing import cast, final, override

from mutagen import StreamInfo
from mutagen._filething import FileThing
from mutagen._tags import PaddingFunction, PaddingInfo
from mutagen._util import convert_error, get_size, loadfile
from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggFileType, OggPage
from mutagen.ogg import error as OggError


class error(OggError):
    pass


class OggVorbisHeaderError(error):
    pass

@final
class OggVorbisInfo(StreamInfo):
    """OggVorbisInfo()

    Ogg Vorbis stream information.

    Attributes:
        length (`float`): File length in seconds, as a float
        channels (`int`): Number of channels
        bitrate (`int`): Nominal ('average') bitrate in bits per second
        sample_rate (`int`): Sample rate in Hz

    """

    length: float = 0.0
    channels: int = 0
    bitrate: int = 0
    sample_rate: int = 0

    def __init__(self, fileobj: BytesIO):
        """Raises ogg.error, IOError"""

        page = OggPage(fileobj)
        if not page.packets:
            raise OggVorbisHeaderError("page has not packets")
        while not page.packets[0].startswith(b"\x01vorbis"):
            page = OggPage(fileobj)
        if not page.first:
            raise OggVorbisHeaderError(
                "page has ID header, but doesn't start a stream")
        if len(page.packets[0]) < 28:
            raise OggVorbisHeaderError(
                "page contains a packet too short to be valid")
        (self.channels, self.sample_rate, max_bitrate, nominal_bitrate,
         min_bitrate) = cast(tuple[int, int, int, int, int],struct.unpack("<BI3i", page.packets[0][11:28]))
        if self.sample_rate == 0:
            raise OggVorbisHeaderError("sample rate can't be zero")
        self.serial = page.serial

        max_bitrate = max(0, max_bitrate)
        min_bitrate = max(0, min_bitrate)
        nominal_bitrate = max(0, nominal_bitrate)

        if nominal_bitrate == 0:
            self.bitrate = (max_bitrate + min_bitrate) // 2
        elif max_bitrate and max_bitrate < nominal_bitrate:
            # If the max bitrate is less than the nominal, we know
            # the nominal is wrong.
            self.bitrate = max_bitrate
        elif min_bitrate > nominal_bitrate:
            self.bitrate = min_bitrate
        else:
            self.bitrate = nominal_bitrate

    def _post_tags(self, fileobj: BytesIO):
        """Raises ogg.error"""

        page = OggPage.find_last(fileobj, self.serial, finishing=True)
        if page is None:
            raise OggVorbisHeaderError
        self.length = page.position / float(self.sample_rate)

    @override
    def pprint(self):
        return "Ogg Vorbis, %.2f seconds, %d bps" % (
            self.length, self.bitrate)


class OggVCommentDict(VCommentDict):
    """Vorbis comments embedded in an Ogg bitstream."""

    _padding: int

    def __init__(self, fileobj: BytesIO, info: OggVorbisInfo):
        pages: list[OggPage] = []
        complete = False
        while not complete:
            page = OggPage(fileobj)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        data = OggPage.to_packets(pages)[0][7:]  # Strip off "\x03vorbis".
        super().__init__(data)
        self._padding = len(data) - self._size

    def _inject(self, fileobj: BytesIO, padding_func: PaddingFunction | None):
        """Write tag data into the Vorbis comment packet/page."""

        # Find the old pages in the file; we'll need to remove them,
        # plus grab any stray setup packet data out of them.
        _ = fileobj.seek(0)
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"\x03vorbis"):
            page = OggPage(fileobj)

        old_pages = [page]
        while not (old_pages[-1].complete or len(old_pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == old_pages[0].serial:
                old_pages.append(page)

        packets = OggPage.to_packets(old_pages, strict=False)

        content_size = get_size(fileobj) - len(packets[0])  # approx
        vcomment_data = b"\x03vorbis" + self.write()
        padding_left = len(packets[0]) - len(vcomment_data)

        info = PaddingInfo(padding_left, content_size)
        new_padding = info._get_padding(padding_func)

        # Set the new comment packet.
        packets[0] = vcomment_data + b"\x00" * new_padding

        new_pages = OggPage._from_packets_try_preserve(packets, old_pages)
        OggPage.replace(fileobj, old_pages, new_pages)

@final
class OggVorbis(OggFileType):
    """OggVorbis(filething)

    Arguments:
        filething (filething)

    An Ogg Vorbis file.

    Attributes:
        info (`OggVorbisInfo`)
        tags (`mutagen._vorbis.VCommentDict`)
    """

    _Info: type[StreamInfo] = OggVorbisInfo
    _Tags = OggVCommentDict
    _Error = OggVorbisHeaderError
    _mimes: list[str] = ["audio/vorbis", "audio/x-vorbis"]

    info = None
    tags = None

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        return (header.startswith(b"OggS") * (b"\x01vorbis" in header))


Open = OggVorbis


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething: FileThing):
    """ delete(filething)

    Arguments:
        filething (filething)
    Raises:
        mutagen.MutagenError

    Remove tags from a file.
    """

    t = OggVorbis(filething)
    _ = filething.fileobj.seek(0)
    t.delete(filething)
