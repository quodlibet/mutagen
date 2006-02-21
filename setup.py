#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name="mutagen", version="0.9",
      url="http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen",
      description="read and write ID3v1/ID3v2/APEv2/FLAC audio tags",
      author="Michael Urman",
      license = "GNU GPL v2",
      packages = ["mutagen"],
    )
