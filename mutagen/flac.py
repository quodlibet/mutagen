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
from mutagen import Metadata

"""Read metadata from a FLAC file.

Based on the documentation at http://flac.sourceforge.net/format.html.

Ogg FLAC is not supported."""

class error(IOError): pass
class FLACNoHeaderError(error): pass
class FLACVorbisError(ValueError, error): pass

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

    def writeblocks(blocks):
        data = []
        codes = [[block.code, block.write()] for block in blocks]
        codes[-1][0] |= 128
        for code, datum in codes:
            byte = chr(code)
            length = struct.pack(">I", len(datum))[-3:]
            data.append(byte + length + datum)
        return "".join(data)
    writeblocks = staticmethod(writeblocks)

    def group_padding(blocks):
        """Replace any padding metadata blocks with a single block
        at the end, maintaining the same size as the old blocks."""
        paddings = filter(lambda x: isinstance(x, Padding), blocks)
        map(blocks.remove, paddings)
        padding = Padding()
        # total padding size is the sum of padding sizes plus 4 bytes
        # per removed header.
        size = sum([padding.length for padding in paddings])
        padding.length = size + 4 * (len(paddings) - 1)
        blocks.append(padding)
    group_padding = staticmethod(group_padding)

class StreamInfo(MetadataBlock):
    """Parse a FLAC's stream information metadata block. This contains
    information about the block size and sample format."""

    code = 0

    def __eq__(self, other):
        try: return (self.min_blocksize == other.min_blocksize and
                     self.max_blocksize == other.max_blocksize and
                     self.sample_rate == other.sample_rate and
                     self.channels == other.channels and
                     self.bits_per_sample == other.bits_per_sample and
                     self.total_samples == other.total_samples)
        except: return False

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
        self.total_samples = bps_total & 0xFFFFFFFFFL
        self.length = self.total_samples / float(self.sample_rate)

        self.md5_signature = to_int_be(data.read(16))

    def write(self):
        f = StringIO()
        f.write(struct.pack(">I", self.min_blocksize)[-2:])
        f.write(struct.pack(">I", self.max_blocksize)[-2:])
        f.write(struct.pack(">I", self.min_framesize)[-3:])
        f.write(struct.pack(">I", self.max_framesize)[-3:])

        # first 16 bits of sample rate
        f.write(struct.pack(">I", self.sample_rate >> 4)[-2:])
        # 4 bits sample, 3 channel, 1 bps
        byte = (self.sample_rate & 0xF) << 4
        byte += ((self.channels - 1) & 3) << 1
        byte += ((self.bits_per_sample - 1) >> 4) & 1
        f.write(chr(byte))
        # 4 bits of bps, 4 of sample count
        byte = ((self.bits_per_sample - 1) & 0xF)  << 4
        byte += (self.total_samples >> 32) & 0xF
        f.write(chr(byte))
        # last 32 of sample count
        f.write(struct.pack(">I", self.total_samples & 0xFFFFFFFFL))
        # MD5 signature
        sig = self.md5_signature
        f.write(struct.pack(
            ">4I", (sig >> 96) & 0xFFFFFFFFL, (sig >> 64) & 0xFFFFFFFFL,
            (sig >> 32) & 0xFFFFFFFFL, sig & 0xFFFFFFFFL))
        return f.getvalue()

class VCFLACDict(VCommentDict):
    """FLACs don't use the framing bit at the end of the comment block.
    So don't expect it during reads, and chop it off during writes."""

    code = 4

    def load(self, data, errors='replace'):
        super(VCFLACDict, self).load(data, errors, False)

    def write(self):
        return super(VCFLACDict, self).write()[:-1]

class Padding(MetadataBlock):
    """A block consisting of null padding. Its size can be adjusted by
    changing the 'length' attribute.

    Usually this will follow a Vorbis comment, to avoid needing to
    resize the file when changing tags."""

    code = 1

    def __init__(self, data=""): super(Padding, self).__init__(data)
    def load(self, data): self.length = len(data.read())
    def write(self): return "\x00" * self.length
    def __repr__(self):
        return "<%s (%d bytes)>" % (type(self).__name__, self.length)

