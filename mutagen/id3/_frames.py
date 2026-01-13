# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

import zlib
from collections.abc import Sequence
from struct import unpack
from typing import TYPE_CHECKING, Any, Final, Self, override

if TYPE_CHECKING:
    from ._tags import ID3Header

from ._specs import (
    ASPIIndexSpec,
    BinaryDataSpec,
    ByteSpec,
    ChannelSpec,
    CTOCFlagsSpec,
    EncodedNumericPartTextSpec,
    EncodedNumericTextSpec,
    EncodedTextSpec,
    Encoding,
    EncodingSpec,
    FrameIDSpec,
    ID3FramesSpec,
    ID3TimeStamp,
    IntegerSpec,
    KeyEventSpec,
    Latin1TextListSpec,
    Latin1TextSpec,
    MultiSpec,
    PictureType,
    PictureTypeSpec,
    RVASpec,
    SizedIntegerSpec,
    Spec,
    SpecError,
    StringSpec,
    SynchronizedTextSpec,
    TimeStampSpec,
    VolumeAdjustmentSpec,
    VolumeAdjustmentsSpec,
    VolumePeakSpec,
)
from ._util import (
    ID3EncryptionUnsupportedError,
    ID3JunkFrameError,
    ID3SaveConfig,
    error,
    unsynch,
)


def _bytes2key(b: bytes) -> str:
    assert isinstance(b, bytes)

    return b.decode("latin1")


class Frame:
    """Fundamental unit of ID3 data.

    ID3 tags are split into frames. Each frame has a potentially
    different structure, and so this base class is not very featureful.
    """

    FLAG23_ALTERTAG: int = 0x8000
    FLAG23_ALTERFILE: int = 0x4000
    FLAG23_READONLY: int = 0x2000
    FLAG23_COMPRESS: int = 0x0080
    FLAG23_ENCRYPT: int = 0x0040
    FLAG23_GROUP: int = 0x0020

    FLAG24_ALTERTAG: int = 0x4000
    FLAG24_ALTERFILE: int = 0x2000
    FLAG24_READONLY: int = 0x1000
    FLAG24_GROUPID: int = 0x0040
    FLAG24_COMPRESS: int = 0x0008
    FLAG24_ENCRYPT: int = 0x0004
    FLAG24_UNSYNCH: int = 0x0002
    FLAG24_DATALEN: int = 0x0001

    _framespec: Sequence[Spec[Any]] = []
    _optionalspec: Sequence[Spec[Any]] = []

    def __init__(self, *args: Frame, **kwargs: object):
        if len(args) == 1 and len(kwargs) == 0 and \
                isinstance(args[0], type(self)):
            other = args[0]
            # ask the sub class to fill in our data
            other._to_other(self)
        else:
            for checker, val in zip(self._framespec, args, strict=False):
                setattr(self, checker.name, val)
            for checker in self._framespec[len(args):]:
                setattr(self, checker.name,
                        kwargs.get(checker.name, checker.default))
            for spec in self._optionalspec:
                if spec.name in kwargs:
                    setattr(self, spec.name, kwargs[spec.name])
                else:
                    break

    @override
    def __setattr__(self, name: str, value):
        for checker in self._framespec:
            if checker.name == name:
                self._setattr(name, checker.validate(self, value))
                return
        for checker in self._optionalspec:
            if checker.name == name:
                self._setattr(name, checker.validate(self, value))
                return
        super().__setattr__(name, value)

    def _setattr(self, name: str, value):
        self.__dict__[name] = value

    def _to_other(self, other: Frame) -> None:
        # this impl covers subclasses with the same framespec
        if other._framespec is not self._framespec:
            raise ValueError

        for checker in other._framespec:
            other._setattr(checker.name, getattr(self, checker.name))

        # this impl covers subclasses with the same optionalspec
        if other._optionalspec is not self._optionalspec:
            raise ValueError

        for checker in other._optionalspec:
            if hasattr(self, checker.name):
                other._setattr(checker.name, getattr(self, checker.name))

    def _merge_frame(self, other: Self) -> Self:
        # default impl, use the new tag over the old one
        return other

    def _upgrade_frame(self) -> Frame | None:
        """Returns either this instance or a new instance if this is a v2.2
        frame and an upgrade to a v2.3/4 equivalent is viable.

        If this is a v2.2 instance and there is no upgrade path, returns None.
        """

        # turn 2.2 into 2.3/2.4 tags
        if len(type(self).__name__) == 3:
            base = type(self).__base__
            if base is Frame:
                return None
            assert base is not None and issubclass(base, Frame)
            return base(self)
        else:
            return self

    def _get_v23_frame(self, **kwargs):
        """Returns a frame copy which is suitable for writing into a v2.3 tag.

        kwargs get passed to the specs.
        """

        new_kwargs = {}
        for checker in self._framespec:
            name = checker.name
            value = getattr(self, name)
            new_kwargs[name] = checker._validate23(self, value, **kwargs)

        for checker in self._optionalspec:
            name = checker.name
            if hasattr(self, name):
                value = getattr(self, name)
                new_kwargs[name] = checker._validate23(self, value, **kwargs)

        return type(self)(**new_kwargs)

    @property
    def HashKey(self) -> str:
        """An internal key used to ensure frame uniqueness in a tag"""

        return self.FrameID

    @property
    def FrameID(self) -> str:
        """ID3v2 three or four character frame ID"""

        return type(self).__name__

    @override
    def __repr__(self) -> str:
        """Python representation of a frame.

        The string returned is a valid Python expression to construct
        a copy of this frame.
        """
        kw: list[str] = []
        for attr in self._framespec:
            # so repr works during __init__
            if hasattr(self, attr.name):
                kw.append(f'{attr.name}={getattr(self, attr.name)!r}')
        for attr in self._optionalspec:
            if hasattr(self, attr.name):
                kw.append(f'{attr.name}={getattr(self, attr.name)!r}')
        return '{}({})'.format(type(self).__name__, ', '.join(kw))

    def _readData(self, id3: ID3Header, data: bytes) -> bytes:
        """Raises ID3JunkFrameError; Returns leftover data"""

        for reader in self._framespec:
            if len(data) or reader.handle_nodata:
                try:
                    value, data = reader.read(id3, self, data)
                except SpecError as e:
                    raise ID3JunkFrameError(e) from e
            else:
                raise ID3JunkFrameError("no data left")
            self._setattr(reader.name, value)

        for reader in self._optionalspec:
            if len(data) or reader.handle_nodata:
                try:
                    value, data = reader.read(id3, self, data)
                except SpecError as e:
                    raise ID3JunkFrameError(e) from e
            else:
                break
            self._setattr(reader.name, value)

        return data

    def _writeData(self, config: ID3SaveConfig | None = None) -> bytes:
        """Raises error"""

        if config is None:
            config = ID3SaveConfig()

        if config.v2_version == 3:
            frame = self._get_v23_frame(sep=config.v23_separator)
        else:
            frame = self

        data: list[bytes] = []
        for writer in self._framespec:
            try:
                data.append(
                    writer.write(config, frame, getattr(frame, writer.name)))
            except SpecError as e:
                raise error(e) from e

        for writer in self._optionalspec:
            try:
                data.append(
                    writer.write(config, frame, getattr(frame, writer.name)))
            except AttributeError:
                break
            except SpecError as e:
                raise error(e) from e

        return b''.join(data)

    def pprint(self) -> str:
        """Return a human-readable representation of the frame."""
        return f"{type(self).__name__}={self._pprint()}"

    def _pprint(self) -> str:
        return "[unrepresentable data]"

    @classmethod
    def _fromData(cls, header: ID3Header, tflags: int, data: bytes):
        """Construct this ID3 frame from raw string data.

        Raises:

        ID3JunkFrameError in case parsing failed
        NotImplementedError in case parsing isn't implemented
        ID3EncryptionUnsupportedError in case the frame is encrypted.
        """

        if header.version >= header._V24:
            if tflags & (Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN):
                # The data length int is syncsafe in 2.4 (but not 2.3).
                # However, we don't actually need the data length int,
                # except to work around a QL 0.12 bug, and in that case
                # all we need are the raw bytes.
                datalen_bytes = data[:4]
                data = data[4:]
            if tflags & Frame.FLAG24_UNSYNCH or header.f_unsynch:
                try:
                    data = unsynch.decode(data)
                except ValueError:
                    # Some things write synch-unsafe data with either the frame
                    # or global unsynch flag set. Try to load them as is.
                    # https://github.com/quodlibet/mutagen/issues/210
                    # https://github.com/quodlibet/mutagen/issues/223
                    pass
            if tflags & Frame.FLAG24_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG24_COMPRESS:
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    # the initial mutagen that went out with QL 0.12 did not
                    # write the 4 bytes of uncompressed size. Compensate.
                    data = datalen_bytes + data
                    try:
                        data = zlib.decompress(data)
                    except zlib.error as err:
                        raise ID3JunkFrameError(f'zlib: {err}: {data!r}') from err

        elif header.version >= header._V23:
            if tflags & Frame.FLAG23_COMPRESS:
                if len(data) < 4:
                    raise ID3JunkFrameError(f'frame too small: {data!r}')
                usize, = unpack('>L', data[:4])
                data = data[4:]
            if tflags & Frame.FLAG23_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG23_COMPRESS:
                try:
                    data = zlib.decompress(data)
                except zlib.error as err:
                    raise ID3JunkFrameError(f'zlib: {err}: {data!r}') from err

        frame = cls()
        frame._readData(header, data)
        return frame

    @override
    def __hash__(self: object):
        raise TypeError("Frame objects are unhashable")


