# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import traceback
from collections.abc import Sequence
from types import TracebackType
from typing import override

from mutagen.id3 import ID3

from ._util import SignalHandler

ErrorEntry = tuple[str, type[BaseException] | None, BaseException | None, TracebackType | None]


class Report:
    name: str
    files: int
    unsync: int
    missings: int
    errors: list[ErrorEntry]
    exceptions: dict[type[BaseException], int]
    versions: dict[tuple[int, ...], int]

    def __init__(self, pathname: str):
        self.name = pathname
        self.files = 0
        self.unsync = 0
        self.missings = 0
        self.errors = []
        self.exceptions = {}
        self.versions = {}

    def missing(self, filename: str) -> None:
        self.missings += 1
        self.files += 1

    def error(self, filename: str) -> None:
        Ex, value, trace = sys.exc_info()
        _ = self.exceptions.setdefault(Ex, 0)
        self.exceptions[Ex] += 1
        self.errors.append((filename, Ex, value, trace))
        self.files += 1

    def success(self, id3: ID3) -> None:
        self.versions.setdefault(id3.version, 0)
        self.versions[id3.version] += 1
        self.files += 1
        if id3.f_unsynch:
            self.unsync += 1

    @override
    def __str__(self) -> str:
        strings = [f"-- Report for {self.name} --"]
        if self.files == 0:
            return strings[0] + "\n" + "No MP3 files found.\n"

        good = self.files - len(self.errors)
        strings.append("Loaded %d/%d files (%d%%)" % (
            good, self.files, (float(good) / self.files) * 100))
        strings.append("%d files with unsynchronized frames." % self.unsync)
        strings.append("%d files without tags." % self.missings)

        strings.append("\nID3 Versions:")
        items = list(self.versions.items())
        items.sort()
        for v, i in items:
            strings.append("  %s\t%d" % (".".join(map(str, v)), i))

        if self.exceptions:
            strings.append("\nExceptions:")
            items = list(self.exceptions.items())
            items.sort()
            for Ex, i in items:
                strings.append("  %-20s\t%d" % (Ex.__name__, i))

        if self.errors:
            strings.append("\nERRORS:\n")
            for filename, Ex, value, trace in self.errors:
                strings.append(f"\nReading {filename}:")
                strings.append(
                    "".join(traceback.format_exception(Ex, value, trace)[1:]))
        else:
            strings.append("\nNo errors!")

        return "\n".join(strings)


def check_dir(path: str) -> None:
    from mutagen.mp3 import MP3

    rep = Report(path)
    print("Scanning", path)
    for path, _dirs, files in os.walk(path):
        files.sort()
        for fn in files:
            if not fn.lower().endswith('.mp3'):
                continue
            ffn = os.path.join(path, fn)
            try:
                mp3 = MP3(ffn)
            except Exception:
                rep.error(ffn)
            else:
                if mp3.tags is None:
                    rep.missing(ffn)
                else:
                    rep.success(mp3.tags)

    print(str(rep))


def main(argv: Sequence[str]) -> None:
    if len(argv) == 1:
        print("Usage:", argv[0], "directory ...")
    else:
        for path in argv[1:]:
            check_dir(path)


def entry_point() -> None:
    SignalHandler().init()
    return main(sys.argv)
