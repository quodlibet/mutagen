# -*- coding: utf-8 -*-

# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky

#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write ASF (Window Media Audio) files."""

__all__ = ["ASF", "Open"]

import sys
import struct
from mutagen import FileType, Metadata, StreamInfo
from mutagen._util import (resize_bytes, DictMixin,
                           total_ordering, MutagenError, cdata)
from ._compat import swap_to_string, text_type, PY2, string_types, reraise, \
    xrange, long_, PY3


class error(IOError, MutagenError):
    pass


class ASFError(error):
    pass


class ASFHeaderError(error):
    pass


class ASFInfo(StreamInfo):
    """ASF stream information.

    :ivar float length: Length in seconds
    :ivar int sample_rate: Sample rate in Hz
    :ivar int bitrate: Bitrate in bps
    :ivar int channels: Number of channels
    :ivar text codec_type: Name of the codec type of the first audio stream or
        an empty string if unknown. Example: "Windows Media Audio 9 Standard"
    :ivar text codec_name: Name and maybe version of the codec used. Example:
        "Windows Media Audio 9.1"
    :ivar text codec_description: Further information on the codec used.
        Example: "64 kbps, 48 kHz, stereo 2-pass CBR"
    """

    def __init__(self):
        self.length = 0.0
        self.sample_rate = 0
        self.bitrate = 0
        self.channels = 0
        self.codec_type = u""
        self.codec_name = u""
        self.codec_description = u""

    def pprint(self):
        """Returns a stream information text summary

        :rtype: text
        """

        s = u"ASF (%s) %d bps, %s Hz, %d channels, %.2f seconds" % (
            self.codec_type or self.codec_name or u"???", self.bitrate,
            self.sample_rate, self.channels, self.length)
        return s