class CHAP(Frame):
    """Chapter"""

    element_id: str
    start_time: int = 0
    end_time: int = 0
    start_offset: int = 0xffffffff
    end_offset: int = 0xffffffff
    sub_frames: dict[str, Frame]

    _framespec = [
        Latin1TextSpec("element_id"),
        SizedIntegerSpec("start_time", 4, default=0),
        SizedIntegerSpec("end_time", 4, default=0),
        SizedIntegerSpec("start_offset", 4, default=0xffffffff),
        SizedIntegerSpec("end_offset", 4, default=0xffffffff),
        ID3FramesSpec("sub_frames"),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.element_id}'

    @override
    def __eq__(self, other: CHAP | object):
        if not isinstance(other, CHAP):
            return False

        self_frames = self.sub_frames or {}
        other_frames = other.sub_frames or {}
        if sorted(self_frames.values()) != sorted(other_frames.values()):
            return False

        return self.element_id == other.element_id and \
            self.start_time == other.start_time and \
            self.end_time == other.end_time and \
            self.start_offset == other.start_offset and \
            self.end_offset == other.end_offset

    __hash__: Final = Frame.__hash__

    @override
    def _pprint(self):
        frame_pprint = ""
        for frame in self.sub_frames.values():
            for line in frame.pprint().splitlines():
                frame_pprint += "\n" + " " * 4 + line
        return "%s time=%d..%d offset=%d..%d%s" % (
            self.element_id, self.start_time, self.end_time,
            self.start_offset, self.end_offset, frame_pprint)


class CTOC(Frame):
    """Table of contents"""

    element_id: str
    flags: int = 0
    child_element_ids: list[str]
    sub_frames: dict[str, Frame]

    _framespec = [
        Latin1TextSpec("element_id"),
        CTOCFlagsSpec("flags", default=0),
        Latin1TextListSpec("child_element_ids"),
        ID3FramesSpec("sub_frames"),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.element_id}'

    __hash__: Final = Frame.__hash__

    @override
    def __eq__(self, other: CTOC | object):
        if not isinstance(other, CTOC):
            return False

        self_frames = self.sub_frames or {}
        other_frames = other.sub_frames or {}
        if sorted(self_frames.values()) != sorted(other_frames.values()):
            return False

        return self.element_id == other.element_id and \
            self.flags == other.flags and \
            self.child_element_ids == other.child_element_ids

    @override
    def _pprint(self):
        frame_pprint = ""
        if getattr(self, "sub_frames", None):
            frame_pprint += "\n" + "\n".join(
                [" " * 4 + f.pprint() for f in self.sub_frames.values()])
        return "%s flags=%d child_element_ids=%s%s" % (
            self.element_id, int(self.flags),
            ",".join(self.child_element_ids), frame_pprint)


