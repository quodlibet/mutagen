# -*- coding: utf-8 -*-
# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import sys
import struct

from mutagen._compat import swap_to_string, text_type, PY2, reraise
from mutagen._util import total_ordering

from ._util import ASFError


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
