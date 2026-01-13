# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import struct
import sys
from functools import total_ordering
from typing import Any, Final, Self, SupportsInt, cast, final, override

from mutagen._util import reraise

from ._util import ASFError


class ASFBaseAttribute:
    """Generic attribute."""

    TYPE: int

    _TYPES: dict[int, type[Self]] = {}

    value: Any | None = None
    """The Python value of this attribute (type depends on the class)"""

    language: int | None
    """Language"""

    stream: int | None
    """Stream"""

    def __init__(self, value: object | None =None, data: bytes | None=None, language: int | None = None,
                 stream: int | None =None, **kwargs):
        self.language = language
        self.stream = stream
        if data is not None:
            self.value = self.parse(data, **kwargs)
        else:
            if value is None:
                # we used to support not passing any args and instead assign
                # them later, keep that working..
                self.value = None
            else:
                self.value = self._validate(value)

    @classmethod
    def _register(cls, other: type[Self]) -> type[Self]:
        cls._TYPES[other.TYPE] = other
        return other

    @classmethod
    def _get_type(cls, type_: int) -> type[Self]:
        """Raises KeyError"""

        return cls._TYPES[type_]

    def _validate(self, value: SupportsInt) -> object:
        """Raises TypeError or ValueError in case the user supplied value
        isn't valid.
        """

        return value

    def data_size(self) -> int:
        raise NotImplementedError

    @override
    def __repr__(self) -> str:
        name = f"{type(self).__name__}({self.value!r}"
        if self.language:
            name += f", language={self.language}"
        if self.stream:
            name += f", stream={self.stream}"
        name += ")"
        return name

    def render(self, name: str) -> bytes:
        nameb = name.encode("utf-16-le") + b"\x00\x00"
        data: bytes = self._render()
        return (struct.pack("<H", len(nameb)) + nameb +
                struct.pack("<HH", self.TYPE, len(data)) + data)

    def render_m(self, name: str) -> bytes:
        nameb = name.encode("utf-16-le") + b"\x00\x00"
        data = self._render(dword=False) if self.TYPE == 2 else self._render()
        return (struct.pack("<HHHHI", 0, self.stream or 0, len(nameb),
                            self.TYPE, len(data)) + nameb + data)

    def render_ml(self, name: str) -> bytes:
        nameb = name.encode("utf-16-le") + b"\x00\x00"
        data = self._render(dword=False) if self.TYPE == 2 else self._render()

        return (struct.pack("<HHHHI", self.language or 0, self.stream or 0,
                            len(nameb), self.TYPE, len(data)) + nameb + data)

