# A Musepack reader/tagger
#
# Copyright 2006 Lukas Lalinsky <lalinsky@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Musepack audio streams with APEv2 tags.

Musepack is an audio format originally based on the MPEG-1 Layer-2
algorithms. Stream versions 4 through 7 are supported.

For more information, see http://www.musepack.net/.
"""

__all__ = ["Musepack", "Open", "delete"]

from mutagen.apev2 import APEv2File, error, delete
from mutagen._util import cdata

class MusepackHeaderError(error): pass

RATES = [44100, 48000, 37800, 32000]

class MusepackInfo(object):
    """Musepack stream information.

    Attributes:
    channels -- number of audio channels
    length -- file length in seconds, as a float
    sample_rate -- audio sampling rate in Hz
    bitrate -- audio bitrate, in bits per second 
    version -- Musepack stream version
    """

    def __init__(self, fileobj):
        header = fileobj.read(32)
        if len(header) != 32:
            raise MusepackHeaderError("not a Musepack file")
        # SV7
        if header.startswith("MP+"):
            self.version = ord(header[3]) & 0xF
            if self.version < 7:
                raise MusepackHeaderError("not a Musepack file")
            frames = cdata.uint_le(header[4:8])
            flags = cdata.uint_le(header[8:12])
            self.sample_rate = RATES[(flags >> 16) & 0x0003]
            self.bitrate = 0
        # SV4-SV6
        else:
            header_dword = cdata.uint_le(header[0:4])
            self.version = (header_dword >> 11) & 0x03FF;
            if self.version < 4 or self.version > 6:
                raise MusepackHeaderError("not a Musepack file")
            self.bitrate = (header_dword >> 23) & 0x01FF;
            self.sample_rate = 44100
            if self.version >= 5:
                frames = cdata.uint_le(header[4:8])
            else:
                frames = cdata.ushort_le(header[6:8])
            if self.version < 6:
                frames -= 1
        self.channels = 2
        self.length = float(frames * 1152 - 576) / self.sample_rate
        if not self.bitrate and self.length != 0:
            fileobj.seek(0, 2)
            self.bitrate = int(fileobj.tell() * 8 / (self.length * 1000) + 0.5)

    def pprint(self):
        return "Musepack, %.2f seconds, %d Hz" % (
            self.length, self.sample_rate)

class Musepack(APEv2File):
    _Info = MusepackInfo

    def score(filename, fileobj, header):
        return header.startswith("MP+") + filename.endswith(".mpc")
    score = staticmethod(score)

Open = Musepack