class TextFrame(Frame):
    """Text strings.

    Text frames support casts to unicode or str objects, as well as
    list-like indexing, extend, and append.

    Iterating over a TextFrame iterates over its strings, not its
    characters.

    Text frames have a 'text' attribute which is the list of strings,
    and an 'encoding' attribute; 0 for ISO-8859 1, 1 UTF-16, 2 for
    UTF-16BE, and 3 for UTF-8. If you don't want to worry about
    encodings, just set it to 3.
    """

    encoding: int = Encoding.UTF16
    text: list[str] = []

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        MultiSpec('text', EncodedTextSpec('text'), sep='\u0000', default=[]),
    ]

    def __bytes__(self):
        return str(self).encode('utf-8')

    @override
    def __str__(self):
        return '\u0000'.join(self.text)

    @override
    def __eq__(self, other: bytes | str | object):
        if isinstance(other, bytes):
            return bytes(self) == other
        elif isinstance(other, str):
            return str(self) == other
        return self.text == other

    __hash__: Final = Frame.__hash__

    def __getitem__(self, item: int):
        return self.text[item]

    def __iter__(self):
        return iter(self.text)

    def append(self, value: str):
        """Append a string."""

        return self.text.append(value)

    def extend(self, value: Sequence[str]):
        """Extend the list by appending all strings from the given list."""

        return self.text.extend(value)

    @override
    def _merge_frame(self, other: TextFrame) -> TextFrame:
        # merge in new values
        for val in other[:]:
            if val not in self:
                self.append(val)
                self.encoding = max(self.encoding, other.encoding)
        return self

    @override
    def _pprint(self):
        return " / ".join(self.text)


class NumericTextFrame(TextFrame):
    """Numerical text strings.

    The numeric value of these frames can be gotten with unary plus, e.g.::

        frame = TLEN('12345')
        length = +frame
    """

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        MultiSpec('text', EncodedNumericTextSpec('text'), sep='\u0000',
                  default=[]),
    ]

    def __pos__(self):
        """Return the numerical value of the string."""
        return int(self.text[0])


class NumericPartTextFrame(TextFrame):
    """Multivalue numerical text strings.

    These strings indicate 'part (e.g. track) X of Y', and unary plus
    returns the first value::

        frame = TRCK('4/15')
        track = +frame # track == 4
    """

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        MultiSpec('text', EncodedNumericPartTextSpec('text'), sep='\u0000',
                  default=[]),
    ]

    def __pos__(self):
        return int(self.text[0].split("/")[0])


class TimeStampTextFrame(TextFrame):
    """A list of time stamps.

    The 'text' attribute in this frame is a list of ID3TimeStamp
    objects, not a list of strings.
    """

    text: list[ID3TimeStamp] = []

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        MultiSpec('text', TimeStampSpec('stamp'), sep=',', default=[]),
    ]

    @override
    def __bytes__(self):
        return str(self).encode('utf-8')

    @override
    def __str__(self):
        return ','.join([stamp.text for stamp in self.text])

    @override
    def _pprint(self):
        return " / ".join([stamp.text for stamp in self.text])


class UrlFrame(Frame):
    """A frame containing a URL string.

    The ID3 specification is silent about IRIs and normalized URL
    forms. Mutagen assumes all URLs in files are encoded as Latin 1,
    but string conversion of this frame returns a UTF-8 representation
    for compatibility with other string conversions.

    The only sane way to handle URLs in MP3s is to restrict them to
    ASCII.
    """

    _framespec = [
        Latin1TextSpec('url'),
    ]
    url: str

    def __bytes__(self):
        return self.url.encode('utf-8')

    @override
    def __str__(self):
        return self.url

    @override
    def __eq__(self, other: object):
        return self.url == other

    __hash__: Final = Frame.__hash__


    @override
    def _pprint(self)-> str:
        return self.url


class UrlFrameU(UrlFrame):

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.url}'


class TALB(TextFrame):
    "Album"


class TBPM(NumericTextFrame):
    "Beats per minute"


class TCOM(TextFrame):
    "Composer"


class TCON(TextFrame):
    """Content type (Genre)

    ID3 has several ways genres can be represented; for convenience,
    use the 'genres' property rather than the 'text' attribute.
    """

    from mutagen._constants import GENRES
    GENRES = GENRES

    text: list[str]

    def __get_genres(self) -> list[str]:
        genres: list[str] = []
        import re
        genre_re = re.compile(r"((?:\((?P<id>[0-9]+|RX|CR)\))*)(?P<str>.+)?")
        for value in self.text:
            # 255 possible entries in id3v1
            if value.isdecimal() and int(value) < 256:
                try:
                    genres.append(self.GENRES[int(value)])
                except IndexError:
                    genres.append("Unknown")
            elif value == "CR":
                genres.append("Cover")
            elif value == "RX":
                genres.append("Remix")
            elif value:
                newgenres: list[str] = []
                genreid, dummy, genrename = genre_re.match(value).groups()

                if genreid:
                    for gid in genreid[1:-1].split(")("):
                        if gid.isdigit() and int(gid) < len(self.GENRES):
                            gid = str(self.GENRES[int(gid)])
                            newgenres.append(gid)
                        elif gid == "CR":
                            newgenres.append("Cover")
                        elif gid == "RX":
                            newgenres.append("Remix")
                        else:
                            newgenres.append("Unknown")

                if genrename:
                    # "Unescaping" the first parenthesis
                    if genrename.startswith("(("):
                        genrename = genrename[1:]
                    if genrename not in newgenres:
                        newgenres.append(genrename)

                genres.extend(newgenres)

        return genres

    def __set_genres(self, genres: list[str] | str):
        if isinstance(genres, str):
            genres = [genres]
        self.text = [self.__decode(g) for g in genres]

    def __decode(self, value: str):
        if isinstance(value, bytes):
            enc = EncodedTextSpec._encodings[self.encoding][0]
            return value.decode(enc)
        else:
            return value

    @property
    def genres(self) -> list[str]:
        """A list of genres parsed from the raw text data."""
        return self.__get_genres()

    @genres.setter
    def genres(self, value: list[str] | str):
        self.__set_genres(value)

    @override
    def _pprint(self) -> str:
        return " / ".join(self.genres)


class TCOP(TextFrame):
    "Copyright (c)"


class TCMP(NumericTextFrame):
    "iTunes Compilation Flag"