@final
@ASFBaseAttribute._register
@total_ordering
class ASFUnicodeAttribute(ASFBaseAttribute):
    """Unicode string attribute.

    ::

        ASFUnicodeAttribute(u'some text')
    """

    TYPE = 0x0000
    value: str

    def parse(self, data: bytes) -> str:
        try:
            return data.decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError as e:
            reraise(ASFError, e, sys.exc_info()[2])

    @override
    def _validate(self, value: str | object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{value!r} not str")
        return value

    def _render(self) -> bytes:
        return self.value.encode("utf-16-le") + b"\x00\x00"

    @override
    def data_size(self):
        return len(self._render())

    def __bytes__(self):
        return self.value.encode("utf-16-le")

    @override
    def __str__(self):
        return self.value

    @override
    def __eq__(self, other: object) -> bool:
        return str(self) == other

    def __lt__(self, other: str) -> bool:
        return str(self) < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFByteArrayAttribute(ASFBaseAttribute):
    """Byte array attribute.

    ::

        ASFByteArrayAttribute(b'1234')
    """
    TYPE = 0x0001
    value: bytes

    def parse(self, data: bytes) -> bytes:
        assert isinstance(data, bytes)
        return data

    def _render(self) -> bytes:
        assert isinstance(self.value, bytes)
        return self.value

    @override
    def _validate(self, value: bytes | object) -> bytes:
        if not isinstance(value, bytes):
            raise TypeError(f"must be bytes/str: {value!r}")
        return value

    @override
    def data_size(self) -> int:
        return len(self.value)

    def __bytes__(self) -> bytes:
        return self.value

    @override
    def __str__(self):
        return f"[binary data ({len(self.value)} bytes)]"

    @override
    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __lt__(self, other: bytes) -> bool:
        return self.value < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFBoolAttribute(ASFBaseAttribute):
    """Bool attribute.

    ::

        ASFBoolAttribute(True)
    """

    TYPE = 0x0002
    value: bool

    def parse(self, data: bytes, dword: bool=True) -> bool:
        if dword:
            return cast(int, struct.unpack("<I", data)[0]) == 1
        else:
            return cast(int, struct.unpack("<H", data)[0]) == 1

    def _render(self, dword: bool =True):
        if dword:
            return struct.pack("<I", bool(self.value))
        else:
            return struct.pack("<H", bool(self.value))

    @override
    def _validate(self, value: object) -> bool:
        return bool(value)

    @override
    def data_size(self):
        return 4

    def __bool__(self):
        return bool(self.value)

    def __bytes__(self):
        return str(self.value).encode('utf-8')

    @override
    def __str__(self):
        return str(self.value)

    @override
    def __eq__(self, other: object) -> bool:
        return bool(self.value) == other

    def __lt__(self, other: bool) -> bool:
        return bool(self.value) < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFDWordAttribute(ASFBaseAttribute):
    """DWORD attribute.

    ::

        ASFDWordAttribute(42)
    """

    TYPE = 0x0003
    value: int

    def parse(self, data: bytes) -> int:
        return cast(int, struct.unpack("<I", data)[0])

    def _render(self) -> bytes:
        return struct.pack("<L", self.value)

    @override
    def _validate(self, value: object) -> int:
        if not isinstance(value, SupportsInt):
            raise TypeError(f"must be int: {value!r}")
        value = int(value)
        if not 0 <= value <= 2 ** 32 - 1:
            raise ValueError("Out of range")
        return value

    @override
    def data_size(self) -> int:
        return 4

    def __int__(self) -> int:
        return self.value

    def __bytes__(self) -> bytes:
        return str(self.value).encode('utf-8')

    @override
    def __str__(self) -> str:
        return str(self.value)

    @override
    def __eq__(self, other: object) -> bool:
        return int(self.value) == other

    def __lt__(self, other: int) -> bool:
        return int(self.value) < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFQWordAttribute(ASFBaseAttribute):
    """QWORD attribute.

    ::

        ASFQWordAttribute(42)
    """

    TYPE = 0x0004
    value: int

    def parse(self, data: bytes) -> int:
        return cast(int, struct.unpack("<Q", data)[0])

    def _render(self) -> bytes:
        return struct.pack("<Q", self.value)

    @override
    def _validate(self, value: SupportsInt) -> int:
        valuei = int(value)
        if not 0 <= valuei <= 2 ** 64 - 1:
            raise ValueError("Out of range")
        return valuei

    @override
    def data_size(self) -> int:
        return 8

    def __int__(self) -> int:
        return self.value

    def __bytes__(self) -> bytes:
        return str(self.value).encode('utf-8')

    @override
    def __str__(self) -> str:
        return str(self.value)

    @override
    def __eq__(self, other: object) -> bool:
        return int(self.value) == other

    def __lt__(self, other: int) -> bool:
        return int(self.value) < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFWordAttribute(ASFBaseAttribute):
    """WORD attribute.

    ::

        ASFWordAttribute(42)
    """

    TYPE = 0x0005
    value: int

    def parse(self, data: bytes) -> int:
        return cast(int, struct.unpack("<H", data)[0])

    def _render(self) -> bytes:
        return struct.pack("<H", self.value)

    @override
    def _validate(self, value: object) -> int:
        if not isinstance(value, SupportsInt):
            raise TypeError(f"must be int: {value!r}")
        valueInt = int(value)
        if not 0 <= valueInt <= 2 ** 16 - 1:
            raise ValueError("Out of range")
        return valueInt

    @override
    def data_size(self) -> int:
        return 2

    def __int__(self) -> int:
        return self.value

    def __bytes__(self) -> bytes:
        return str(self.value).encode('utf-8')

    @override
    def __str__(self) -> str:
        return str(self.value)

    @override
    def __eq__(self, other: object) -> bool:
        return int(self.value) == other

    def __lt__(self, other: int) -> bool:
        return int(self.value) < other

    __hash__: Final = ASFBaseAttribute.__hash__


@final
@ASFBaseAttribute._register
@total_ordering
class ASFGUIDAttribute(ASFBaseAttribute):
    """GUID attribute."""

    TYPE = 0x0006
    value: bytes

    def parse(self, data: bytes) -> bytes:
        assert isinstance(data, bytes)
        return data

    def _render(self):
        assert isinstance(self.value, bytes)
        return self.value

    @override
    def _validate(self, value: object) -> bytes:
        if not isinstance(value, bytes):
            raise TypeError(f"must be bytes/str: {value!r}")
        return value

    @override
    def data_size(self):
        return len(self.value)

    def __bytes__(self) -> bytes:
        return self.value

    @override
    def __str__(self):
        return repr(self.value)

    @override
    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __lt__(self, other: bytes) -> bool:
        return self.value < other

    __hash__: Final = ASFBaseAttribute.__hash__


def ASFValue(value: str, kind: int, **kwargs: bytes):
    """Create a tag value of a specific kind.

    ::

        ASFValue(u"My Value", UNICODE)

    :rtype: ASFBaseAttribute
    :raises TypeError: in case a wrong type was passed
    :raises ValueError: in case the value can't be be represented as ASFValue.
    """

    try:
        attr_type = ASFBaseAttribute._get_type(kind)
    except KeyError:
        raise ValueError(f"Unknown value type {kind!r}") from None
    else:
        return attr_type(value=value, **kwargs)
