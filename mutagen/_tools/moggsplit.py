# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Split a multiplex/chained Ogg file into its component parts."""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import TextIO

from ._util import SignalHandler

_sig = SignalHandler()

@dataclass
class Args(Namespace):
    extension: str
    pattern: str
    m3u: bool
    filenames: list[str]

def main(argv: Sequence[str]) -> None:
    import mutagen
    from mutagen.ogg import OggPage
    parser = ArgumentParser(
        usage="%(prog)s [options] filename.ogg ...",
        description="Split Ogg logical streams using Mutagen.",
    )

    _ = parser.add_argument(
        "--version", action="version",
        version="Mutagen {}".format(".".join(map(str, mutagen.version))))

    _ = parser.add_argument(
        "--extension", dest="extension", default="ogg", metavar='ext', type=str,
        help="use this extension (default 'ogg')")
    _ = parser.add_argument(
        "--pattern", dest="pattern", default="%(base)s-%(stream)d.%(ext)s", type=str,
        metavar='pattern', help="name files using this pattern")
    _ = parser.add_argument(
        "--m3u", dest="m3u", action="store_true", default=False, type=bool,
        help="generate an m3u (playlist) file")
    _ = parser.add_argument(
        "filenames", nargs="+", metavar="filename.ogg", type=str,
        help="Ogg files to split")

    args = parser.parse_args(argv[1:], namespace=Args())

    fileobjs: dict[int | str, BytesIO | TextIO] = {}
    format: dict[str, str | int] = {'ext': args.extension}
    for filename in args.filenames:
        with _sig.block():
            format["base"] = os.path.splitext(os.path.basename(filename))[0]
            with open(filename, "rb") as fileobj:
                if args.m3u:
                    m3u: TextIO | None = open(str(format["base"]) + ".m3u", "w")
                else:
                    m3u = None
                while True:
                    try:
                        page = OggPage(fileobj)
                    except EOFError:
                        break
                    else:
                        format["stream"] = page.serial
                        if page.serial not in fileobjs:
                            new_filename = args.pattern % format
                            new_fileobj = open(new_filename, "wb")
                            fileobjs[page.serial] = new_fileobj
                            if m3u:
                                _ = m3u.write(new_filename + "\r\n")
                        _ = fileobjs[page.serial].write(page.write())
                for f in fileobjs.values():
                    f.close()


def entry_point() -> None:
    _sig.init()
    return main(sys.argv)
