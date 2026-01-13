# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

import codecs
import struct
from collections.abc import Iterator
from enum import IntEnum, IntFlag
from functools import total_ordering
from re import Pattern
from struct import pack, unpack
from typing import TYPE_CHECKING, Final, Protocol, cast, final, override

from mutagen.id3._frames import ASPI
from mutagen.id3._tags import ID3Header, ID3Tags

if TYPE_CHECKING:
    from mutagen.id3._frames import Frame

from .._util import (
    bchr,
    cdata,
    decode_terminated,
    encode_endian,
    intround,
)
from ._util import BitPaddedInt, ID3SaveConfig, is_valid_frame_id


class PictureType(IntEnum):
    """Enumeration of image types defined by the ID3 standard for the APIC
    frame, but also reused in WMA/FLAC/VorbisComment.
    """

    OTHER = 0
    """Other"""

    FILE_ICON = 1
    """32x32 pixels 'file icon' (PNG only)"""

    OTHER_FILE_ICON = 2
    """Other file icon"""

    COVER_FRONT = 3
    """Cover (front)"""

    COVER_BACK = 4
    """Cover (back)"""

    LEAFLET_PAGE = 5
    """Leaflet page"""

    MEDIA = 6
    """Media (e.g. label side of CD)"""

    LEAD_ARTIST = 7
    """Lead artist/lead performer/soloist"""

    ARTIST = 8
    """Artist/performer"""

    CONDUCTOR = 9
    """Conductor"""

    BAND = 10
    """Band/Orchestra"""

    COMPOSER = 11
    """Composer"""

    LYRICIST = 12
    """Lyricist/text writer"""

    RECORDING_LOCATION = 13
    """Recording Location"""

    DURING_RECORDING = 14
    """During recording"""

    DURING_PERFORMANCE = 15
    """During performance"""

    SCREEN_CAPTURE = 16
    """Movie/video screen capture"""

    FISH = 17
    """A bright coloured fish"""

    ILLUSTRATION = 18
    """Illustration"""

    BAND_LOGOTYPE = 19
    """Band/artist logotype"""

    PUBLISHER_LOGOTYPE = 20
    """Publisher/Studio logotype"""

    def _pprint(self) -> str:
        return str(self).split(".", 1)[-1].lower().replace("_", " ")


class CTOCFlags(IntFlag):

    TOP_LEVEL = 0x2
    """Identifies the CTOC root frame"""

    ORDERED = 0x1
    """Child elements are ordered"""


class SpecError(Exception):
    pass


class Spec[T](Protocol):

    handle_nodata: bool = False
    """If reading empty data is possible and writing it back will again
    result in no data.
    """
    name: str
    default: T

    def __init__(self, name: str, default: T):
        self.name = name
        self.default = default

    @override
    def __hash__(self) -> int:
        raise TypeError("Spec objects are unhashable")

    def _validate23(self, frame: Frame, value, **kwargs):
        """Return a possibly modified value which, if written,
        results in valid id3v2.3 data.
        """

        return value

    def read(self, header: ID3Header, frame: Frame, data: bytes) -> tuple[object, bytes]:
        """
        Returns:
            (value: object, left_data: bytes)
        Raises:
            SpecError
        """

        raise NotImplementedError

    def write(self, config: ID3SaveConfig, frame: Frame, value) -> bytes:
        """
        Returns:
            bytes: The serialized data
        Raises:
            SpecError
        """
        raise NotImplementedError

    def validate(self, frame: Frame, value) -> object:
        """
        Returns:
            the validated value
        Raises:
            ValueError
            TypeError
        """

        raise NotImplementedError


class ByteSpec(Spec[int]):

    def __init__(self, name: str, default: int=0):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes) -> tuple[int, bytes]:
        return bytearray(data)[0], data[1:]

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: int) -> bytes:
        return bchr(value)

    @override
    def validate(self, frame: Frame, value: int | None):
        if value is not None:
            _ = bchr(value)
        return value


class PictureTypeSpec(ByteSpec):

    def __init__(self, name: str, default: PictureType=PictureType.COVER_FRONT):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        value, data = ByteSpec.read(self, header, frame, data)
        return PictureType(value), data

    @override
    def validate(self, frame: Frame, value: int | None):
        value = ByteSpec.validate(self, frame, value)
        if value is not None:
            return PictureType(value)
        return value


