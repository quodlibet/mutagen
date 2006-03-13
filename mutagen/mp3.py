# MP3 stream header information support for Mutagen.
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os
import struct

from mutagen import FileType
from mutagen.id3 import ID3, BitPaddedInt, error as ID3Error

class error(RuntimeError): pass
class HeaderNotFoundError(error, IOError): pass
class InvalidMPEGHeader(error, IOError): pass

class MPEGInfo(object):
    """Parse information about an MPEG audio file; most importantly,
    get the length. Since this can be incredibly inaccurate (e.g. when
    lacking a Xing header in a VBR MP3) it is recommended you let
    the TLEN tag, if present, override it.

    http://www.dv.co.yu/mpgscript/mpeghdr.htm documents the header
    format this code parses.

    For best performance and accuracy, call the constructor with an
    file-like object and the suspected start of the audio data (i.e.
    after any metadata tags, but before a Xing tag). I can't emphasize
    enough how important a good offset is.

    This code tries very hard to find MPEG headers. It might try too hard,
    and load files that are not MPEG audio. If the 'sketchy' attribute
    is set, then it's not entirely sure it found an accurate MPEG header.
    """


    # Map (version, layer) tuples to bitrates.
    __BITRATE = {
        (1, 1): range(0, 480, 32),
        (1, 2): [0, 32, 48, 56, 64, 80, 96, 112,128,160,192,224,256,320,384],
        (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112,128,160,192,224,256,320],
        (2, 1): [0, 32, 48, 56, 64, 80, 96, 112,128,144,160,176,192,224,256],
        (2, 2): [0,  8, 16, 24, 32, 40, 48,  56, 64, 80, 96,112,128,144,160],
        }
        
    __BITRATE[(2, 3)] = __BITRATE[(2, 2)]
    for i in range(1, 4): __BITRATE[(2.5, i)] = __BITRATE[(2, i)]

    # Map version to sample rates.
    __RATES = {
        1: [44100, 48000, 32000],
        2: [22050, 24000, 16000],
        2.5: [11025, 12000, 8000]
        }

    sketchy = False

    def __init__(self, fileobj, offset=None):
        try: size = os.path.getsize(fileobj.name)
        except (IOError, OSError, AttributeError):
            fileobj.seek(0, 2)
            size = fileobj.tell()

        # If we don't get an offset, try to skip an ID3v2 tag.
        if offset is None:
            fileobj.seek(0, 0)
            idata = fileobj.read(10)
            try: id3, insize = struct.unpack('>3sxxx4s', idata)
            except struct.error: id3, insize = '', 0
            insize = BitPaddedInt(insize)
            if id3 == 'ID3' and insize > 0:
                offset = insize
            else: offset = 0

        # Try to find two valid headers (meaning, very likely MPEG data)
        # at the given offset, 30% through the file, 60% through the file,
        # and 90% through the file.
        for i in [offset, 0.3 * size, 0.6 * size, 0.9 * size]:
            try: self.__try(fileobj, i, size - offset)
            except error, e: pass
            else: break
        # If we can't find any two consecutive frames, try to find just
        # one frame back at the original offset given.
        else:
            self.__try(fileobj, offset, size - offset, False)
            self.sketchy = True

    def __try(self, fileobj, offset, real_size, check_second=True):
        # This is going to be one really long function; bear with it,
        # because there's not really a sane point to cut it up.
        fileobj.seek(offset, 0)

        # We "know" we have an MPEG file if we find two frames that look like
        # valid MPEG data. If we can't find them in 32k of reads, something
        # is horribly wrong (the longest frame can only be about 4k). This
        # is assuming the offset didn't lie.
        data = fileobj.read(32768)

        frame_1 = data.find("\xff")
        while 0 <= frame_1 <= len(data) - 4:
            frame_data = struct.unpack(">I", data[frame_1:frame_1 + 4])[0]
            if (frame_data >> 16) & 0xE0 != 0xE0:
                frame_1 = data.find("\xff", frame_1 + 2)
            else:
                version = (frame_data >> 19) & 0x3
                layer = (frame_data >> 17) & 0x3
                protection = (frame_data >> 16) & 0x1
                bitrate = (frame_data >> 12) & 0xF
                sample_rate = (frame_data >> 10) & 0x3
                padding = (frame_data >> 9) & 0x1
                private = (frame_data >> 8) & 0x1
                mode = (frame_data >> 6) & 0x3
                mode_extension = (frame_data >> 4) & 0x3
                copyright = (frame_data >> 3) & 0x1
                original = (frame_data >> 2) & 0x1
                emphasis = (frame_data >> 0) & 0x3
                if (version == 1 or layer == 0 or sample_rate == 0x3 or
                    bitrate == 0 or bitrate == 0xF):
                    frame_1 = data.find("\xff", frame_1 + 2)
                else: break
        else:
            raise HeaderNotFoundError("can't sync to an MPEG frame")

        # There is a serious problem here, which is that many flags
        # in an MPEG header are backwards.
        self.version = [2.5, None, 2, 1][version]
        self.layer = 4 - layer
        self.protected = not protection
        self.padding = bool(padding)

        self.bitrate = self.__BITRATE[(self.version, self.layer)][bitrate]
        self.bitrate *= 1000
        self.sample_rate = self.__RATES[self.version][sample_rate]

        if self.layer == 1:
            frame_length = (12 * self.bitrate / self.sample_rate + padding) * 4
            frame_size = 384
        else:
            frame_length = 144 * self.bitrate / self.sample_rate + padding
            frame_size = 1152

        if check_second:
            possible = frame_1 + frame_length
            if possible > len(data) + 4:
                raise HeaderNotFoundError("can't sync to second MPEG frame")
            frame_data = struct.unpack(">H", data[possible:possible + 2])[0]
            if frame_data & 0xFFE0 != 0xFFE0:
                raise HeaderNotFoundError("can't sync to second MPEG frame")

        frame_count = real_size / float(frame_length)
        samples = frame_size * frame_count
        self.length = samples / self.sample_rate

        # Try to find/parse the Xing header, which trumps the above length
        # and bitrate calculation.
        fileobj.seek(offset, 0)
        data = fileobj.read(32768)
        try:
            xing = data[:-4].index("Xing")
        except ValueError: pass
        else:
            flags = struct.unpack('>I', data[xing + 4:xing + 8])[0]
            if flags & 0x1:
                frame_count = struct.unpack('>I', data[xing + 8:xing + 12])[0]
                samples = frame_size * frame_count
                self.length = samples / self.sample_rate
            if flags & 0x2:
                bytes = struct.unpack('>I', data[xing + 12:xing + 16])[0]
                self.bitrate = (bytes * 8) // self.length

class MP3(FileType):
    """An MPEG audio (usually MPEG-1 Layer 3) object, optionally
    with ID3 tags as .tags."""

    def __init__(self, filename=None, ID3=ID3):
        if filename is not None:
            self.load(filename, ID3)

    def pprint(self):
        s = "MPEG %s layer %d, %d bps, %s Hz, %.2f seconds" %(
            self.info.version, self.info.layer, self.info.bitrate,
            self.info.sample_rate, self.info.length)
        if self.tags is not None:
            return s + "\n" + self.tags.pprint()
        else: return s

    def add_tags(self):
        if self.tags is None:
            self.tags = ID3()
        else: raise ID3Error("a ID3 tag already exists")

    def load(self, filename, ID3=ID3):
        self.filename = filename
        try: self.tags = ID3(filename)
        except ID3Error: pass
        if self.tags is not None: offset = self.tags._size
        else: offset = None
        self.info = MPEGInfo(file(filename, "rb"), offset)

    def save(self, filename=None):
        if self.tags is not None:
            self.tags.save(filename)

Open = MP3

def delete(filename):
    """Remove tags from a file."""
    MP3(filename).delete()

