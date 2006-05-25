# Ogg FLAC support.
#
# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Read and write Ogg FLAC comments.

This module handles FLAC files wrapped in an Ogg bitstream. For
'naked' FLACs, see mutagen.flac.

This module is bsaed off the specification at
http://flac.sourceforge.net/ogg_mapping.html.
"""

import struct

from cStringIO import StringIO

from mutagen import FileType, Metadata
from mutagen.flac import StreamInfo, VCFLACDict
from mutagen.ogg import OggPage

class error(Exception): pass
class OggFLACNoHeaderError(error, IOError): pass

class OggFLACStreamInfo(StreamInfo):
    """Ogg FLAC general header and stream info.

    This encompasses the Ogg wrapper for the FLAC STREAMINFO metadata
    block, as well as the Ogg codec setup that precedes it.
    """

    packets = 0
    serial = 0

    def load(self, data):
        page = OggPage(data)
        while not page.packets[0].startswith("\x7FFLAC"):
            print repr(page.packets[0])
            page = OggPage(data)
        major, minor, self.packets, flac = struct.unpack(
            ">BBH4s", page.packets[0][5:13])
        if flac != "fLaC":
            raise IOError("invalid FLAC marker (%r)" % flac)
        elif (major, minor) != (1, 0):
            raise IOError("unknown mapping version: %d.%d" % (major, minor))
        self.serial = page.serial

        # Skip over the block header.
        stringobj = StringIO(page.packets[0][17:])
        super(OggFLACStreamInfo, self).load(StringIO(page.packets[0][17:]))

class OggFLACVComment(VCFLACDict):
    def load(self, data, info, errors='replace'):
        # data should be pointing at the start of an Ogg page, after
        # the first FLAC page.
        pages = []
        complete = False
        while not complete:
            page = OggPage(data)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        comment = StringIO(OggPage.to_packets(pages)[0][4:])
        super(OggFLACVComment, self).load(comment, errors)

    def _inject(self, fileobj):
        """Write tag data into the FLAC Vorbis comment packet/page."""
        fileobj.seek(0)

        # Ogg FLAC has no convenient data marker like Vorbis, but the
        # second packet - and second page - must be the comment data.
        page = OggPage(fileobj)
        while not page.packets[0].startswith("\x7FFLAC"):
            OggPage(fileobj)
        first_page = page
        while not (page.sequence == 1 and page.serial == first_page.serial):
            page = OggPage(fileobj)

        old_pages = [page]
        while not (old_pages[-1].complete or len(old_pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == first_page.serial:
                old_pages.append(page)

        packets = OggPage.to_packets(old_pages)

        # Set the new comment block. Set our flags to the
        # previous Ogg block's; that's what we're overwriting.
        data = self.write()
        data = packets[0][0] + struct.pack(">I", len(data))[-3:] + data
        packets[0] = data

        # Render the new pages, copying the header from the old ones.
        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        for page in new_pages:
            page.serial = old_pages[0].serial
        new_pages[-1].complete = old_pages[-1].complete
        new_data = "".join(map(OggPage.write, new_pages))

        # Make room in the file for the new data.
        delta = len(new_data)
        fileobj.seek(old_pages[0].offset, 0)
        Metadata._insert_space(fileobj, delta, old_pages[0].offset)
        fileobj.seek(old_pages[0].offset, 0)
        fileobj.write(new_data)
        new_data_end = fileobj.tell()

        # Go through the old pages and delete them. Since we shifted
        # the data down the file, we need to adjust their offsets. We
        # also need to go backwards, so we don't adjust the deltas of
        # the other pages.
        old_pages.reverse()
        for old_page in old_pages:
            adj_offset = old_page.offset + delta
            Metadata._delete_bytes(fileobj, old_page.size, adj_offset)

        # Finally, if there's any discrepency in length, we need to
        # renumber the pages for the logical stream.
        if len(old_pages) != len(new_pages):
            fileobj.seek(new_data_end, 0)
            serial = new_pages[-1].serial
            sequence = new_pages[-1].sequence + 1
            OggPage.renumber(fileobj, serial, sequence)

class OggFLAC(FileType):
    def score(filename, fileobj, header):
        return (header.startswith("OggS") + ("FLAC" in header) +
                ("fLaC" in header))
    score = staticmethod(score)

    def __init__(self, filename=None):
        if filename:
            self.load(filename)

    def load(self, filename):
        """Load file information from a filename."""

        # FIXME: This is almost verbatim from OggVorbis.

        self.filename = filename
        fileobj = file(filename, "rb")
        try:
            try:
                self.info = OggFLACStreamInfo(fileobj)
                self.tags = OggFLACVComment(fileobj, self.info)

                if self.info.length:
                    # The streaminfo gave us real length information,
                    # don't waste time scanning the Ogg.
                    return

                # For non-muxed streams, look at the last page.
                try: fileobj.seek(-256*256, 2)
                except IOError:
                    # The file is less than 64k in length.
                    fileobj.seek(0)
                data = fileobj.read()
                try: index = data.rindex("OggS")
                except ValueError:
                    raise OggFLACNoHeaderError(
                        "unable to find final Ogg header")
                stringobj = StringIO(data[index:])
                last_page = OggPage(stringobj)
                if last_page.serial == self.info.serial:
                    samples = last_page.position
                else:
                    # The stream is muxed, so use the slow way.
                    fileobj.seek(0)
                    page = OggPage(fileobj)
                    samples = page.position
                    while not page.last:
                        while page.serial != self.info.serial:
                            page = OggPage(fileobj)
                        if page.serial == self.info.serial:
                            samples = max(samples, page.position)

                self.info.length = samples / float(self.info.sample_rate)

            except IOError, e:
                raise OggFLACNoHeaderError(e)
        finally:
            fileobj.close()

    def delete(self, filename=None):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename

        self.tags.clear()
        fileobj = file(filename, "rb+")
        try:
            try: self.tags._inject(fileobj)
            except IOError, e:
                raise OggFLACNoHeaderError(e)
        finally:
            fileobj.close()

    def save(self, filename=None):
        """Save a tag to a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename
        self.tags.validate()
        fileobj = file(filename, "rb+")
        try:
            try: self.tags._inject(fileobj)
            except IOError, e:
                raise OggFLACNoHeaderError(e)
        finally:
            fileobj.close()

Open = OggFLAC

def delete(filename):
    """Remove tags from a file."""
    OggFLAC(filename).delete()