class CTOCFlagsSpec(ByteSpec):

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        value, data = ByteSpec.read(self, header, frame, data)
        return CTOCFlags(value), data

    @override
    def validate(self, frame: Frame, value: int | None):
        value = ByteSpec.validate(self, frame, value)
        if value is not None:
            return CTOCFlags(value)
        return value


class IntegerSpec(Spec[int]):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        return int(BitPaddedInt(data, bits=8)), b''

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: int):
        return BitPaddedInt.to_str(value, bits=8, width=-1)

    @override
    def validate(self, frame: Frame, value: int | None):
        return value


class SizedIntegerSpec(Spec[int]):

    name: str
    __sz: int
    default: int

    def __init__(self, name: str, size: int, default: int):
        self.name, self.__sz = name, size
        self.default = default

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        return int(BitPaddedInt(data[:self.__sz], bits=8)), data[self.__sz:]

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: int):
        return BitPaddedInt.to_str(value, bits=8, width=self.__sz)

    @override
    def validate(self, frame: Frame, value: int | None):
        return value


class Encoding(IntEnum):
    """Text Encoding"""

    LATIN1 = 0
    """ISO-8859-1"""

    UTF16 = 1
    """UTF-16 with BOM"""

    UTF16BE = 2
    """UTF-16BE without BOM"""

    UTF8 = 3
    """UTF-8"""


class EncodingSpec(ByteSpec):

    def __init__(self, name: str, default: Encoding=Encoding.UTF16):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        enc, data = super().read(header, frame, data)
        if enc not in (Encoding.LATIN1, Encoding.UTF16, Encoding.UTF16BE,
                       Encoding.UTF8):
            raise SpecError(f'Invalid Encoding: {enc!r}')
        return Encoding(enc), data

    @override
    def validate(self, frame: Frame, value: int | None):
        if value is None:
            raise TypeError
        if value not in (Encoding.LATIN1, Encoding.UTF16, Encoding.UTF16BE,
                         Encoding.UTF8):
            raise ValueError(f'Invalid Encoding: {value!r}')
        return Encoding(value)

    @override
    def _validate23(self, frame: Frame, value: Encoding, **kwargs):
        # only 0, 1 are valid in v2.3, default to utf-16
        if value not in (Encoding.LATIN1, Encoding.UTF16):
            value = Encoding.UTF16
        return value


class StringSpec(Spec[str]):
    """A fixed size ASCII only payload."""

    len: int

    def __init__(self, name: str, length: int, default: str | None=None):
        if default is None:
            default = " " * length
        super().__init__(name, default)
        self.len = length

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        chunk = data[:self.len]
        try:
            ascii = chunk.decode("ascii")
        except UnicodeDecodeError:
            raise SpecError("not ascii") from None
        else:
            chunk = ascii

        return chunk, data[self.len:]

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: str):
        return (bytes(value.encode("ascii")) + b'\x00' * self.len)[:self.len]

    @override
    def validate(self, frame: Frame, value: str | None | object):
        if value is None:
            raise TypeError

        if not isinstance(value, str):
            raise TypeError(f"{self.name} has to be str")
        value.encode("ascii")

        if len(value) == self.len:
            return value

        raise ValueError('Invalid StringSpec[%d] data: %r' % (self.len, value))


