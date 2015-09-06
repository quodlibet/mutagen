# -*- coding: utf-8 -*-

# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write Ogg Speex comments.

This module handles Speex files wrapped in an Ogg bitstream. The
first Speex stream found is used.

Read more about Ogg Speex at http://www.speex.org/. This module is
based on the specification at http://www.speex.org/manual2/node7.html
and clarifications after personal communication with Jean-Marc,
http://lists.xiph.org/pipermail/speex-dev/2006-July/004676.html.
"""

__all__ = ["OggSpeex", "Open", "delete"]

from mutagen import StreamInfo
from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggPage, OggFileType, error as OggError
from mutagen._util import cdata, get_size
from mutagen._tags import PaddingInfo


class error(OggError):
    pass


class OggSpeexHeaderError(error):
    pass


class OggSpeexInfo(StreamInfo):
    """Ogg Speex stream information."""

    length = 0
    """file length in seconds, as a float"""

    channels = 0
    """number of channels"""

    bitrate = 0
    """nominal bitrate in bits per second.

    The reference encoder does not set the bitrate; in this case,
    the bitrate will be 0.
    """

    def __init__(self, fileobj):
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"Speex   "):
            page = OggPage(fileobj)
        if not page.first:
            raise OggSpeexHeaderError(
                "page has ID header, but doesn't start a stream")
        self.sample_rate = cdata.uint_le(page.packets[0][36:40])
        self.channels = cdata.uint_le(page.packets[0][48:52])
        self.bitrate = max(0, cdata.int_le(page.packets[0][52:56]))
        self.serial = page.serial

    def _post_tags(self, fileobj):
        page = OggPage.find_last(fileobj, self.serial)
        self.length = page.position / float(self.sample_rate)

    def pprint(self):
        return u"Ogg Speex, %.2f seconds" % self.length


class OggSpeexVComment(VCommentDict):
    """Speex comments embedded in an Ogg bitstream."""

    def __init__(self, fileobj, info):
        pages = []
        complete = False
        while not complete:
            page = OggPage(fileobj)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        data = OggPage.to_packets(pages)[0]
        super(OggSpeexVComment, self).__init__(data, framing=False)
        self._padding = len(data) - self._size

    def _inject(self, fileobj, padding_func):
        """Write tag data into the Speex comment packet/page."""

        fileobj.seek(0)

        # Find the first header page, with the stream info.
        # Use it to get the serial number.
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"Speex   "):
            page = OggPage(fileobj)

        # Look for the next page with that serial number, it'll start
        # the comment packet.
        serial = page.serial
        page = OggPage(fileobj)
        while page.serial != serial:
            page = OggPage(fileobj)

        # Then find all the pages with the comment packet.
        old_pages = [page]
        while not (old_pages[-1].complete or len(old_pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == old_pages[0].serial:
                old_pages.append(page)

        packets = OggPage.to_packets(old_pages, strict=False)

        content_size = get_size(fileobj) - len(packets[0])  # approx
        vcomment_data = self.write(framing=False)
        padding_left = len(packets[0]) - len(vcomment_data)

        info = PaddingInfo(padding_left, content_size)
        new_padding = info._get_padding(padding_func)

        # Set the new comment packet.
        packets[0] = vcomment_data + b"\x00" * new_padding

        new_pages = OggPage._from_packets_try_preserve(packets, old_pages)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggSpeex(OggFileType):
    """An Ogg Speex file."""

    _Info = OggSpeexInfo
    _Tags = OggSpeexVComment
    _Error = OggSpeexHeaderError
    _mimes = ["audio/x-speex"]

    info = None
    """A `OggSpeexInfo`"""

    tags = None
    """A `VCommentDict`"""

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"OggS") * (b"Speex   " in header))


Open = OggSpeex


def delete(filename):
    """Remove tags from a file."""

    OggSpeex(filename).delete()