class TDAT(TextFrame):
    "Date of recording (DDMM)"


class TDEN(TimeStampTextFrame):
    "Encoding Time"


class TDES(TextFrame):
    "iTunes Podcast Description"


class TKWD(TextFrame):
    "iTunes Podcast Keywords"


class TCAT(TextFrame):
    "iTunes Podcast Category"


class MVNM(TextFrame):
    "iTunes Movement Name"


class MVN(MVNM):
    "iTunes Movement Name"


class MVIN(NumericPartTextFrame):
    "iTunes Movement Number/Count"


class MVI(MVIN):
    "iTunes Movement Number/Count"


class GRP1(TextFrame):
    "iTunes Grouping"


class GP1(GRP1):
    "iTunes Grouping"


class TDOR(TimeStampTextFrame):
    "Original Release Time"


class TDLY(NumericTextFrame):
    "Audio Delay (ms)"


class TDRC(TimeStampTextFrame):
    "Recording Time"


class TDRL(TimeStampTextFrame):
    "Release Time"


class TDTG(TimeStampTextFrame):
    "Tagging Time"


class TENC(TextFrame):
    "Encoder"


class TEXT(TextFrame):
    "Lyricist"


class TFLT(TextFrame):
    "File type"


class TGID(TextFrame):
    "iTunes Podcast Identifier"


class TIME(TextFrame):
    "Time of recording (HHMM)"


class TIT1(TextFrame):
    "Content group description"


class TIT2(TextFrame):
    "Title"


class TIT3(TextFrame):
    "Subtitle/Description refinement"


class TKEY(TextFrame):
    "Starting Key"


class TLAN(TextFrame):
    "Audio Languages"


class TLEN(NumericTextFrame):
    "Audio Length (ms)"


class TMED(TextFrame):
    "Source Media Type"


class TMOO(TextFrame):
    "Mood"


class TOAL(TextFrame):
    "Original Album"


class TOFN(TextFrame):
    "Original Filename"


class TOLY(TextFrame):
    "Original Lyricist"


class TOPE(TextFrame):
    "Original Artist/Performer"


class TORY(NumericTextFrame):
    "Original Release Year"


class TOWN(TextFrame):
    "Owner/Licensee"


class TPE1(TextFrame):
    "Lead Artist/Performer/Soloist/Group"


class TPE2(TextFrame):
    "Band/Orchestra/Accompaniment"


class TPE3(TextFrame):
    "Conductor"


class TPE4(TextFrame):
    "Interpreter/Remixer/Modifier"


class TPOS(NumericPartTextFrame):
    "Part of set"


class TPRO(TextFrame):
    "Produced (P)"


class TPUB(TextFrame):
    "Publisher"


class TRCK(NumericPartTextFrame):
    "Track Number"


class TRDA(TextFrame):
    "Recording Dates"


class TRSN(TextFrame):
    "Internet Radio Station Name"


class TRSO(TextFrame):
    "Internet Radio Station Owner"


class TSIZ(NumericTextFrame):
    "Size of audio data (bytes)"


class TSO2(TextFrame):
    "iTunes Album Artist Sort"


class TSOA(TextFrame):
    "Album Sort Order key"


class TSOC(TextFrame):
    "iTunes Composer Sort"


class TSOP(TextFrame):
    "Performer Sort Order key"


class TSOT(TextFrame):
    "Title Sort Order key"


class TSRC(TextFrame):
    "International Standard Recording Code (ISRC)"


class TSSE(TextFrame):
    "Encoder settings"


class TSST(TextFrame):
    "Set Subtitle"


class TYER(NumericTextFrame):
    "Year of recording"


class TXXX(TextFrame):
    """User-defined text data.

    TXXX frames have a 'desc' attribute which is set to any Unicode
    value (though the encoding of the text and the description must be
    the same). Many taggers use this frame to store freeform keys.
    """

    encoding: int
    desc: str
    text: list[str] = []

    _framespec = [
        EncodingSpec('encoding'),
        EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep='\u0000', default=[]),
    ]

    @property
    @override
    def HashKey(self) -> str:
        return f'{self.FrameID}:{self.desc}'

    @override
    def _pprint(self):
        return "{}={}".format(self.desc, " / ".join(self.text))


class WCOM(UrlFrameU):
    "Commercial Information"


class WCOP(UrlFrame):
    "Copyright Information"


class WFED(UrlFrame):
    "iTunes Podcast Feed"


class WOAF(UrlFrame):
    "Official File Information"


class WOAR(UrlFrameU):
    "Official Artist/Performer Information"


class WOAS(UrlFrame):
    "Official Source Information"


class WORS(UrlFrame):
    "Official Internet Radio Information"


class WPAY(UrlFrame):
    "Payment Information"


class WPUB(UrlFrame):
    "Official Publisher Information"


class WXXX(UrlFrame):
    """User-defined URL data.

    Like TXXX, this has a freeform description associated with it.
    """

    encoding: int = Encoding.UTF16
    desc: str
    url: str

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        EncodedTextSpec('desc'),
        Latin1TextSpec('url'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}'


class PairedTextFrame(Frame):
    """Paired text strings.

    Some ID3 frames pair text strings, to associate names with a more
    specific involvement in the song. The 'people' attribute of these
    frames contains a list of pairs::

        [['trumpet', 'Miles Davis'], ['bass', 'Paul Chambers']]

    Like text frames, these frames also have an encoding attribute.
    """

    encoding: int = Encoding.UTF16
    people: list[list[str]] = []

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        MultiSpec('people',
                  EncodedTextSpec('involvement'),
                  EncodedTextSpec('person'), default=[])
    ]

    @override
    def __eq__(self, other: object):
        return self.people == other

    __hash__: Final = Frame.__hash__


class TIPL(PairedTextFrame):
    "Involved People List"


class TMCL(PairedTextFrame):
    "Musicians Credits List"


class IPLS(TIPL):
    "Involved People List"


class BinaryFrame(Frame):
    """Binary data

    The 'data' attribute contains the raw byte string.
    """

    data: bytes

    _framespec = [
        BinaryDataSpec('data'),
    ]

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class MCDI(BinaryFrame):
    "Binary dump of CD's TOC"