class RVASpec(Spec[list[int]]):

    _max_values: int

    def __init__(self, name: str, stereo_only: bool, default: list[int] | None=None):
        # two_chan: RVA has only 2 channels, while RVAD has 6 channels
        if default is None:
            default = [0, 0]
        super().__init__(name, default)
        self._max_values = 4 if stereo_only else 12

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        # inc/dec flags
        spec = ByteSpec("flags", 0)
        flags, data = spec.read(header, frame, data)
        if not data:
            raise SpecError("truncated")

        # how many bytes per value
        bits, data = spec.read(header, frame, data)
        if bits == 0:
            # not allowed according to spec
            raise SpecError("bits used has to be > 0")
        bytes_per_value = (bits + 7) // 8

        values: list[BitPaddedInt] = []
        while len(data) >= bytes_per_value and len(values) < self._max_values:
            v = BitPaddedInt(data[:bytes_per_value], bits=8)
            data = data[bytes_per_value:]
            values.append(v)

        if len(values) < 2:
            raise SpecError("First two values not optional")

        # if the respective flag bit is zero, take as decrement
        for bit, index in enumerate([0, 1, 4, 5, 8, 10]):
            if not cdata.test_bit(flags, bit):
                try:
                    values[index] = -values[index]
                except IndexError:
                    break

        return values, data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, values: list[int]):
        if len(values) < 2 or len(values) > self._max_values:
            raise SpecError(
                "at least two volume change values required, max %d" %
                self._max_values)

        spec = ByteSpec("flags", 0)

        flags = 0
        values = list(values)
        for bit, index in enumerate([0, 1, 4, 5, 8, 10]):
            try:
                if values[index] < 0:
                    values[index] = -values[index]
                else:
                    flags |= (1 << bit)
            except IndexError:
                break

        buffer_ = bytearray()
        buffer_.extend(spec.write(config, frame, flags))

        # serialized and make them all the same size (min 2 bytes)
        byte_values = [
            BitPaddedInt.to_str(v, bits=8, width=-1, minwidth=2)
            for v in values]
        max_bytes = max([len(v) for v in byte_values])
        byte_values = [v.ljust(max_bytes, b"\x00") for v in byte_values]

        bits = max_bytes * 8
        buffer_.extend(spec.write(config, frame, bits))

        for v in byte_values:
            buffer_.extend(v)

        return bytes(buffer_)

    @override
    def validate(self, frame: Frame, values: list[int] | object | None):
        if len(values) < 2 or len(values) > self._max_values:
            raise ValueError("needs list of length 2..%d" % self._max_values)
        return values


class FrameIDSpec(StringSpec):

    def __init__(self, name: str, length: int):
        super().__init__(name, length, "X" * length)

    @override
    def validate(self, frame: Frame, value: str | object | None):
        value = super().validate(frame, value)
        if not is_valid_frame_id(value):
            raise ValueError("Invalid frame ID")
        return value


class BinaryDataSpec(Spec[bytes]):

    handle_nodata: bool = True

    def __init__(self, name: str, default: bytes=b""):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        return data, b''

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: bytes | object):
        if isinstance(value, bytes):
            return value
        value = str(value).encode("ascii")
        return value

    @override
    def validate(self, frame: Frame, value: bytes | object | None) -> bytes:
        if value is None:
            raise TypeError
        if isinstance(value, bytes):
            return value
        else:
            raise TypeError(f"{self.name} has to be bytes")


def iter_text_fixups(data: bytes, encoding: Encoding) -> Iterator[bytes]:
    """Yields a series of repaired text values for decoding"""

    yield data
    if encoding == Encoding.UTF16BE:
        # wrong termination
        yield data + b"\x00"
    elif encoding == Encoding.UTF16:
        # wrong termination
        yield data + b"\x00"
        # utf-16 is missing BOM, content is usually utf-16-le
        yield codecs.BOM_UTF16_LE + data
        # both cases combined
        yield codecs.BOM_UTF16_LE + data + b"\x00"


class EncodedTextSpec(Spec[str]):

    _encodings: Final = {
        Encoding.LATIN1: ('latin1', b'\x00'),
        Encoding.UTF16: ('utf16', b'\x00\x00'),
        Encoding.UTF16BE: ('utf_16_be', b'\x00\x00'),
        Encoding.UTF8: ('utf8', b'\x00'),
    }

    def __init__(self, name: str, default: str=""):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        enc, term = self._encodings[frame.encoding]
        err = None
        for data in iter_text_fixups(data, frame.encoding):
            try:
                value, data = decode_terminated(data, enc, strict=False)
            except ValueError as e:
                err = e
            else:
                # Older id3 did not support multiple values, but we still
                # read them. To not missinterpret zero padded values with
                # a list of empty strings, stop if everything left is zero.
                # https://github.com/quodlibet/mutagen/issues/276
                if header.version < header._V24 and not data.strip(b"\x00"):
                    data = b""
                return value, data
        raise SpecError(err)

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: str):
        enc, term = self._encodings[frame.encoding]
        try:
            return encode_endian(value, enc, le=True) + term
        except UnicodeEncodeError as e:
            raise SpecError(e) from e

    @override
    def validate(self, frame: Frame, value: str | object | None):
        return str(value)


