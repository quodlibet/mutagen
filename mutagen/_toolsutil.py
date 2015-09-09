# -*- coding: utf-8 -*-

# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys
import signal
import locale
import contextlib
import optparse
import ctypes

from ._compat import text_type, PY2, PY3, iterbytes


def split_escape(string, sep, maxsplit=None, escape_char="\\"):
    """Like unicode/str/bytes.split but allows for the separator to be escaped

    If passed unicode/str/bytes will only return list of unicode/str/bytes.
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    if isinstance(string, bytes):
        if isinstance(escape_char, text_type):
            escape_char = escape_char.encode("ascii")
        iter_ = iterbytes
    else:
        iter_ = iter

    if maxsplit is None:
        maxsplit = len(string)

    empty = string[:0]
    result = []
    current = empty
    escaped = False
    for char in iter_(string):
        if escaped:
            if char != escape_char and char != sep:
                current += escape_char
            current += char
            escaped = False
        else:
            if char == escape_char:
                escaped = True
            elif char == sep and len(result) < maxsplit:
                result.append(current)
                current = empty
            else:
                current += char
    result.append(current)
    return result


class SignalHandler(object):

    def __init__(self):
        self._interrupted = False
        self._nosig = False
        self._init = False

    def init(self):
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
        if os.name != "nt":
            signal.signal(signal.SIGHUP, self._handler)

    def _handler(self, signum, frame):
        self._interrupted = True
        if not self._nosig:
            raise SystemExit("Aborted...")

    @contextlib.contextmanager
    def block(self):
        """While this context manager is active any signals for aborting
        the process will be queued and exit the program once the context
        is left.
        """

        self._nosig = True
        yield
        self._nosig = False
        if self._interrupted:
            raise SystemExit("Aborted...")


def get_win32_unicode_argv():
    """Returns a unicode argv under Windows and standard sys.argv otherwise"""

    if os.name != "nt" or not PY2:
        return sys.argv

    import ctypes
    from ctypes import cdll, windll, wintypes

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = wintypes.LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)

    LocalFree = windll.kernel32.LocalFree
    LocalFree.argtypes = [wintypes.HLOCAL]
    LocalFree.restype = wintypes.HLOCAL

    argc = ctypes.c_int()
    argv = CommandLineToArgvW(GetCommandLineW(), ctypes.byref(argc))
    if not argv:
        return

    res = argv[max(0, argc.value - len(sys.argv)):argc.value]

    LocalFree(argv)

    return res


def fsencoding():
    """The encoding used for paths, argv, environ, stdout and stdin"""

    if os.name == "nt":
        return ""

    return locale.getpreferredencoding() or "utf-8"


def fsnative(text=u""):
    """Returns the passed text converted to the preferred path type
    for each platform.
    """

    assert isinstance(text, text_type)

    if os.name == "nt" or PY3:
        return text
    else:
        return text.encode(fsencoding(), "replace")
    return text


def is_fsnative(arg):
    """If the passed value is of the preferred path type for each platform.
    Note that on Python3+linux, paths can be bytes or str but this returns
    False for bytes there.
    """

    if PY3 or os.name == "nt":
        return isinstance(arg, text_type)
    else:
        return isinstance(arg, bytes)


def print_(*objects, **kwargs):
    """A print which supports bytes and str+surrogates under python3.

    Needed so we can print anything passed to us through argv and environ.
    Under Windows only text_type is allowed.

    Arguments:
        objects: one or more bytes/text
        linesep (bool): whether a line separator should be appended
        sep (bool): whether objects should be printed separated by spaces
    """

    linesep = kwargs.pop("linesep", True)
    sep = kwargs.pop("sep", True)
    file_ = kwargs.pop("file", None)
    if file_ is None:
        file_ = sys.stdout

    old_cp = None
    if os.name == "nt":
        # Try to force the output to cp65001 aka utf-8.
        # If that fails use the current one (most likely cp850, so
        # most of unicode will be replaced with '?')
        encoding = "utf-8"
        old_cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        if ctypes.windll.kernel32.SetConsoleOutputCP(65001) == 0:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            old_cp = None
    else:
        encoding = fsencoding()

    try:
        if linesep:
            objects = list(objects) + [os.linesep]

        parts = []
        for text in objects:
            if isinstance(text, text_type):
                if PY3:
                    try:
                        text = text.encode(encoding, 'surrogateescape')
                    except UnicodeEncodeError:
                        text = text.encode(encoding, 'replace')
                else:
                    text = text.encode(encoding, 'replace')
            parts.append(text)

        data = (b" " if sep else b"").join(parts)
        try:
            fileno = file_.fileno()
        except (AttributeError, OSError, ValueError):
            # for tests when stdout is replaced
            try:
                file_.write(data)
            except TypeError:
                file_.write(data.decode(encoding, "replace"))
        else:
            file_.flush()
            os.write(fileno, data)
    finally:
        # reset the code page to what we had before
        if old_cp is not None:
            ctypes.windll.kernel32.SetConsoleOutputCP(old_cp)


class OptionParser(optparse.OptionParser):
    """OptionParser subclass which supports printing Unicode under Windows"""

    def print_help(self, file=None):
        print_(self.format_help(), file=file)