class ETCO(Frame):
    """Event timing codes."""

    format: int = 1
    events: list[tuple[int, int]] = []

    _framespec = [
        ByteSpec("format", default=1),
        KeyEventSpec("events", default=[]),
    ]

    @override
    def __eq__(self, other: object):
        return self.events == other

    __hash__: Final = Frame.__hash__


class MLLT(Frame):
    """MPEG location lookup table.

    This frame's attributes may be changed in the future based on
    feedback from real-world use.
    """

    frames: int = 0
    bytes: int = 0
    milliseconds: int = 0
    bits_for_bytes: int = 0
    bits_for_milliseconds: int = 0
    data: bytes

    _framespec = [
        SizedIntegerSpec('frames', size=2, default=0),
        SizedIntegerSpec('bytes', size=3, default=0),
        SizedIntegerSpec('milliseconds', size=3, default=0),
        ByteSpec('bits_for_bytes', default=0),
        ByteSpec('bits_for_milliseconds', default=0),
        BinaryDataSpec('data'),
    ]

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class SYTC(Frame):
    """Synchronised tempo codes.

    This frame's attributes may be changed in the future based on
    feedback from real-world use.
    """

    format: int = 1
    data: bytes

    _framespec = [
        ByteSpec("format", default=1),
        BinaryDataSpec("data"),
    ]

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class USLT(Frame):
    """Unsynchronised lyrics/text transcription.

    Lyrics have a three letter ISO language code ('lang'), a
    description ('desc'), and a block of plain text ('text').
    """

    encoding: int = Encoding.UTF16
    lang: str = "XXX"
    desc: str
    text: str

    _framespec = [
        EncodingSpec('encoding', default=Encoding.UTF16),
        StringSpec('lang', length=3, default="XXX"),
        EncodedTextSpec('desc'),
        EncodedTextSpec('text'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}:{self.lang}'

    def __bytes__(self):
        return self.text.encode('utf-8')

    @override
    def __str__(self):
        return self.text

    @override
    def __eq__(self, other: object):
        return self.text == other

    __hash__: Final = Frame.__hash__

    @override
    def _pprint(self):
        return f"{self.desc}={self.lang}={self.text}"


class SYLT(Frame):
    """Synchronised lyrics/text."""

    encoding: int
    lang: str = "XXX"
    format: int = 1
    type: int = 0
    desc: str
    text: list[tuple[str, int]]

    _framespec = [
        EncodingSpec('encoding'),
        StringSpec('lang', length=3, default="XXX"),
        ByteSpec('format', default=1),
        ByteSpec('type', default=0),
        EncodedTextSpec('desc'),
        SynchronizedTextSpec('text'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}:{self.lang}'

    @override
    def _pprint(self):
        return str(self)

    @override
    def __eq__(self, other: object):
        return str(self) == other

    __hash__: Final = Frame.__hash__

    @override
    def __str__(self):
        unit = 'fr' if self.format == 1 else 'ms'
        return "\n".join(f"[{time}{unit}]: {text}"
                          for (text, time) in self.text)

    def __bytes__(self):
        return str(self).encode("utf-8")


class COMM(TextFrame):
    """User comment.

    User comment frames have a description, like TXXX, and also a three
    letter ISO language code in the 'lang' attribute.
    """

    encoding: int
    lang: str = "XXX"
    desc: str
    text: list[str] = []

    _framespec = [
        EncodingSpec('encoding'),
        StringSpec('lang', length=3, default="XXX"),
        EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep='\u0000', default=[]),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}:{self.lang}'

    @override
    def _pprint(self):
        return "{}={}={}".format(self.desc, self.lang, " / ".join(self.text))


class RVA2(Frame):
    """Relative volume adjustment (2).

    This frame is used to implemented volume scaling, and in
    particular, normalization using ReplayGain.

    Attributes:

    * desc -- description or context of this adjustment
    * channel -- audio channel to adjust (master is 1)
    * gain -- a + or - dB gain relative to some reference level
    * peak -- peak of the audio as a floating point number, [0, 1]

    When storing ReplayGain tags, use descriptions of 'album' and
    'track' on channel 1.
    """

    desc: str
    channel: int = 1
    gain: float = 1
    peak: float = 1

    _framespec = [
        Latin1TextSpec('desc'),
        ChannelSpec('channel', default=1),
        VolumeAdjustmentSpec('gain', default=1),
        VolumePeakSpec('peak', default=1),
    ]

    _channels: list[str] = ["Other", "Master volume", "Front right", "Front left",
                 "Back right", "Back left", "Front centre", "Back centre",
                 "Subwoofer"]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}'

    @override
    def __eq__(self, other: object):
        try:
            if not isinstance(other, RVA2):
                return False
            return ((str(self) == other) or
                    (self.desc == other.desc and
                     self.channel == other.channel and
                     self.gain == other.gain and
                     self.peak == other.peak))
        except AttributeError:
            return False

    __hash__: Final = Frame.__hash__

    @override
    def __str__(self):
        return f"{self._channels[self.channel]}: {self.gain:+0.4f} dB/{self.peak:0.4f}"


class EQU2(Frame):
    """Equalisation (2).

    Attributes:
    method -- interpolation method (0 = band, 1 = linear)
    desc -- identifying description
    adjustments -- list of (frequency, vol_adjustment) pairs
    """

    method: int = 0
    desc: str
    adjustments: list[tuple[int, float]] = []

    _framespec = [
        ByteSpec("method", default=0),
        Latin1TextSpec("desc"),
        VolumeAdjustmentsSpec("adjustments", default=[]),
    ]

    @override
    def __eq__(self, other: object):
        return self.adjustments == other

    __hash__: Final = Frame.__hash__

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}'


class RVAD(Frame):
    """Relative volume adjustment"""

    adjustments: list[object]

    _framespec = [
        RVASpec("adjustments", stereo_only=False),
    ]

    __hash__: Final = Frame.__hash__

    @override
    def __eq__(self, other: object):
        if not isinstance(other, RVAD):
            return False
        return self.adjustments == other.adjustments


# class EQUA: unsupported