class MultiSpec(Spec):
    def __init__(self, name: str, *specs: Spec, **kw: str):
        super().__init__(name, default=kw.get('default'))
        self.specs: tuple[Spec, ...] = specs
        self.sep: str | None = kw.get('sep')

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        values: list[object] = []
        while data:
            record: list[object] = []
            for spec in self.specs:
                value, data = spec.read(header, frame, data)
                record.append(value)
            if len(self.specs) != 1:
                values.append(record)
            else:
                values.append(record[0])
        return values, data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: str | list):
        data: list[bytes] = []
        if len(self.specs) == 1:
            for v in value:
                data.append(self.specs[0].write(config, frame, v))
        else:
            for record in value:
                for v, s in zip(record, self.specs, strict=False):
                    data.append(s.write(config, frame, v))
        return b''.join(data)

    @override
    def validate(self, frame: Frame, value: str | list):
        if self.sep and isinstance(value, str):
            value = value.split(self.sep)
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [
                    [s.validate(frame, v) for (v, s) in zip(val, self.specs, strict=False)]
                    for val in value]
        raise ValueError(f'Invalid MultiSpec data: {value!r}')

    @override
    def _validate23(self, frame: Frame, value, **kwargs):
        if len(self.specs) != 1:
            return [[s._validate23(frame, v, **kwargs)
                     for (v, s) in zip(val, self.specs, strict=False)]
                    for val in value]

        spec = self.specs[0]

        # Merge single text spec multispecs only.
        # (TimeStampSpec being the exception, but it's not a valid v2.3 frame)
        if not isinstance(spec, EncodedTextSpec) or \
                isinstance(spec, TimeStampSpec):
            return value

        value = [spec._validate23(frame, v, **kwargs) for v in value]
        if kwargs.get("sep") is not None:
            return [spec.validate(frame, kwargs["sep"].join(value))]
        return value


class EncodedNumericTextSpec(EncodedTextSpec):
    pass


class EncodedNumericPartTextSpec(EncodedTextSpec):
    pass


class Latin1TextSpec(Spec[str]):

    def __init__(self, name: str, default: str=""):
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes) -> tuple[str, bytes]:
        if b'\x00' in data:
            data, ret = data.split(b'\x00', 1)
        else:
            ret = b''
        return data.decode('latin1'), ret

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: str) -> bytes:
        return value.encode('latin1') + b'\x00'

    @override
    def validate(self, frame: Frame, value: str | object | None) -> str:
        return str(value)

@final
class ID3FramesSpec(Spec[list[Frame]]):

    handle_nodata = True

    def __init__(self, name: str, default: list[Frame] | None=None):
        default = default or []
        super().__init__(name, default)

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        from ._tags import ID3Tags

        tags = ID3Tags()
        return tags, tags._read(header, data)

    @override
    def _validate23(self, frame: Frame, value: ID3Tags, **kwargs):
        v = ID3Tags()
        for frame in value.values():
            v.add(frame._get_v23_frame(**kwargs))
        return v

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: ID3Tags):
        return bytes(value._write(config))

    @override
    def validate(self, frame: Frame, value: ID3Tags | object | None):
        if isinstance(value, ID3Tags):
            return value

        tags = ID3Tags()
        for v in value:
            tags.add(v)

        return tags

@final
class Latin1TextListSpec(Spec[list[str]]):

    def __init__(self, name: str, default: list[str] | None=None):
        if default is None:
            default = []
        super().__init__(name, default)
        self._bspec = ByteSpec("entry_count", default=0)
        self._lspec = Latin1TextSpec("child_element_id")

    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        count, data = self._bspec.read(header, frame, data)
        entries: list[str] = []
        for _i in range(count):
            entry, data = self._lspec.read(header, frame, data)
            entries.append(entry)
        return entries, data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: list[str]):
        b = self._bspec.write(config, frame, len(value))
        for v in value:
            b += self._lspec.write(config, frame, v)
        return b

    @override
    def validate(self, frame: Frame, value: list[str]):
        return [self._lspec.validate(frame, v) for v in value]

