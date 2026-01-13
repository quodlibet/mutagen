# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Full tag list for any given file."""

from __future__ import annotations

import argparse
import sys

from ._util import SignalHandler

_sig = SignalHandler()


class Arguments(argparse.Namespace):
    files: list[str] = []


def main(argv: list[str]) -> None:
    from mutagen import File

    parser = argparse.ArgumentParser(usage="%(prog)s [options] FILE [FILE...]")
    parser.add_argument("--no-flac", help="Compatibility; does nothing.")
    parser.add_argument("--no-mp3", help="Compatibility; does nothing.")
    parser.add_argument("--no-apev2", help="Compatibility; does nothing.")
    parser.add_argument("files", nargs="+", metavar="FILE", help="Files to inspect")

    args = parser.parse_args(argv[1:], namespace=Arguments())

    for filename in args.files:
        print("--", filename)
        try:
            print("-", File(filename).pprint())
        except AttributeError:
            print("- Unknown file type")
        except Exception as err:
            print(str(err))
        print("")


def entry_point() -> None:
    _sig.init()
    return main(sys.argv)