class FLAC(object):
    METADATA_BLOCKS = [StreamInfo, Padding, None, None, VCFLACDict]

    vc = None

    def __init__(self, filename=None):
        self.metadata_blocks = []
        if filename is not None: self.load(filename)

    def pprint(self):
        return "\n".join(["%s=%s" % (k.lower(), v) for k, v in (self.vc or [])])

    def __read_metadata_block(self, file):
        byte = ord(file.read(1))
        size = to_int_be(file.read(3))
        try:
            data = file.read(size)
            block = self.METADATA_BLOCKS[byte & 0x7F](data)
        except (IndexError, TypeError):
            block = MetadataBlock(data)
            block.code = byte & 0x7F
            self.metadata_blocks.append(block)
        else:
            self.metadata_blocks.append(block)
            if block.code == VCFLACDict.code:
                if self.vc is None: self.vc = block
                else: raise FLACVorbisError("> 1 Vorbis comment block found")
        return (byte >> 7) ^ 1

    def add_vorbiscomment(self):
        if self.vc is None:
            self.vc = VCFLACDict()
            self.metadata_blocks.append(self.vc)
        else: raise FLACVorbisError("a Vorbis comment already exists")

    def __getitem__(self, key):
        if self.vc is None: raise KeyError, key
        else: return self.vc[key]

    def __setitem__(self, key, value):
        if self.vc is None: self.add_vorbiscomment()
        self.vc[key] = value

    def __delitem__(self, key):
        if self.vc is None: raise KeyError, key
        else: del(self.vc[key])

    def keys(self):
        if self.vc is None: return []
        else: return self.vc.keys()

    def values(self):
        if self.vc is None: return []
        else: return self.vc.values()

    def items(self):
        if self.vc is None: return []
        else: return self.vc.items()

    def load(self, filename):
        self.filename = filename
        f = file(filename, "rb")
        if f.read(4) != "fLaC":
            raise FLACNoHeaderError("%r is not a valid FLAC file" % filename)
        while self.__read_metadata_block(f): pass

        try: self.metadata_blocks[0].length
        except (AttributeError, IndexError):
            raise FLACNoHeaderError("Stream info block not found")

    info = property(lambda s: s.metadata_blocks[0])

    def save(self, filename=None):
        if filename is None: filename = self.filename
        f = open(filename, 'rb+')

        # Ensure we've got padding at the end, and only at the end.
        # If adding makes it too large, we'll scale it down later.
        self.metadata_blocks.append(Padding('\x00' * 1020))
        MetadataBlock.group_padding(self.metadata_blocks)

        available = self.__find_audio_offset(f) - 4 # "fLaC"
        data = MetadataBlock.writeblocks(self.metadata_blocks)

        if len(data) > available:
            # If we have too much data, see if we can reduce padding.
            padding = self.metadata_blocks[-1]
            newlength = padding.length - (len(data) - available)
            if newlength > 0:
                padding.length = newlength
                data = MetadataBlock.writeblocks(self.metadata_blocks)
                assert len(data) == available

        elif len(data) < available:
            # If we hve too little data, increase padding.
            self.metadata_blocks[-1].length += (available - len(data))
            data = MetadataBlock.writeblocks(self.metadata_blocks)
            assert len(data) == available

        if len(data) != available:
            # We couldn't reduce the padding enough.
            diff = (len(data) - available)
            Metadata._insert_space(f, diff, 4)

        f.seek(4)
        f.write(data)

    def __find_audio_offset(self, fileobj):
        if fileobj.read(4) != "fLaC":
            raise FLACNoHeaderError("%r is not a valid FLAC file" % filename)
        byte = 0x00
        while not (byte >> 7) & 1:
            byte = ord(fileobj.read(1))
            size = to_int_be(fileobj.read(3))
            fileobj.read(size)
        return fileobj.tell()