@final
@total_ordering
class ID3TimeStamp:
    """A time stamp in ID3v2 format.

    This is a restricted form of the ISO 8601 standard; time stamps
    take the form of:
        YYYY-MM-DD HH:MM:SS
    Or some partial form (YYYY-MM-DD HH, YYYY, etc.).

    The 'text' attribute contains the raw text data of the time stamp.
    """

    import re

    year: int | None
    month: int | None
    day: int | None
    hour: int | None
    minute: int | None
    second: int | None

    def __init__(self, text: str | ID3TimeStamp | object) -> None:
        if isinstance(text, ID3TimeStamp):
            text = text.text
        elif not isinstance(text, str):
            raise TypeError("not a str")

        self.text = text

    __formats = ['%04d'] + ['%02d'] * 5
    __seps = ['-', '-', ' ', ':', ':', 'x']

    def get_text(self) -> str:
        parts = [self.year, self.month, self.day,
                 self.hour, self.minute, self.second]
        pieces: list[str] = []
        for i, part in enumerate(parts):
            if part is None:
                break
            pieces.append(self.__formats[i] % part + self.__seps[i])
        return ''.join(pieces)[:-1]

    def set_text(self, text: str, splitre: Pattern[str] = re.compile('[-T:/.]|\\s+')):
        year, month, day, hour, minute, second = \
            splitre.split(text + ':::::')[:6]
        for a in ['year', 'month', 'day', 'hour', 'minute', 'second']:
            try:
                v = int(locals()[a])
            except ValueError:
                v = None
            setattr(self, a, v)

    @property
    def text(self) -> str:
        """ID3v2.4 date and time."""
        return self.get_text()
    @text.setter
    def text(self, value: str) -> None:
        self.set_text(value)

    @override
    def __str__(self) -> str:
        return self.text

    def __bytes__(self):
        return self.text.encode("utf-8")

    @override
    def __repr__(self):
        return repr(self.text)

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, ID3TimeStamp) and self.text == other.text

    def __lt__(self, other: ID3TimeStamp) -> bool:
        return self.text < other.text

    __hash__: Final = object.__hash__

    def encode(self, *args: str) -> bytes:
        return self.text.encode(*args)


class TimeStampSpec(EncodedTextSpec):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        value, data = super().read(header, frame, data)
        return self.validate(frame, value), data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, data: ID3TimeStamp):
        return super().write(config, frame,data.text.replace(' ', 'T'))

    @override
    def validate(self, frame: Frame, value: str | ID3TimeStamp | object | None):
        try:
            return ID3TimeStamp(value)
        except TypeError as e:
            raise ValueError(f"Invalid ID3TimeStamp: {value!r}") from e

@final
class ChannelSpec(ByteSpec):
    OTHER = 0
    MASTER = 1
    FRONTRIGHT = 2
    FRONTLEFT = 3
    BACKRIGHT = 4
    BACKLEFT = 5
    FRONTCENTRE = 6
    BACKCENTRE = 7
    SUBWOOFER = 8


class VolumeAdjustmentSpec(Spec[float]):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        value, = cast(tuple[int], unpack('>h', data[0:2]))
        return value / 512.0, data[2:]

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: float):
        number = intround(value * 512)
        # pack only fails in 2.7, do it manually in 2.6
        if not -32768 <= number <= 32767:
            raise SpecError("not in range")
        return pack('>h', number)

    @override
    def validate(self, frame: Frame, value: float | None):
        if value is not None:
            try:
                self.write(None, frame, value)
            except SpecError as e:
                raise ValueError("out of range") from e
        return value


