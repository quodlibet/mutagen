#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name="mutagen", version="0.0",
      url="http://www.sacredchao.net/quodlibet/wiki/Mutagen",
      description="ID3v 1.1, 2.2, 2.3, 2.4 reader / 1.1, 2.4 writer",
      author="Michael Urman",
      license = "GNU GPL v2",
      packages = ["mutagen"],
    )