class RVRB(Frame):
    """Reverb."""

    left: int = 0
    right: int = 0
    bounce_left: int = 0
    bounce_right: int = 0
    feedback_ltl: int = 0
    feedback_ltr: int = 0
    feedback_rtr: int = 0
    feedback_rtl: int = 0
    premix_ltr: int = 0
    premix_rtl: int = 0

    _framespec = [
        SizedIntegerSpec('left', size=2, default=0),
        SizedIntegerSpec('right', size=2, default=0),
        ByteSpec('bounce_left', default=0),
        ByteSpec('bounce_right', default=0),
        ByteSpec('feedback_ltl', default=0),
        ByteSpec('feedback_ltr', default=0),
        ByteSpec('feedback_rtr', default=0),
        ByteSpec('feedback_rtl', default=0),
        ByteSpec('premix_ltr', default=0),
        ByteSpec('premix_rtl', default=0),
    ]

    @override
    def __eq__(self, other: object):
        return (self.left, self.right) == other

    __hash__: Final = Frame.__hash__


class APIC(Frame):
    """Attached (or linked) Picture.

    Attributes:

    * encoding -- text encoding for the description
    * mime -- a MIME type (e.g. image/jpeg) or '-->' if the data is a URI
    * type -- the source of the image (3 is the album front cover)
    * desc -- a text description of the image
    * data -- raw image data, as a byte string
    * salt -- will be added to the `HashKey`; this allows for
      multiple `APIC` frames with the same description
    """

    encoding: int
    mime: str
    type: PictureType
    desc: str
    data: bytes
    salt: str = ''

    _framespec = [
        EncodingSpec('encoding'),
        Latin1TextSpec('mime'),
        PictureTypeSpec('type'),
        EncodedTextSpec('desc'),
        BinaryDataSpec('data'),
    ]

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}{self.salt}'

    @override
    def _merge_frame(self, other: APIC) -> APIC:
        other.salt += ' '
        return other

    @override
    def _pprint(self):
        type_desc = str(self.type)
        if hasattr(self.type, "_pprint"):
            type_desc = self.type._pprint()

        return f"{type_desc}, {self.desc} ({self.mime}, {len(self.data)} bytes)"


class PCNT(Frame):
    """Play counter.

    The 'count' attribute contains the (recorded) number of times this
    file has been played.

    This frame is basically obsoleted by POPM.
    """

    count: int = 0

    _framespec = [
        IntegerSpec('count', default=0),
    ]

    @override
    def __eq__(self, other: object):
        return self.count == other

    __hash__: Final = Frame.__hash__

    def __pos__(self):
        return self.count

    @override
    def _pprint(self):
        return str(self.count)


class PCST(Frame):
    """iTunes Podcast Flag"""

    value: int = 0

    _framespec = [
        IntegerSpec('value', default=0),
    ]

    @override
    def __eq__(self, other: object):
        return self.value == other

    __hash__: Final = Frame.__hash__

    def __pos__(self):
        return self.value

    @override
    def _pprint(self):
        return str(self.value)


class POPM(Frame):
    """Popularimeter.

    This frame keys a rating (out of 255) and a play count to an email
    address.

    Attributes:

    * email -- email this POPM frame is for
    * rating -- rating from 0 to 255
    * count -- number of times the files has been played (optional)
    """

    email: str
    rating: int = 0
    count: int | None

    _framespec = [
        Latin1TextSpec('email'),
        ByteSpec('rating', default=0),
    ]

    _optionalspec: Sequence[Spec] = [
        IntegerSpec('count', default=0),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.email}'

    @override
    def __eq__(self, other: object):
        return self.rating == other

    __hash__: Final = Frame.__hash__

    def __pos__(self):
        return self.rating

    @override
    def _pprint(self):
        return "{}={!r} {!r}/255".format(
            self.email, getattr(self, 'count', None), self.rating)


class GEOB(Frame):
    """General Encapsulated Object.

    A blob of binary data, that is not a picture (those go in APIC).

    Attributes:

    * encoding -- encoding of the description
    * mime -- MIME type of the data or '-->' if the data is a URI
    * filename -- suggested filename if extracted
    * desc -- text description of the data
    * data -- raw data, as a byte string
    """

    encoding: int
    mime: str
    filename: str
    desc: str
    data: bytes

    _framespec = [
        EncodingSpec('encoding'),
        Latin1TextSpec('mime'),
        EncodedTextSpec('filename'),
        EncodedTextSpec('desc'),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.desc}'

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class RBUF(Frame):
    """Recommended buffer size.

    Attributes:

    * size -- recommended buffer size in bytes
    * info -- if ID3 tags may be elsewhere in the file (optional)
    * offset -- the location of the next ID3 tag, if any

    Mutagen will not find the next tag itself.
    """

    size: int = 0
    info: int | None
    offset: int | None

    _framespec = [
        SizedIntegerSpec('size', size=3, default=0),
    ]

    _optionalspec: Sequence[Spec] = [
        ByteSpec('info', default=0),
        SizedIntegerSpec('offset', size=4, default=0),
    ]

    @override
    def __eq__(self, other: object):
        return self.size == other

    __hash__: Final = Frame.__hash__

    def __pos__(self):
        return self.size


class AENC(Frame):
    """Audio encryption.

    Attributes:

    * owner -- key identifying this encryption type
    * preview_start -- unencrypted data block offset
    * preview_length -- number of unencrypted blocks
    * data -- data required for decryption (optional)

    Mutagen cannot decrypt files.
    """

    owner: str
    preview_start: int = 0
    preview_length: int = 0
    data: bytes | None

    _framespec = [
        Latin1TextSpec('owner'),
        SizedIntegerSpec('preview_start', size=2, default=0),
        SizedIntegerSpec('preview_length', size=2, default=0),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.owner}'

    def __bytes__(self):
        return self.owner.encode('utf-8')

    def __str__(self):
        return self.owner

    @override
    def __eq__(self, other: object):
        return self.owner == other

    __hash__: Final = Frame.__hash__