class ASFTags(list, DictMixin, Metadata):
    """Dictionary containing ASF attributes."""

    def pprint(self):
        return "\n".join("%s=%s" % (k, v) for k, v in self)

    def __getitem__(self, key):
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__getitem__(self, key)

        values = [value for (k, value) in self if k == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    def __delitem__(self, key):
        """Delete all values associated with the key."""

        # PY3 only
        if isinstance(key, slice):
            return list.__delitem__(self, key)

        to_delete = [x for x in self if x[0] == key]
        if not to_delete:
            raise KeyError(key)
        else:
            for k in to_delete:
                self.remove(k)

    def __contains__(self, key):
        """Return true if the key has any values."""
        for k, value in self:
            if k == key:
                return True
        else:
            return False

    def __setitem__(self, key, values):
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__setitem__(self, key, values)

        if not isinstance(values, list):
            values = [values]

        to_append = []
        for value in values:
            if not isinstance(value, ASFBaseAttribute):
                if isinstance(value, string_types):
                    value = ASFUnicodeAttribute(value)
                elif PY3 and isinstance(value, bytes):
                    value = ASFByteArrayAttribute(value)
                elif isinstance(value, bool):
                    value = ASFBoolAttribute(value)
                elif isinstance(value, int):
                    value = ASFDWordAttribute(value)
                elif isinstance(value, long_):
                    value = ASFQWordAttribute(value)
                else:
                    raise TypeError("Invalid type %r" % type(value))
            to_append.append((key, value))

        try:
            del(self[key])
        except KeyError:
            pass

        self.extend(to_append)

    def keys(self):
        """Return all keys in the comment."""
        return self and set(next(iter(zip(*self))))

    def as_dict(self):
        """Return a copy of the comment data in a real dict."""
        d = {}
        for key, value in self:
            d.setdefault(key, []).append(value)
        return d


class ASFBaseAttribute(object):
    """Generic attribute."""
    TYPE = None

    def __init__(self, value=None, data=None, language=None,
                 stream=None, **kwargs):
        self.language = language
        self.stream = stream
        if data:
            self.value = self.parse(data, **kwargs)
        else:
            if value is None:
                # we used to support not passing any args and instead assign
                # them later, keep that working..
                self.value = None
            else:
                self.value = self._validate(value)

    def _validate(self, value):
        """Raises TypeError or ValueError in case the user supplied value
        isn't valid.
        """

        return value

    def data_size(self):
        raise NotImplementedError

    def __repr__(self):
        name = "%s(%r" % (type(self).__name__, self.value)
        if self.language:
            name += ", language=%d" % self.language
        if self.stream:
            name += ", stream=%d" % self.stream
        name += ")"
        return name

    def render(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        data = self._render()
        return (struct.pack("<H", len(name)) + name +
                struct.pack("<HH", self.TYPE, len(data)) + data)

    def render_m(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        if self.TYPE == 2:
            data = self._render(dword=False)
        else:
            data = self._render()
        return (struct.pack("<HHHHI", 0, self.stream or 0, len(name),
                            self.TYPE, len(data)) + name + data)

    def render_ml(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        if self.TYPE == 2:
            data = self._render(dword=False)
        else:
            data = self._render()

        return (struct.pack("<HHHHI", self.language or 0, self.stream or 0,
                            len(name), self.TYPE, len(data)) + name + data)


@swap_to_string
@total_ordering
class ASFUnicodeAttribute(ASFBaseAttribute):
    """Unicode string attribute."""
    TYPE = 0x0000

    def parse(self, data):
        try:
            return data.decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError as e:
            reraise(ASFError, e, sys.exc_info()[2])

    def _validate(self, value):
        if not isinstance(value, text_type):
            if PY2:
                return value.decode("utf-8")
            else:
                raise TypeError("%r not str" % value)
        return value

    def _render(self):
        return self.value.encode("utf-16-le") + b"\x00\x00"

    def data_size(self):
        return len(self._render())

    def __bytes__(self):
        return self.value.encode("utf-16-le")

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return text_type(self) == other

    def __lt__(self, other):
        return text_type(self) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFByteArrayAttribute(ASFBaseAttribute):
    """Byte array attribute."""
    TYPE = 0x0001

    def parse(self, data):
        assert isinstance(data, bytes)
        return data

    def _render(self):
        assert isinstance(self.value, bytes)
        return self.value

    def _validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError("must be bytes/str: %r" % value)
        return value

    def data_size(self):
        return len(self.value)

    def __bytes__(self):
        return self.value

    def __str__(self):
        return "[binary data (%d bytes)]" % len(self.value)

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFBoolAttribute(ASFBaseAttribute):
    """Bool attribute."""
    TYPE = 0x0002

    def parse(self, data, dword=True):
        if dword:
            return struct.unpack("<I", data)[0] == 1
        else:
            return struct.unpack("<H", data)[0] == 1

    def _render(self, dword=True):
        if dword:
            return struct.pack("<I", bool(self.value))
        else:
            return struct.pack("<H", bool(self.value))

    def _validate(self, value):
        return bool(value)

    def data_size(self):
        return 4

    def __bool__(self):
        return bool(self.value)

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return bool(self.value) == other

    def __lt__(self, other):
        return bool(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFDWordAttribute(ASFBaseAttribute):
    """DWORD attribute."""
    TYPE = 0x0003

    def parse(self, data):
        return struct.unpack("<L", data)[0]

    def _render(self):
        return struct.pack("<L", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 32 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 4

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFQWordAttribute(ASFBaseAttribute):
    """QWORD attribute."""
    TYPE = 0x0004

    def parse(self, data):
        return struct.unpack("<Q", data)[0]

    def _render(self):
        return struct.pack("<Q", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 64 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 8

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFWordAttribute(ASFBaseAttribute):
    """WORD attribute."""
    TYPE = 0x0005

    def parse(self, data):
        return struct.unpack("<H", data)[0]

    def _render(self):
        return struct.pack("<H", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 16 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 2

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFGUIDAttribute(ASFBaseAttribute):
    """GUID attribute."""
    TYPE = 0x0006

    def parse(self, data):
        assert isinstance(data, bytes)
        return data

    def _render(self):
        assert isinstance(self.value, bytes)
        return self.value

    def _validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError("must be bytes/str: %r" % value)
        return value

    def data_size(self):
        return len(self.value)

    def __bytes__(self):
        return self.value

    def __str__(self):
        return repr(self.value)

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    __hash__ = ASFBaseAttribute.__hash__


UNICODE = ASFUnicodeAttribute.TYPE
BYTEARRAY = ASFByteArrayAttribute.TYPE
BOOL = ASFBoolAttribute.TYPE
DWORD = ASFDWordAttribute.TYPE
QWORD = ASFQWordAttribute.TYPE
WORD = ASFWordAttribute.TYPE
GUID = ASFGUIDAttribute.TYPE


def ASFValue(value, kind, **kwargs):
    try:
        attr_type = _attribute_types[kind]
    except KeyError:
        raise ValueError("Unknown value type %r" % kind)
    else:
        return attr_type(value=value, **kwargs)


_attribute_types = {
    ASFUnicodeAttribute.TYPE: ASFUnicodeAttribute,
    ASFByteArrayAttribute.TYPE: ASFByteArrayAttribute,
    ASFBoolAttribute.TYPE: ASFBoolAttribute,
    ASFDWordAttribute.TYPE: ASFDWordAttribute,
    ASFQWordAttribute.TYPE: ASFQWordAttribute,
    ASFWordAttribute.TYPE: ASFWordAttribute,
    ASFGUIDAttribute.TYPE: ASFGUIDAttribute,
}


class BaseObject(object):
    """Base ASF object."""
    GUID = None

    def parse(self, asf, data, fileobj, size):
        self.data = data

    def render(self, asf):
        data = self.GUID + struct.pack("<Q", len(self.data) + 24) + self.data
        return data


class UnknownObject(BaseObject):
    """Unknown ASF object."""
    def __init__(self, guid):
        assert isinstance(guid, bytes)
        self.GUID = guid


def _GUID(s):
    assert len(s) == 36

    p = struct.pack
    return b"".join([
        p("<IHH", int(s[:8], 16), int(s[9:13], 16), int(s[14:18], 16)),
        p(">H", int(s[19:23], 16)),
        p(">Q", int(s[24:], 16))[2:],
        ])


def _GUID_STR(s):
    assert isinstance(s, bytes)

    u = struct.unpack
    v = []
    v.extend(u("<IHH", s[:8]))
    v.extend(u(">HQ", s[8:10] + b"\x00\x00" + s[10:]))
    return "%08X-%04X-%04X-%04X-%012X" % tuple(v)


class HeaderObject(object):
    """ASF header."""

    GUID = _GUID("75B22630-668E-11CF-A6D9-00AA0062CE6C")


class ContentDescriptionObject(BaseObject):
    """Content description."""

    GUID = _GUID("75B22633-668E-11CF-A6D9-00AA0062CE6C")

    NAMES = [
        u"Title",
        u"Author",
        u"Copyright",
        u"Description",
        u"Rating",
    ]

    def parse(self, asf, data, fileobj, size):
        super(ContentDescriptionObject, self).parse(asf, data, fileobj, size)
        asf.content_description_obj = self
        lengths = struct.unpack("<HHHHH", data[:10])
        texts = []
        pos = 10
        for length in lengths:
            end = pos + length
            if length > 0:
                texts.append(data[pos:end].decode("utf-16-le").strip(u"\x00"))
            else:
                texts.append(None)
            pos = end

        for key, value in zip(self.NAMES, texts):
            if value is not None:
                value = ASFUnicodeAttribute(value=value)
                asf._tags.setdefault(self.GUID, []).append((key, value))

    def render(self, asf):
        def render_text(name):
            value = asf.to_content_description.get(name)
            if value is not None:
                return text_type(value).encode("utf-16-le") + b"\x00\x00"
            else:
                return b""

        texts = [render_text(x) for x in self.NAMES]
        data = struct.pack("<HHHHH", *map(len, texts)) + b"".join(texts)
        return self.GUID + struct.pack("<Q", 24 + len(data)) + data


class ExtendedContentDescriptionObject(BaseObject):
    """Extended content description."""

    GUID = _GUID("D2D0A440-E307-11D2-97F0-00A0C95EA850")

    def parse(self, asf, data, fileobj, size):
        super(ExtendedContentDescriptionObject, self).parse(
            asf, data, fileobj, size)
        asf.extended_content_description_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            name_length, = struct.unpack("<H", data[pos:pos + 2])
            pos += 2
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value_type, value_length = struct.unpack("<HH", data[pos:pos + 4])
            pos += 4
            value = data[pos:pos + value_length]
            pos += value_length
            attr = _attribute_types[value_type](data=value)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_extended_content_description.items()
        data = b"".join(attr.render(name) for (name, attr) in attrs)
        data = struct.pack("<QH", 26 + len(data), len(attrs)) + data
        return self.GUID + data


class FilePropertiesObject(BaseObject):
    """File properties."""

    GUID = _GUID("8CABDCA1-A947-11CF-8EE4-00C00C205365")

    def parse(self, asf, data, fileobj, size):
        super(FilePropertiesObject, self).parse(asf, data, fileobj, size)
        length, _, preroll = struct.unpack("<QQQ", data[40:64])
        asf.info.length = (length / 10000000.0) - (preroll / 1000.0)


class StreamPropertiesObject(BaseObject):
    """Stream properties."""

    GUID = _GUID("B7DC0791-A9B7-11CF-8EE6-00C00C205365")

    def parse(self, asf, data, fileobj, size):
        super(StreamPropertiesObject, self).parse(asf, data, fileobj, size)
        channels, sample_rate, bitrate = struct.unpack("<HII", data[56:66])
        asf.info.channels = channels
        asf.info.sample_rate = sample_rate
        asf.info.bitrate = bitrate * 8


# Names from http://windows.microsoft.com/en-za/windows7/c00d10d1-[0-9A-F]{1,4}
_CODECS = {
    0x0000: u"Unknown Wave Format",
    0x0001: u"Microsoft PCM Format",
    0x0002: u"Microsoft ADPCM Format",
    0x0003: u"IEEE Float",
    0x0004: u"Compaq Computer VSELP",
    0x0005: u"IBM CVSD",
    0x0006: u"Microsoft CCITT A-Law",
    0x0007: u"Microsoft CCITT u-Law",
    0x0008: u"Microsoft DTS",
    0x0009: u"Microsoft DRM",
    0x000A: u"Windows Media Audio 9 Voice",
    0x000B: u"Windows Media Audio 10 Voice",
    0x000C: u"OGG Vorbis",
    0x000D: u"FLAC",
    0x000E: u"MOT AMR",
    0x000F: u"Nice Systems IMBE",
    0x0010: u"OKI ADPCM",
    0x0011: u"Intel IMA ADPCM",
    0x0012: u"Videologic MediaSpace ADPCM",
    0x0013: u"Sierra Semiconductor ADPCM",
    0x0014: u"Antex Electronics G.723 ADPCM",
    0x0015: u"DSP Solutions DIGISTD",
    0x0016: u"DSP Solutions DIGIFIX",
    0x0017: u"Dialogic OKI ADPCM",
    0x0018: u"MediaVision ADPCM",
    0x0019: u"Hewlett-Packard CU codec",
    0x001A: u"Hewlett-Packard Dynamic Voice",
    0x0020: u"Yamaha ADPCM",
    0x0021: u"Speech Compression SONARC",
    0x0022: u"DSP Group True Speech",
    0x0023: u"Echo Speech EchoSC1",
    0x0024: u"Ahead Inc. Audiofile AF36",
    0x0025: u"Audio Processing Technology APTX",
    0x0026: u"Ahead Inc. AudioFile AF10",
    0x0027: u"Aculab Prosody 1612",
    0x0028: u"Merging Technologies S.A. LRC",
    0x0030: u"Dolby Labs AC2",
    0x0031: u"Microsoft GSM 6.10",
    0x0032: u"Microsoft MSNAudio",
    0x0033: u"Antex Electronics ADPCME",
    0x0034: u"Control Resources VQLPC",
    0x0035: u"DSP Solutions Digireal",
    0x0036: u"DSP Solutions DigiADPCM",
    0x0037: u"Control Resources CR10",
    0x0038: u"Natural MicroSystems VBXADPCM",
    0x0039: u"Crystal Semiconductor IMA ADPCM",
    0x003A: u"Echo Speech EchoSC3",
    0x003B: u"Rockwell ADPCM",
    0x003C: u"Rockwell DigiTalk",
    0x003D: u"Xebec Multimedia Solutions",
    0x0040: u"Antex Electronics G.721 ADPCM",
    0x0041: u"Antex Electronics G.728 CELP",
    0x0042: u"Intel G.723",
    0x0043: u"Intel G.723.1",
    0x0044: u"Intel G.729 Audio",
    0x0045: u"Sharp G.726 Audio",
    0x0050: u"Microsoft MPEG-1",
    0x0052: u"InSoft RT24",
    0x0053: u"InSoft PAC",
    0x0055: u"MP3 - MPEG Layer III",
    0x0059: u"Lucent G.723",
    0x0060: u"Cirrus Logic",
    0x0061: u"ESS Technology ESPCM",
    0x0062: u"Voxware File-Mode",
    0x0063: u"Canopus Atrac",
    0x0064: u"APICOM G.726 ADPCM",
    0x0065: u"APICOM G.722 ADPCM",
    0x0066: u"Microsoft DSAT",
    0x0067: u"Microsoft DSAT Display",
    0x0069: u"Voxware Byte Aligned",
    0x0070: u"Voxware AC8",
    0x0071: u"Voxware AC10",
    0x0072: u"Voxware AC16",
    0x0073: u"Voxware AC20",
    0x0074: u"Voxware RT24 MetaVoice",
    0x0075: u"Voxware RT29 MetaSound",
    0x0076: u"Voxware RT29HW",
    0x0077: u"Voxware VR12",
    0x0078: u"Voxware VR18",
    0x0079: u"Voxware TQ40",
    0x007A: u"Voxware SC3",
    0x007B: u"Voxware SC3",
    0x0080: u"Softsound",
    0x0081: u"Voxware TQ60",
    0x0082: u"Microsoft MSRT24",
    0x0083: u"AT&T Labs G.729A",
    0x0084: u"Motion Pixels MVI MV12",
    0x0085: u"DataFusion Systems G.726",
    0x0086: u"DataFusion Systems GSM610",
    0x0088: u"Iterated Systems ISIAudio",
    0x0089: u"Onlive",
    0x008A: u"Multitude FT SX20",
    0x008B: u"Infocom ITS ACM G.721",
    0x008C: u"Convedia G.729",
    0x008D: u"Congruency Audio",
    0x0091: u"Siemens Business Communications SBC24",
    0x0092: u"Sonic Foundry Dolby AC3 SPDIF",
    0x0093: u"MediaSonic G.723",
    0x0094: u"Aculab Prosody 8KBPS",
    0x0097: u"ZyXEL ADPCM",
    0x0098: u"Philips LPCBB",
    0x0099: u"Studer Professional Audio AG Packed",
    0x00A0: u"Malden Electronics PHONYTALK",
    0x00A1: u"Racal Recorder GSM",
    0x00A2: u"Racal Recorder G720.a",
    0x00A3: u"Racal Recorder G723.1",
    0x00A4: u"Racal Recorder Tetra ACELP",
    0x00B0: u"NEC AAC",
    0x00FF: u"CoreAAC Audio",
    0x0100: u"Rhetorex ADPCM",
    0x0101: u"BeCubed Software IRAT",
    0x0111: u"Vivo G.723",
    0x0112: u"Vivo Siren",
    0x0120: u"Philips CELP",
    0x0121: u"Philips Grundig",
    0x0123: u"Digital G.723",
    0x0125: u"Sanyo ADPCM",
    0x0130: u"Sipro Lab Telecom ACELP.net",
    0x0131: u"Sipro Lab Telecom ACELP.4800",
    0x0132: u"Sipro Lab Telecom ACELP.8V3",
    0x0133: u"Sipro Lab Telecom ACELP.G.729",
    0x0134: u"Sipro Lab Telecom ACELP.G.729A",
    0x0135: u"Sipro Lab Telecom ACELP.KELVIN",
    0x0136: u"VoiceAge AMR",
    0x0140: u"Dictaphone G.726 ADPCM",
    0x0141: u"Dictaphone CELP68",
    0x0142: u"Dictaphone CELP54",
    0x0150: u"Qualcomm PUREVOICE",
    0x0151: u"Qualcomm HALFRATE",
    0x0155: u"Ring Zero Systems TUBGSM",
    0x0160: u"Windows Media Audio Standard",
    0x0161: u"Windows Media Audio 9 Standard",
    0x0162: u"Windows Media Audio 9 Professional",
    0x0163: u"Windows Media Audio 9 Lossless",
    0x0164: u"Windows Media Audio Pro over SPDIF",
    0x0170: u"Unisys NAP ADPCM",
    0x0171: u"Unisys NAP ULAW",
    0x0172: u"Unisys NAP ALAW",
    0x0173: u"Unisys NAP 16K",
    0x0174: u"Sycom ACM SYC008",
    0x0175: u"Sycom ACM SYC701 G725",
    0x0176: u"Sycom ACM SYC701 CELP54",
    0x0177: u"Sycom ACM SYC701 CELP68",
    0x0178: u"Knowledge Adventure ADPCM",
    0x0180: u"Fraunhofer IIS MPEG-2 AAC",
    0x0190: u"Digital Theater Systems DTS",
    0x0200: u"Creative Labs ADPCM",
    0x0202: u"Creative Labs FastSpeech8",
    0x0203: u"Creative Labs FastSpeech10",
    0x0210: u"UHER informatic GmbH ADPCM",
    0x0215: u"Ulead DV Audio",
    0x0216: u"Ulead DV Audio",
    0x0220: u"Quarterdeck",
    0x0230: u"I-link Worldwide ILINK VC",
    0x0240: u"Aureal Semiconductor RAW SPORT",
    0x0249: u"Generic Passthru",
    0x0250: u"Interactive Products HSX",
    0x0251: u"Interactive Products RPELP",
    0x0260: u"Consistent Software CS2",
    0x0270: u"Sony SCX",
    0x0271: u"Sony SCY",
    0x0272: u"Sony ATRAC3",
    0x0273: u"Sony SPC",
    0x0280: u"Telum Audio",
    0x0281: u"Telum IA Audio",
    0x0285: u"Norcom Voice Systems ADPCM",
    0x0300: u"Fujitsu TOWNS SND",
    0x0350: u"Micronas SC4 Speech",
    0x0351: u"Micronas CELP833",
    0x0400: u"Brooktree BTV Digital",
    0x0401: u"Intel Music Coder",
    0x0402: u"Intel Audio",
    0x0450: u"QDesign Music",
    0x0500: u"On2 AVC0 Audio",
    0x0501: u"On2 AVC1 Audio",
    0x0680: u"AT&T Labs VME VMPCM",
    0x0681: u"AT&T Labs TPC",
    0x08AE: u"ClearJump Lightwave Lossless",
    0x1000: u"Olivetti GSM",
    0x1001: u"Olivetti ADPCM",
    0x1002: u"Olivetti CELP",
    0x1003: u"Olivetti SBC",
    0x1004: u"Olivetti OPR",
    0x1100: u"Lernout & Hauspie",
    0x1101: u"Lernout & Hauspie CELP",
    0x1102: u"Lernout & Hauspie SBC8",
    0x1103: u"Lernout & Hauspie SBC12",
    0x1104: u"Lernout & Hauspie SBC16",
    0x1400: u"Norris Communication",
    0x1401: u"ISIAudio",
    0x1500: u"AT&T Labs Soundspace Music Compression",
    0x1600: u"Microsoft MPEG ADTS AAC",
    0x1601: u"Microsoft MPEG RAW AAC",
    0x1608: u"Nokia MPEG ADTS AAC",
    0x1609: u"Nokia MPEG RAW AAC",
    0x181C: u"VoxWare MetaVoice RT24",
    0x1971: u"Sonic Foundry Lossless",
    0x1979: u"Innings Telecom ADPCM",
    0x1FC4: u"NTCSoft ALF2CD ACM",
    0x2000: u"Dolby AC3",
    0x2001: u"DTS",
    0x4143: u"Divio AAC",
    0x4201: u"Nokia Adaptive Multi-Rate",
    0x4243: u"Divio G.726",
    0x4261: u"ITU-T H.261",
    0x4263: u"ITU-T H.263",
    0x4264: u"ITU-T H.264",
    0x674F: u"Ogg Vorbis Mode 1",
    0x6750: u"Ogg Vorbis Mode 2",
    0x6751: u"Ogg Vorbis Mode 3",
    0x676F: u"Ogg Vorbis Mode 1+",
    0x6770: u"Ogg Vorbis Mode 2+",
    0x6771: u"Ogg Vorbis Mode 3+",
    0x7000: u"3COM NBX Audio",
    0x706D: u"FAAD AAC Audio",
    0x77A1: u"True Audio Lossless Audio",
    0x7A21: u"GSM-AMR CBR 3GPP Audio",
    0x7A22: u"GSM-AMR VBR 3GPP Audio",
    0xA100: u"Comverse Infosys G723.1",
    0xA101: u"Comverse Infosys AVQSBC",
    0xA102: u"Comverse Infosys SBC",
    0xA103: u"Symbol Technologies G729a",
    0xA104: u"VoiceAge AMR WB",
    0xA105: u"Ingenient Technologies G.726",
    0xA106: u"ISO/MPEG-4 Advanced Audio Coding (AAC)",
    0xA107: u"Encore Software Ltd's G.726",
    0xA108: u"ZOLL Medical Corporation ASAO",
    0xA109: u"Speex Voice",
    0xA10A: u"Vianix MASC Speech Compression",
    0xA10B: u"Windows Media 9 Spectrum Analyzer Output",
    0xA10C: u"Media Foundation Spectrum Analyzer Output",
    0xA10D: u"GSM 6.10 (Full-Rate) Speech",
    0xA10E: u"GSM 6.20 (Half-Rate) Speech",
    0xA10F: u"GSM 6.60 (Enchanced Full-Rate) Speech",
    0xA110: u"GSM 6.90 (Adaptive Multi-Rate) Speech",
    0xA111: u"GSM Adaptive Multi-Rate WideBand Speech",
    0xA112: u"Polycom G.722",
    0xA113: u"Polycom G.728",
    0xA114: u"Polycom G.729a",
    0xA115: u"Polycom Siren",
    0xA116: u"Global IP Sound ILBC",
    0xA117: u"Radio Time Time Shifted Radio",
    0xA118: u"Nice Systems ACA",
    0xA119: u"Nice Systems ADPCM",
    0xA11A: u"Vocord Group ITU-T G.721",
    0xA11B: u"Vocord Group ITU-T G.726",
    0xA11C: u"Vocord Group ITU-T G.722.1",
    0xA11D: u"Vocord Group ITU-T G.728",
    0xA11E: u"Vocord Group ITU-T G.729",
    0xA11F: u"Vocord Group ITU-T G.729a",
    0xA120: u"Vocord Group ITU-T G.723.1",
    0xA121: u"Vocord Group LBC",
    0xA122: u"Nice G.728",
    0xA123: u"France Telecom G.729 ACM Audio",
    0xA124: u"CODIAN Audio",
    0xCC12: u"Intel YUV12 Codec",
    0xCFCC: u"Digital Processing Systems Perception Motion JPEG",
    0xD261: u"DEC H.261",
    0xD263: u"DEC H.263",
    0xFFFE: u"Extensible Wave Format",
    0xFFFF: u"Unregistered",
}


class CodecListObject(BaseObject):
    """Codec List"""

    GUID = _GUID("86D15240-311D-11D0-A3A4-00A0C90348F6")

    def _parse_entry(self, data, offset):
        """can raise cdata.error"""

        type_, offset = cdata.uint16_le_from(data, offset)

        units, offset = cdata.uint16_le_from(data, offset)
        # utf-16 code units, not characters..
        next_offset = offset + units * 2
        try:
            name = data[offset:next_offset].decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError:
            name = u""
        offset = next_offset

        units, offset = cdata.uint16_le_from(data, offset)
        next_offset = offset + units * 2
        try:
            desc = data[offset:next_offset].decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError:
            desc = u""
        offset = next_offset

        bytes_, offset = cdata.uint16_le_from(data, offset)
        next_offset = offset + bytes_
        codec = u""
        if bytes_ == 2:
            codec_id = cdata.uint16_le_from(data, offset)[0]
            if codec_id in _CODECS:
                codec = _CODECS[codec_id]
        offset = next_offset

        return offset, type_, name, desc, codec

    def parse(self, asf, data, fileobj, size):
        super(CodecListObject, self).parse(asf, data, fileobj, size)

        offset = 16
        count, offset = cdata.uint32_le_from(data, offset)
        for i in xrange(count):
            try:
                offset, type_, name, desc, codec = \
                    self._parse_entry(data, offset)
            except cdata.error:
                raise ASFError("invalid codec entry")

            # go with the first audio entry
            if type_ == 2:
                name = name.strip()
                desc = desc.strip()
                asf.info.codec_type = codec
                asf.info.codec_name = name
                asf.info.codec_description = desc
                return


class HeaderExtensionObject(BaseObject):
    """Header extension."""

    GUID = _GUID("5FBF03B5-A92E-11CF-8EE3-00C00C205365")

    def parse(self, asf, data, fileobj, size):
        super(HeaderExtensionObject, self).parse(asf, data, fileobj, size)
        asf.header_extension_obj = self
        datasize, = struct.unpack("<I", data[18:22])
        datapos = 0
        self.objects = []
        while datapos < datasize:
            guid, size = struct.unpack(
                "<16sQ", data[22 + datapos:22 + datapos + 24])
            if guid in _object_types:
                obj = _object_types[guid]()
            else:
                obj = UnknownObject(guid)
            obj.parse(asf, data[22 + datapos + 24:22 + datapos + size],
                      fileobj, size)
            self.objects.append(obj)
            datapos += size

    def render(self, asf):
        data = b"".join(obj.render(asf) for obj in self.objects)
        return (self.GUID + struct.pack("<Q", 24 + 16 + 6 + len(data)) +
                b"\x11\xD2\xD3\xAB\xBA\xA9\xcf\x11" +
                b"\x8E\xE6\x00\xC0\x0C\x20\x53\x65" +
                b"\x06\x00" + struct.pack("<I", len(data)) + data)


class MetadataObject(BaseObject):
    """Metadata description."""

    GUID = _GUID("C5F8CBEA-5BAF-4877-8467-AA8C44FA4CCA")

    def parse(self, asf, data, fileobj, size):
        super(MetadataObject, self).parse(asf, data, fileobj, size)
        asf.metadata_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            (reserved, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = _attribute_types[value_type](**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata.items()
        data = b"".join([attr.render_m(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)


class MetadataLibraryObject(BaseObject):
    """Metadata library description."""

    GUID = _GUID("44231C94-9498-49D1-A141-1D134E457054")

    def parse(self, asf, data, fileobj, size):
        super(MetadataLibraryObject, self).parse(asf, data, fileobj, size)
        asf.metadata_library_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            (language, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'language': language, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = _attribute_types[value_type](**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata_library
        data = b"".join([attr.render_ml(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)


_object_types = {
    ExtendedContentDescriptionObject.GUID: ExtendedContentDescriptionObject,
    ContentDescriptionObject.GUID: ContentDescriptionObject,
    FilePropertiesObject.GUID: FilePropertiesObject,
    StreamPropertiesObject.GUID: StreamPropertiesObject,
    HeaderExtensionObject.GUID: HeaderExtensionObject,
    MetadataLibraryObject.GUID: MetadataLibraryObject,
    MetadataObject.GUID: MetadataObject,
    CodecListObject.GUID: CodecListObject,
}


class ASF(FileType):
    """An ASF file, probably containing WMA or WMV."""

    _mimes = ["audio/x-ms-wma", "audio/x-ms-wmv", "video/x-ms-asf",
              "audio/x-wma", "video/x-wmv"]

    def load(self, filename):
        self.filename = filename
        with open(filename, "rb") as fileobj:
            self.size = 0
            self.size1 = 0
            self.size2 = 0
            self.offset1 = 0
            self.offset2 = 0
            self.num_objects = 0
            self.info = ASFInfo()
            self.tags = ASFTags()
            self.__read_file(fileobj)

    def save(self):
        # Move attributes to the right objects
        self.to_content_description = {}
        self.to_extended_content_description = {}
        self.to_metadata = {}
        self.to_metadata_library = []
        for name, value in self.tags:
            library_only = (value.data_size() > 0xFFFF or value.TYPE == GUID)
            can_cont_desc = value.TYPE == UNICODE

            if library_only or value.language is not None:
                self.to_metadata_library.append((name, value))
            elif value.stream is not None:
                if name not in self.to_metadata:
                    self.to_metadata[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            elif name in ContentDescriptionObject.NAMES:
                if name not in self.to_content_description and can_cont_desc:
                    self.to_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            else:
                if name not in self.to_extended_content_description:
                    self.to_extended_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))

        # Add missing objects
        if not self.content_description_obj:
            self.content_description_obj = \
                ContentDescriptionObject()
            self.objects.append(self.content_description_obj)
        if not self.extended_content_description_obj:
            self.extended_content_description_obj = \
                ExtendedContentDescriptionObject()
            self.objects.append(self.extended_content_description_obj)
        if not self.header_extension_obj:
            self.header_extension_obj = \
                HeaderExtensionObject()
            self.objects.append(self.header_extension_obj)
        if not self.metadata_obj:
            self.metadata_obj = \
                MetadataObject()
            self.header_extension_obj.objects.append(self.metadata_obj)
        if not self.metadata_library_obj:
            self.metadata_library_obj = \
                MetadataLibraryObject()
            self.header_extension_obj.objects.append(self.metadata_library_obj)

        # Render the header
        data = b"".join([obj.render(self) for obj in self.objects])
        data = (HeaderObject.GUID +
                struct.pack("<QL", len(data) + 30, len(self.objects)) +
                b"\x01\x02" + data)

        with open(self.filename, "rb+") as fileobj:
            size = len(data)
            resize_bytes(fileobj, self.size, size, 0)
            fileobj.seek(0)
            fileobj.write(data)

        self.size = size
        self.num_objects = len(self.objects)

    def __read_file(self, fileobj):
        header = fileobj.read(30)
        if len(header) != 30 or header[:16] != HeaderObject.GUID:
            raise ASFHeaderError("Not an ASF file.")

        self.extended_content_description_obj = None
        self.content_description_obj = None
        self.header_extension_obj = None
        self.metadata_obj = None
        self.metadata_library_obj = None

        self.size, self.num_objects = struct.unpack("<QL", header[16:28])
        self.objects = []
        self._tags = {}
        for i in xrange(self.num_objects):
            self.__read_object(fileobj)

        for guid in [ContentDescriptionObject.GUID,
                ExtendedContentDescriptionObject.GUID, MetadataObject.GUID,
                MetadataLibraryObject.GUID]:
            self.tags.extend(self._tags.pop(guid, []))
        assert not self._tags

    def __read_object(self, fileobj):
        guid, size = struct.unpack("<16sQ", fileobj.read(24))
        if guid in _object_types:
            obj = _object_types[guid]()
        else:
            obj = UnknownObject(guid)
        data = fileobj.read(size - 24)
        obj.parse(self, data, fileobj, size)
        self.objects.append(obj)

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(HeaderObject.GUID) * 2

Open = ASF
