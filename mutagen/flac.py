# FLAC comment support for Mutagen
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

# Based off documentation available at
# http://flac.sourceforge.net/format.html

# FLAC files use Vorbis comments, but in a different fashion.
# This module doesn't handle Ogg FLAC files, either.

import struct
from cStringIO import StringIO
from _vorbis import VCommentDict

"""Read metadata from a FLAC file.

Based on the documentation at http://flac.sourceforge.net/format.html.

Ogg FLAC is not supported."""

def to_int_be(string):
    """Convert an arbitrarily-long string to a long using big-endian
    byte order."""
    return reduce(lambda a, b: (a << 8) + ord(b), string, 0L)

class MetadataBlock(object):
    """A generic block of metadata, used as an ancestor for more specific
    blocks, and also as a container for data blobs of unknown blocks."""

    def __init__(self, data):
        """Parse the given data string or file-like as a metadata block.
        The metadata header should not be included."""
        if data is not None:
            if isinstance(data, str): data = StringIO(data)
            elif not hasattr(data, 'read'):
                raise TypeError(
                    "StreamInfo requires string data or a file-like")
            self.load(data)

    def load(self, data): self.data = data.read()
    def write(self): return self.data

class StreamInfo(MetadataBlock):
    """Parse a FLAC's stream information metadata block. This contains
    information about the block size and sample format."""

    def load(self, data):
        self.min_blocksize = int(to_int_be(data.read(2)))
        self.max_blocksize = int(to_int_be(data.read(2)))
        self.min_framesize = int(to_int_be(data.read(3)))
        self.max_framesize = int(to_int_be(data.read(3)))
        # first 16 bits of sample rate
        sample_first = to_int_be(data.read(2))
        # last 4 bits of sample rate, 3 of channels, first 1 of bits/sample
        sample_channels_bps = to_int_be(data.read(1))
        # last 4 of bits/sample, 36 of total samples
        bps_total = to_int_be(data.read(5))

        sample_tail = sample_channels_bps >> 4
        self.sample_rate = int((sample_first << 4) + sample_tail)
        self.channels = int(((sample_channels_bps >> 1) & 7) + 1)
        bps_tail = bps_total >> 36
        bps_head = (sample_channels_bps & 1) << 4
        self.bits_per_sample = int(bps_head + bps_tail + 1)
        self.total_samples = bps_total & 0xFFFFFFFFF
        self.length = self.total_samples / float(self.sample_rate)

        self.md5_signature = to_int_be(data.read(16))

class VCFLACDict(VCommentDict):
    """FLACs don't use the framing bit at the end of the comment block.
    So don't expect it during reads, and chop it off during writes."""

    def load(self, data, errors='replace'):
        super(VCFLACDict, self).load(data, errors, False)

    def write(self):
        return super(VCFLACDict, self).write()[:-1]

class Padding(MetadataBlock):
    """A block consisting of null padding. Its size can be adjusted by
    changing the 'length' attribute.

    Usually this will follow a Vorbis comment, to avoid needing to
    resize the file when changing tags."""

    def __init__(self, data=""): super(Padding, self).__init__(data)
    def load(self, data): self.length = len(data.read())
    def write(self): return "\x00" * self.length

class FLAC(object):
    METADATA_BLOCKS = [StreamInfo, Padding, None, None, VCFLACDict]

    def __init__(self, filename=None):
        self.metadata_blocks = []
        if filename is not None: self.load(filename)

    def __read_metadata_block(self, file):
        byte = ord(file.read(1))
        size = to_int_be(file.read(3))
        try:
            data = file.read(size)
            block = self.METADATA_BLOCKS[byte & 0x7f](data)
        except (IndexError, TypeError):
            self.metadata_blocks.append(MetadataBlock(data))
        else: self.metadata_blocks.append(block)
        return (byte >> 7) ^ 1

    def load(self, filename):
        f = file(filename, "rb")
        if f.read(4) != "fLaC":
            raise IOError("%r is not a valid FLAC file" % filename)
        while self.__read_metadata_block(f): pass

        try: self.metadata_blocks[0].length
        except (AttributeError, IndexError):
            raise IOError("STREAMINFO block not found")
        else: self.info = self.metadata_blocks[0]
