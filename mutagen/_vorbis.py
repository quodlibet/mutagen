# Copyright (C) 2005-2006  Joe Wreschnig
#                    2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write Vorbis comment data.

Vorbis comments are freeform key/value pairs; keys are
case-insensitive ASCII and values are Unicode strings. A key may have
multiple values.

The specification is at http://www.xiph.org/vorbis/doc/v-comment.html.
"""

import contextlib
import sys
from collections.abc import Callable
from io import BytesIO
from typing import Literal, SupportsIndex, override

import mutagen
from mutagen._util import DictMixin, MutagenError, cdata, reraise

type ErrorMode = Literal["strict", "replace", "ignore"]
type EncodedValue = str | bytes
type CommentPair = tuple[str, EncodedValue]


def is_valid_key(key: str) -> bool:
    """Return true if a string is a valid Vorbis comment key.

    Valid Vorbis comment keys are printable ASCII between 0x20 (space)
    and 0x7D ('}'), excluding '='.

    Takes str/unicode in Python 2, unicode in Python 3
    """

    if isinstance(key, bytes):
        raise TypeError("needs to be str not bytes")

    for c in key:
        if c < " " or c > "}" or c == "=":
            return False
    else:
        return bool(key)


istag: Callable[[str], bool] = is_valid_key


class error(MutagenError):
    pass


class VorbisUnsetFrameError(error):
    pass


class VorbisEncodingError(error):
    pass


class VComment(mutagen.Tags, list[CommentPair]):
    """A Vorbis comment parser, accessor, and renderer.

    All comment ordering is preserved. A VComment is a list of
    key/value pairs, and so any Python list method can be used on it.

    Vorbis comments are always wrapped in something like an Ogg Vorbis
    bitstream or a FLAC metadata block, so this loads string data or a
    file-like object, not a filename.

    Attributes:
        vendor (text): the stream 'vendor' (i.e. writer); default 'Mutagen'
    """

    vendor: str = "Mutagen " + mutagen.version_string
    _size: int = 0

    def __init__(
        self,
        data: bytes | BytesIO | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        # Collect the args to pass to load, this lets child classes
        # override just load and get equivalent magic for the
        # constructor.
        if data is not None:
            if isinstance(data, bytes):
                data = BytesIO(data)
            elif not hasattr(data, 'read'):
                raise TypeError("VComment requires bytes or a file-like")
            start = data.tell()
            self.load(data, *args, **kwargs)
            self._size = data.tell() - start

    def load(
        self,
        fileobj: BytesIO,
        errors: ErrorMode = 'replace',
        framing: bool = True,
    ) -> None:
        """Parse a Vorbis comment from a file-like object.

        Arguments:
            errors (str): 'strict', 'replace', or 'ignore'.
                This affects Unicode decoding and how other malformed content
                is interpreted.
            framing (bool): if true, fail if a framing bit is not present

        Framing bits are required by the Vorbis comment specification,
        but are not used in FLAC Vorbis comment blocks.
        """

        try:
            vendor_length = cdata.uint_le(fileobj.read(4))
            self.vendor = fileobj.read(vendor_length).decode('utf-8', errors)
            count: int = cdata.uint_le(fileobj.read(4))
            for i in range(count):
                length = cdata.uint_le(fileobj.read(4))
                try:
                    string = fileobj.read(length).decode('utf-8', errors)
                except (OverflowError, MemoryError):
                    raise error("cannot read %d bytes, too large" % length) from None
                try:
                    tag, value = string.split('=', 1)
                except ValueError as err:
                    if errors == "ignore":
                        continue
                    elif errors == "replace":
                        tag, value = f"unknown{i}", string
                    else:
                        reraise(VorbisEncodingError, err, sys.exc_info()[2])
                try:
                    tag = tag.encode('ascii', errors)
                except UnicodeEncodeError:
                    raise VorbisEncodingError(f"invalid tag name {tag!r}") from None
                else:
                    tag = tag.decode("ascii")
                    if is_valid_key(tag):
                        self.append((tag, value))

            if framing and not bytearray(fileobj.read(1))[0] & 0x01:
                raise VorbisUnsetFrameError("framing bit was unset")
        except (cdata.error, TypeError):
            raise error("file is not a valid Vorbis comment") from None

    def validate(self) -> bool:
        """Validate keys and values.

        Check to make sure every key used is a valid Vorbis key, and
        that every value used is a valid Unicode or UTF-8 string. If
        any invalid keys or values are found, a ValueError is raised.

        In Python 3 all keys and values have to be a string.
        """

        if not isinstance(self.vendor, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("vendor needs to be str")

        for key, value in self:
            try:
                if not is_valid_key(key):
                    raise ValueError(f"{key!r} is not a valid key")
            except TypeError:
                raise ValueError(f"{key!r} is not a valid key") from None

            if not isinstance(value, str):
                err = f"{value!r} needs to be str for key {key!r}"
                raise ValueError(err)

        return True

    @override
    def clear(self) -> None:
        """Clear all keys from the comment."""

        for i in list(self):
            self.remove(i)

    def write(self, framing: bool = True) -> bytes:
        """Return a string representation of the data.

        Validation is always performed, so calling this function on
        invalid data may raise a ValueError.

        Arguments:
            framing (bool): if true, append a framing bit (see load)
        """

        _ = self.validate()

        def _encode(value: EncodedValue) -> bytes:
            if not isinstance(value, bytes):
                return value.encode('utf-8')
            return value

        f = BytesIO()
        vendor = _encode(self.vendor)
        _ = f.write(cdata.to_uint_le(len(vendor)))
        _ = f.write(vendor)
        _ = f.write(cdata.to_uint_le(len(self)))
        for tag, value in self:
            tag = _encode(tag)
            value = _encode(value)
            comment = tag + b"=" + value
            _ =f.write(cdata.to_uint_le(len(comment)))
            _ =f.write(comment)
        if framing:
            _ =f.write(b"\x01")
        return f.getvalue()

    @override
    def pprint(self) -> str:

        def _decode(value: EncodedValue) -> str:
            if not isinstance(value, str):
                return value.decode('utf-8', 'replace')
            return value

        tags = [f"{_decode(k)}={_decode(v)}" for k, v in self]
        return "\n".join(tags)


class VCommentDict(VComment, DictMixin):  # type: ignore
    """A VComment that looks like a dictionary.

    This object differs from a dictionary in two ways. First,
    len(comment) will still return the number of values, not the
    number of keys. Secondly, iterating through the object will
    iterate over (key, value) pairs, not keys. Since a key may have
    multiple values, the same value may appear multiple times while
    iterating.

    Since Vorbis comment keys are case-insensitive, all keys are
    normalized to lowercase ASCII.
    """

    @override
    def __getitem__(self, key: SupportsIndex) -> list[EncodedValue] | VComment:
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.
        """

        if isinstance(key, slice):
            return VComment.__getitem__(self, key)

        if not is_valid_key(key):
            raise ValueError

        key = key.lower()

        values = [value for (k, value) in self if k.lower() == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    @override
    def __delitem__(self, key: str | slice) -> None:
        """Delete all values associated with the key."""

        if isinstance(key, slice):
            return VComment.__delitem__(self, key)

        if not is_valid_key(key):
            raise ValueError

        key = key.lower()
        to_delete = [x for x in self if x[0].lower() == key]
        if not to_delete:
            raise KeyError(key)
        else:
            for item in to_delete:
                self.remove(item)

    @override
    def __contains__(self, key: str) -> bool:
        """Return true if the key has any values."""

        if not is_valid_key(key):
            raise ValueError

        key = key.lower()
        return any(k.lower() == key for k, value in self)

    @override
    def __setitem__(
        self,
        key: str | slice,
        values: EncodedValue | list[EncodedValue],
    ) -> None:
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.
        """

        if isinstance(key, slice):
            return VComment.__setitem__(self, key, values)

        if not is_valid_key(key):
            raise ValueError

        if not isinstance(values, list):
            values = [values]
        with contextlib.suppress(KeyError):
            del self[key]

        for value in values:
            self.append((key, value))

    def keys(self) -> list[str]:
        """Return all keys in the comment."""

        return list(set([k.lower() for k, v in self]))

    def as_dict(self) -> dict[str, list[EncodedValue]]:
        """Return a copy of the comment data in a real dict."""

        return dict([(key, self[key]) for key in self.keys()])
