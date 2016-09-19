# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

import os
import sys
import ctypes
import codecs

from . import _winapi as winapi
from ._compat import text_type, PY3, PY2, url2pathname, urlparse, quote, \
    unquote


is_win = os.name == "nt"
is_unix = not is_win
is_darwin = sys.platform == "darwin"

_surrogatepass = "strict" if PY2 else "surrogatepass"


def _decode_surrogatepass(data, codec):
    """Like data.decode(codec, 'surrogatepass') but makes utf-16-le work
    on Python < 3.4 + Windows

    https://bugs.python.org/issue27971

    Raises UnicodeDecodeError, LookupError
    """

    try:
        return data.decode(codec, _surrogatepass)
    except UnicodeDecodeError:
        if os.name == "nt" and sys.version_info[:2] < (3, 4) and \
                codecs.lookup(codec).name == "utf-16-le":
            buffer_ = ctypes.create_string_buffer(data + b"\x00\x00")
            value = ctypes.wstring_at(buffer_, len(data) // 2)
            if value.encode("utf-16-le", _surrogatepass) != data:
                raise
            return value
        else:
            raise


def _fsnative(text):
    if not isinstance(text, text_type):
        raise TypeError("%r needs to be a text type (%r)" % (text, text_type))

    if is_unix:
        # First we go to bytes so we can be sure we have a valid source.
        # Theoretically we should fail here in case we have a non-unicode
        # encoding. But this would make everything complicated and there is
        # no good way to handle a failure from the user side. Instead
        # fall back to utf-8 which is the most likely the right choice in
        # a mis-configured environment
        encoding = _encoding
        try:
            path = text.encode(encoding, _surrogatepass)
        except UnicodeEncodeError:
            path = text.encode("utf-8", _surrogatepass)
        if PY3:
            return path.decode(_encoding, "surrogateescape")
        return path
    else:
        return text


def _create_fsnative(type_):
    # a bit of magic to make fsnative(u"foo") and isinstance(path, fsnative)
    # work

    class meta(type):

        def __instancecheck__(self, instance):
            # XXX: invalid str on Unix + Py3 still returns True here, but
            # might fail when passed to fsnative API. We could be more strict
            # here and call _validate_fsnative(), but then we could
            # have a value not being an instance of fsnative, while its type
            # is still a subclass of fsnative.. and this is enough magic
            # already.
            return isinstance(instance, type_)

        def __subclasscheck__(self, subclass):
            return issubclass(subclass, type_)

    class impl(object):
        """fsnative(text=u"")

        Args:
            text (text): The text to convert to a path
        Returns:
            fsnative: The new path.
        Raises:
            TypeError: In case something other then `text` has been passed

        This type is a virtual base class for the real path type.
        Instantiating it returns an instance of the real path type and it
        overrides instance and subclass checks so that `isinstance` and
        `issubclass` checks work:

        ::

            isinstance(fsnative(u"foo"), fsnative) == True
            issubclass(type(fsnative(u"foo")), fsnative) == True

        The real returned type is:

        - Python 2 + Windows: :obj:`python:unicode` with ``surrogates``
        - Python 2 + Unix: :obj:`python:str`
        - Python 3 + Windows: :obj:`python3:str` with ``surrogates``
        - Python 3 + Unix: :obj:`python3:str` with ``surrogates`` (only
          containing code points which can be encoded with the locale encoding)

        Constructing a `fsnative` can't fail.
        """

        def __new__(cls, text=u""):
            return _fsnative(text)

    new_type = meta("fsnative", (object,), dict(impl.__dict__))
    new_type.__module__ = "senf"
    return new_type


fsnative_type = text_type if is_win or PY3 else bytes
fsnative = _create_fsnative(fsnative_type)


def _validate_fsnative(path):
    """
    Args:
        path (fsnative)
    Returns:
        `text` on Windows, `bytes` on Unix
    Raises:
        TypeError: in case the type is wrong or the ´str` on Py3 + Unix
            can't be converted to `bytes`

    This helper allows to validate the type and content of a path.
    To reduce overhead the encoded value for Py3 + Unix is returned so
    it can be reused.
    """

    if not isinstance(path, fsnative_type):
        raise TypeError("path needs to be %s, not %s" % (
            fsnative_type.__name__, type(path).__name__))

    if PY3 and is_unix:
        try:
            return path.encode(_encoding, "surrogateescape")
        except UnicodeEncodeError:
            # This look more like ValueError, but raising only one error
            # makes things simpler... also one could say str + surrogates
            # is its own type
            raise TypeError("path contained Unicode code points not valid in"
                            "the current path encoding. To create a valid "
                            "path from Unicode use text2fsn()")

    return path


def _get_encoding():
    """The encoding used for paths, argv, environ, stdout and stdin"""

    encoding = sys.getfilesystemencoding()
    if encoding is None:
        if is_darwin:
            return "utf-8"
        elif is_win:
            return "mbcs"
        else:
            return "ascii"
    return encoding

_encoding = _get_encoding()


def path2fsn(path):
    """
    Args:
        path (pathlike): The path to convert
    Returns:
        `fsnative`
    Raises:
        TypeError: In case the type can't be converted to a `fsnative`
        ValueError: In case conversion fails

    Returns a `fsnative` path for a `pathlike`.
    """

    # allow mbcs str on py2+win and bytes on py3
    if PY2:
        if is_win:
            if isinstance(path, str):
                path = path.decode(_encoding)
        else:
            if isinstance(path, unicode):
                path = path.encode(_encoding)
    else:
        path = getattr(os, "fspath", lambda x: x)(path)
        if isinstance(path, bytes):
            path = path.decode(_encoding, "surrogateescape")
        elif is_unix and isinstance(path, str):
            # make sure we can encode it and this is not just some random
            # unicode string
            path.encode(_encoding, "surrogateescape")

    if not isinstance(path, fsnative_type):
        raise TypeError("path needs to be %s", fsnative_type.__name__)

    return path


def fsn2text(path):
    """
    Args:
        path (fsnative): The path to convert
    Returns:
        `text`
    Raises:
        TypeError: In case no `fsnative` has been passed

    Converts a `fsnative` path to `text`.

    This process is not reversible and should only be used for display
    purposes.
    Encoding with a Unicode encoding will always succeed with the result.
    """

    path = _validate_fsnative(path)

    if is_win:
        return path.encode("utf-16-le", _surrogatepass).decode("utf-16-le",
                                                               "replace")
    else:
        return path.decode(_encoding, "replace")


def text2fsn(text):
    """
    Args:
        text (text): The text to convert
    Returns:
        `fsnative`
    Raises:
        TypeError: In case no `text` has been passed

    Takes `text` and converts it to a `fsnative`.

    This operation is not reversible and can't fail.
    """

    return fsnative(text)


def fsn2bytes(path, encoding):
    """
    Args:
        path (fsnative): The path to convert
        encoding (`str` or `None`): `None` if you don't care about Windows
    Returns:
        `bytes`
    Raises:
        TypeError: If no `fsnative` path is passed
        ValueError: If encoding fails or no encoding is given

    Turns a `fsnative` path to `bytes`.

    The passed *encoding* is only used on platforms where paths are not
    associated with an encoding (Windows for example). If you don't care about
    Windows you can pass `None`.
    """

    path = _validate_fsnative(path)

    if is_win:
        if encoding is None:
            raise ValueError("invalid encoding %r" % encoding)

        try:
            return path.encode(encoding, _surrogatepass)
        except LookupError:
            raise ValueError("invalid encoding %r" % encoding)
    else:
        return path


def bytes2fsn(data, encoding):
    """
    Args:
        data (bytes): The data to convert
        encoding (`str` or `None`): `None` if you don't care about Windows
    Returns:
        `fsnative`
    Raises:
        TypeError: If no `bytes` path is passed
        ValueError: If decoding fails or no encoding is given

    Turns `bytes` to a `fsnative` path.

    The passed *encoding* is only used on platforms where paths are not
    associated with an encoding (Windows for example). If you don't care about
    Windows you can pass `None`.
    """

    if not isinstance(data, bytes):
        raise TypeError("data needs to be bytes")

    if is_win:
        if encoding is None:
            raise ValueError("invalid encoding %r" % encoding)
        try:
            return _decode_surrogatepass(data, encoding)
        except LookupError:
            raise ValueError("invalid encoding %r" % encoding)
    elif PY2:
        return data
    else:
        return data.decode(_encoding, "surrogateescape")


def uri2fsn(uri):
    """
    Args:
        uri (`text` or :obj:`python:str`): A file URI
    Returns:
        `fsnative`
    Raises:
        TypeError: In case an invalid type is passed
        ValueError: In case the URI isn't a valid file URI

    Takes a file URI and returns a `fsnative` path
    """

    if PY2:
        if isinstance(uri, unicode):
            uri = uri.encode("utf-8")
        if not isinstance(uri, bytes):
            raise TypeError("uri needs to be ascii str or unicode")
    else:
        if not isinstance(uri, str):
            raise TypeError("uri needs to be str")

    parsed = urlparse(uri)
    scheme = parsed.scheme
    netloc = parsed.netloc
    path = parsed.path

    if scheme != "file":
        raise ValueError("Not a file URI")

    if is_win:
        path = url2pathname(netloc + path)
        if netloc:
            path = "\\\\" + path
        if PY2:
            path = path.decode("utf-8")
        return path
    else:
        if PY2:
            return url2pathname(path)
        else:
            return fsnative(url2pathname(path))


def fsn2uri(path):
    """
    Args:
        path (fsnative): The path to convert to an URI
    Returns:
        `str`: An ASCII only URI
    Raises:
        TypeError: If no `fsnative` was passed
        ValueError: If the path can't be converted

    Takes a `fsnative` path and returns a file URI.

    On Windows non-ASCII characters will be encoded using utf-8 and then
    percent encoded.
    """

    path = _validate_fsnative(path)

    def _quote_path(path):
        # RFC 2396
        return quote(path, "/:@&=+$,")

    if is_win:
        buf = ctypes.create_unicode_buffer(winapi.INTERNET_MAX_URL_LENGTH)
        length = winapi.DWORD(winapi.INTERNET_MAX_URL_LENGTH)
        flags = 0
        try:
            winapi.UrlCreateFromPathW(path, buf, ctypes.byref(length), flags)
        except WindowsError as e:
            raise ValueError(e)
        uri = buf[:length.value]

        # For some reason UrlCreateFromPathW escapes some chars outside of
        # ASCII and some not. Unquote and re-quote with utf-8.
        if PY3:
            # latin-1 maps code points directly to bytes, which is what we want
            uri = unquote(uri, "latin-1")
        else:
            # Python 2 does what we want by default
            uri = unquote(uri)

        return _quote_path(uri.encode("utf-8", _surrogatepass))

    else:
        return "file://" + _quote_path(path)
