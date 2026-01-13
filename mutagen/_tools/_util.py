# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

import contextlib
import os
import signal
from collections.abc import Iterator
from types import FrameType

from mutagen._util import iterbytes


def split_escape(string: str | bytes, sep: str | bytes, maxsplit: int | None = None,
                 escape_char: str | bytes = "\\") -> list[str]:
    """Like unicode/str/bytes.split but allows for the separator to be escaped

    If passed unicode/str/bytes will only return list of unicode/str/bytes.
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    if isinstance(string, bytes):
        if isinstance(escape_char, str):
            escape_char = escape_char.encode("ascii")
        iter_ = iterbytes
    else:
        iter_ = iter

    if maxsplit is None:
        maxsplit = len(string)

    empty = string[:0]
    result: list[str] = []
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


class SignalHandler:

    _interrupted: bool
    _nosig: bool
    _init: bool

    def __init__(self):
        self._interrupted = False
        self._nosig = False
        self._init = False

    def init(self) -> None:
        _ = signal.signal(signal.SIGINT, self._handler)
        _ = signal.signal(signal.SIGTERM, self._handler)
        if os.name != "nt":
            _ = signal.signal(signal.SIGHUP, self._handler)

    def _handler(self, signum: int, frame: FrameType | None) -> None:
        self._interrupted = True
        if not self._nosig:
            raise SystemExit("Aborted...")

    @contextlib.contextmanager
    def block(self) -> Iterator[None]:
        """While this context manager is active any signals for aborting
        the process will be queued and exit the program once the context
        is left.
        """

        self._nosig = True
        yield
        self._nosig = False
        if self._interrupted:
            raise SystemExit("Aborted...")