class LINK(Frame):
    """Linked information.

    Attributes:

    * frameid -- the ID of the linked frame
    * url -- the location of the linked frame
    * data -- further ID information for the frame
    """

    frameid: str
    url: str
    data: bytes

    _framespec = [
        FrameIDSpec('frameid', length=4),
        Latin1TextSpec('url'),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f"{self.FrameID}:{self.frameid}:{self.url}:{_bytes2key(self.data)}"

    @override
    def __eq__(self, other: object):
        return (self.frameid, self.url, self.data) == other

    __hash__: Final = Frame.__hash__


class POSS(Frame):
    """Position synchronisation frame

    Attribute:

    * format -- format of the position attribute (frames or milliseconds)
    * position -- current position of the file
    """

    format: int = 1
    position: int = 0

    _framespec = [
        ByteSpec('format', default=1),
        IntegerSpec('position', default=0),
    ]

    def __pos__(self):
        return self.position

    @override
    def __eq__(self, other: object):
        return self.position == other

    __hash__: Final = Frame.__hash__


class UFID(Frame):
    """Unique file identifier.

    Attributes:

    * owner -- format/type of identifier
    * data -- identifier
    """

    owner: str
    data: bytes

    _framespec = [
        Latin1TextSpec('owner'),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.owner}'

    @override
    def __eq__(self, o: object):
        if isinstance(o, UFI):
            return self.owner == o.owner and self.data == o.data
        else:
            return self.data == o

    __hash__: Final = Frame.__hash__

    @override
    def _pprint(self):
        return f"{self.owner}={self.data!r}"


class USER(Frame):
    """Terms of use.

    Attributes:

    * encoding -- text encoding
    * lang -- ISO three letter language code
    * text -- licensing terms for the audio
    """

    encoding: int
    lang: str = "XXX"
    text: str

    _framespec = [
        EncodingSpec('encoding'),
        StringSpec('lang', length=3, default="XXX"),
        EncodedTextSpec('text'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.lang}'

    def __bytes__(self):
        return self.text.encode('utf-8')

    @override
    def __str__(self):
        return self.text

    @override
    def __eq__(self, other: object):
        return self.text == other

    __hash__: Final = Frame.__hash__

    @override
    def _pprint(self):
        return f"{self.lang!r}={self.text}"


class OWNE(Frame):
    """Ownership frame."""
    encoding: int
    price: str
    date: str = "19700101"
    seller: str

    _framespec = [
        EncodingSpec('encoding'),
        Latin1TextSpec('price'),
        StringSpec('date', length=8, default="19700101"),
        EncodedTextSpec('seller'),
    ]

    def __bytes__(self):
        return self.seller.encode('utf-8')

    @override
    def __str__(self):
        return self.seller

    @override
    def __eq__(self, other: object):
        return self.seller == other

    __hash__: Final = Frame.__hash__


class COMR(Frame):
    """Commercial frame."""

    encoding: int
    price: str
    valid_until: str = "19700101"
    contact: str
    format: int = 0
    seller: str
    desc: str

    mime: str | None
    logo: bytes | None

    _framespec = [
        EncodingSpec('encoding'),
        Latin1TextSpec('price'),
        StringSpec('valid_until', length=8, default="19700101"),
        Latin1TextSpec('contact'),
        ByteSpec('format', default=0),
        EncodedTextSpec('seller'),
        EncodedTextSpec('desc'),
    ]

    _optionalspec: Sequence[Spec] = [
        Latin1TextSpec('mime'),
        BinaryDataSpec('logo'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{_bytes2key(self._writeData())}'

    @override
    def __eq__(self, other: object) -> bool:
        return self._writeData() == other._writeData()

    __hash__: Final = Frame.__hash__


class ENCR(Frame):
    """Encryption method registration.

    The standard does not allow multiple ENCR frames with the same owner
    or the same method. Mutagen only verifies that the owner is unique.
    """

    owner: str
    method: int = 0x80
    data: bytes

    _framespec = [
        Latin1TextSpec('owner'),
        ByteSpec('method', default=0x80),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f"{self.FrameID}:{self.owner}"

    def __bytes__(self):
        return self.data

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class GRID(Frame):
    """Group identification registration."""

    owner: str
    group: int = 0x80
    data: bytes

    _framespec = [
        Latin1TextSpec('owner'),
        ByteSpec('group', default=0x80),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.group}'

    def __pos__(self):
        return self.group

    def __bytes__(self):
        return self.owner.encode('utf-8')

    @override
    def __str__(self):
        return self.owner

    @override
    def __eq__(self, other: object):
        return self.owner == other or self.group == other

    __hash__: Final = Frame.__hash__


class PRIV(Frame):
    """Private frame."""

    owner: str
    data: bytes

    _framespec = [
        Latin1TextSpec('owner'),
        BinaryDataSpec('data'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.owner}:{_bytes2key(self.data)}'

    def __bytes__(self):
        return self.data

    @override
    def __eq__(self, other: object):
        return self.data == other

    @override
    def _pprint(self):
        return f"{self.owner}={self.data!r}"

    __hash__: Final = Frame.__hash__


class SIGN(Frame):
    """Signature frame."""

    group: int = 0x80
    sig: bytes

    _framespec = [
        ByteSpec('group', default=0x80),
        BinaryDataSpec('sig'),
    ]

    @property
    @override
    def HashKey(self):
        return f'{self.FrameID}:{self.group}:{_bytes2key(self.sig)}'

    def __bytes__(self):
        return self.sig

    @override
    def __eq__(self, other: object):
        return self.sig == other

    __hash__: Final = Frame.__hash__


class SEEK(Frame):
    """Seek frame.

    Mutagen does not find tags at seek offsets.
    """

    offset: int = 0

    _framespec = [
        IntegerSpec('offset', default=0),
    ]

    def __pos__(self):
        return self.offset

    @override
    def __eq__(self, other: object):
        return self.offset == other

    __hash__: Final = Frame.__hash__


class ASPI(Frame):
    """Audio seek point index.

    Attributes: S, L, N, b, and Fi. For the meaning of these, see
    the ID3v2.4 specification. Fi is a list of integers.
    """

    S: int = 0
    L: int = 0
    N: int = 0
    b: int = 0
    Fi: list[int] = []

    _framespec = [
        SizedIntegerSpec("S", size=4, default=0),
        SizedIntegerSpec("L", size=4, default=0),
        SizedIntegerSpec("N", size=2, default=0),
        ByteSpec("b", default=0),
        ASPIIndexSpec("Fi", default=[]),
    ]

    @override
    def __eq__(self, other: object):
        return self.Fi == other

    __hash__: Final = Frame.__hash__


# ID3v2.2 frames
class UFI(UFID):
    "Unique File Identifier"


class TT1(TIT1):
    "Content group description"


class TT2(TIT2):
    "Title"


class TT3(TIT3):
    "Subtitle/Description refinement"


class TP1(TPE1):
    "Lead Artist/Performer/Soloist/Group"


class TP2(TPE2):
    "Band/Orchestra/Accompaniment"


class TP3(TPE3):
    "Conductor"


class TP4(TPE4):
    "Interpreter/Remixer/Modifier"


class TCM(TCOM):
    "Composer"


class TXT(TEXT):
    "Lyricist"


class TLA(TLAN):
    "Audio Language(s)"


class TCO(TCON):
    "Content Type (Genre)"


class TAL(TALB):
    "Album"


class TPA(TPOS):
    "Part of set"


class TRK(TRCK):
    "Track Number"


class TRC(TSRC):
    "International Standard Recording Code (ISRC)"


class TYE(TYER):
    "Year of recording"


class TDA(TDAT):
    "Date of recording (DDMM)"


class TIM(TIME):
    "Time of recording (HHMM)"


class TRD(TRDA):
    "Recording Dates"


class TMT(TMED):
    "Source Media Type"


class TFT(TFLT):
    "File Type"


class TBP(TBPM):
    "Beats per minute"


class TCP(TCMP):
    "iTunes Compilation Flag"


class TCR(TCOP):
    "Copyright (C)"


class TPB(TPUB):
    "Publisher"


class TEN(TENC):
    "Encoder"


class TST(TSOT):
    "Title Sort Order key"


class TSA(TSOA):
    "Album Sort Order key"


class TS2(TSO2):
    "iTunes Album Artist Sort"


class TSP(TSOP):
    "Performer Sort Order key"


class TSC(TSOC):
    "iTunes Composer Sort"


class TSS(TSSE):
    "Encoder settings"


class TOF(TOFN):
    "Original Filename"


class TLE(TLEN):
    "Audio Length (ms)"


class TSI(TSIZ):
    "Audio Data size (bytes)"


class TDY(TDLY):
    "Audio Delay (ms)"


class TKE(TKEY):
    "Starting Key"


class TOT(TOAL):
    "Original Album"


class TOA(TOPE):
    "Original Artist/Performer"


class TOL(TOLY):
    "Original Lyricist"


class TOR(TORY):
    "Original Release Year"


class TXX(TXXX):
    "User-defined Text"


class WAF(WOAF):
    "Official File Information"


class WAR(WOAR):
    "Official Artist/Performer Information"


class WAS(WOAS):
    "Official Source Information"


class WCM(WCOM):
    "Commercial Information"


class WCP(WCOP):
    "Copyright Information"


class WPB(WPUB):
    "Official Publisher Information"


class WXX(WXXX):
    "User-defined URL"


class IPL(IPLS):
    "Involved people list"


class MCI(MCDI):
    "Binary dump of CD's TOC"


class ETC(ETCO):
    "Event timing codes"


class MLL(MLLT):
    "MPEG location lookup table"


class STC(SYTC):
    "Synced tempo codes"


class ULT(USLT):
    "Unsynchronised lyrics/text transcription"


class SLT(SYLT):
    "Synchronised lyrics/text"


class COM(COMM):
    "Comment"


class RVA(RVAD):
    "Relative volume adjustment"

    adjustments: list[object]

    _framespec = [
        RVASpec("adjustments", stereo_only=True),
    ]

    @override
    def _to_other(self, other: object):
        if not isinstance(other, RVAD):
            raise TypeError

        other.adjustments = list(self.adjustments)

# class EQU(EQUA)


class REV(RVRB):
    "Reverb"


class PIC(APIC):
    """Attached Picture.

    The 'mime' attribute of an ID3v2.2 attached picture must be either
    'PNG' or 'JPG'.
    """

    encoding: int
    mime: str = "JPG"
    type: PictureType
    desc: str
    data: bytes

    _framespec = [
        EncodingSpec('encoding'),
        StringSpec('mime', length=3, default="JPG"),
        PictureTypeSpec('type'),
        EncodedTextSpec('desc'),
        BinaryDataSpec('data'),
    ]

    @override
    def _to_other(self, other: object):
        if not isinstance(other, APIC):
            raise TypeError

        other.encoding = self.encoding
        other.mime = self.mime
        other.type = self.type
        other.desc = self.desc
        other.data = self.data


class GEO(GEOB):
    "General Encapsulated Object"


class CNT(PCNT):
    "Play counter"


class POP(POPM):
    "Popularimeter"


class BUF(RBUF):
    "Recommended buffer size"


class CRM(Frame):
    """Encrypted meta frame"""

    owner: str
    desc: str
    data: bytes

    _framespec = [
        Latin1TextSpec('owner'),
        Latin1TextSpec('desc'),
        BinaryDataSpec('data'),
    ]

    @override
    def __eq__(self, other: object):
        return self.data == other

    __hash__: Final = Frame.__hash__


class CRA(AENC):
    "Audio encryption"


class LNK(LINK):
    """Linked information"""

    frameid: str
    url: str
    data: bytes

    _framespec = [
        FrameIDSpec('frameid', length=3),
        Latin1TextSpec('url'),
        BinaryDataSpec('data'),
    ]

    @override
    def _to_other(self, other: object):
        if not isinstance(other, LINK):
            raise TypeError

        if isinstance(other, LNK):
            new_frameid = self.frameid
        else:
            try:
                new_frameid = Frames_2_2[self.frameid].__bases__[0].__name__
            except KeyError:
                new_frameid = self.frameid.ljust(4)

        # we could end up with invalid IDs here, so bypass the validation
        other._setattr("frameid", new_frameid)

        other.url = self.url
        other.data = self.data


Frames: dict[str, type[Frame]] = {}
"""All supported ID3v2.3/4 frames, keyed by frame name."""


Frames_2_2: dict[str, type[Frame]] = {}
"""All supported ID3v2.2 frames, keyed by frame name."""


k, v = None, None
for k, v in globals().items():
    if isinstance(v, type) and issubclass(v, Frame):
        v.__module__ = "mutagen.id3"

        if len(k) == 3:
            Frames_2_2[k] = v
        elif len(k) == 4:
            Frames[k] = v

try:
    del k
    del v
except NameError:
    pass