class VolumePeakSpec(Spec[float]):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        # http://bugs.xmms.org/attachment.cgi?id=113&action=view
        peak = 0
        data_array = bytearray(data)
        bits = data_array[0]
        vol_bytes = min(4, (bits + 7) >> 3)
        # not enough frame data
        if vol_bytes + 1 > len(data):
            raise SpecError("not enough frame data")
        shift = ((8 - (bits & 7)) & 7) + (4 - vol_bytes) * 8
        for i in range(1, vol_bytes + 1):
            peak *= 256
            peak += data_array[i]
        peak *= 2 ** shift
        return (float(peak) / (2 ** 31 - 1)), data[1 + vol_bytes:]

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: float):
        number = intround(value * 32768)
        # pack only fails in 2.7, do it manually in 2.6
        if not 0 <= number <= 65535:
            raise SpecError("not in range")
        # always write as 16 bits for sanity.
        return b"\x10" + pack('>H', number)

    @override
    def validate(self, frame: Frame, value: float | None):
        if value is not None:
            try:
                self.write(None, frame, value)
            except SpecError as e:
                raise ValueError("out of range") from e
        return value


class SynchronizedTextSpec(EncodedTextSpec):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        texts: list[tuple[str, int]] = []
        encoding, term = self._encodings[frame.encoding]
        while data:
            try:
                value, data = decode_terminated(data, encoding)
            except ValueError as e:
                raise SpecError("decoding error") from e

            if len(data) < 4:
                raise SpecError("not enough data")
            time, = cast(tuple[int], struct.unpack(">I", data[:4]))

            texts.append((value, time))
            data = data[4:]
        return texts, b""

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: list[tuple[str, int]]):
        data: list[bytes] = []
        encoding, term = self._encodings[frame.encoding]
        for text, time in value:
            try:
                textb = encode_endian(text, encoding, le=True) + term
            except UnicodeEncodeError as e:
                raise SpecError(e) from e
            data.append(textb + struct.pack(">I", time))
        return b"".join(data)

    @override
    def validate(self, frame: Frame, value: list[tuple[str, int]]):
        return value


class KeyEventSpec(Spec[list[tuple[int, int]]]):
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        events: list[tuple[int, int]] = []
        while len(data) >= 5:
            events.append(struct.unpack(">bI", data[:5]))
            data = data[5:]
        return events, data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: list[tuple[int, int]]):
        return b"".join(struct.pack(">bI", *event) for event in value)

    @override
    def validate(self, frame: Frame, value: list[tuple[int, int]]):
        return list(value)


class VolumeAdjustmentsSpec(Spec[list[tuple[float, float]]]):
    # Not to be confused with VolumeAdjustmentSpec.
    @override
    def read(self, header: ID3Header, frame: Frame, data: bytes):
        adjustments: dict[float, float] = {}
        while len(data) >= 4:
            freq, adj = cast(tuple[int,int], struct.unpack(">Hh", data[:4]))
            data = data[4:]
            adjustments[freq / 2.0] = adj / 512.0
        return sorted(adjustments.items()), data

    @override
    def write(self, config: ID3SaveConfig, frame: Frame, value: list[tuple[float, float]]):
        value.sort()
        return b"".join(struct.pack(">Hh", int(freq * 2), int(adj * 512))
                        for (freq, adj) in value)

    @override
    def validate(self, frame: Frame, value: list[tuple[float, float]]):
        return list(value)


class ASPIIndexSpec(Spec[list[int]]):

    @override
    def read(self, header: ID3Header, frame: ASPI, data: bytes):
        if frame.b == 16:
            format = "H"
            size = 2
        elif frame.b == 8:
            format = "B"
            size = 1
        else:
            raise SpecError("invalid bit count in ASPI (%d)" % frame.b)

        indexes = data[:frame.N * size]
        data = data[frame.N * size:]
        try:
            return list(struct.unpack(">" + format * frame.N, indexes)), data
        except struct.error as e:
            raise SpecError(e) from e

    @override
    def write(self, config: ID3SaveConfig, frame: ASPI, values: list[int]):
        if frame.b == 16:
            format = "H"
        elif frame.b == 8:
            format = "B"
        else:
            raise SpecError("frame.b must be 8 or 16")
        try:
            return struct.pack(">" + format * frame.N, *values)
        except struct.error as e:
            raise SpecError(e) from e

    @override
    def validate(self, frame: Frame, values: list[int]):
        return list(values)
