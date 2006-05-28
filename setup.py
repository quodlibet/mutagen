#!/usr/bin/env python

import os
import glob

from distutils.core import setup, Extension

if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

setup(name="mutagen", version="1.3",
      url="http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen",
      description="read and write ID3v1/ID3v2/APEv2/FLAC/Ogg audio tags",
      author="Michael Urman",
      author_email="quodlibet@lists.sacredchao.net",
      license="GNU GPL v2",
      packages=["mutagen"],
      data_files=data_files,
      scripts=glob.glob("tools/m*[!~]"),
      long_description="""\
Mutagen is a Python module to handle audio metadata. It supports
reading ID3 (all versions), APEv2, Ogg Vorbis, FLAC, and Ogg FLAC, and
writing ID3v1.1, ID3v2.4, APEv2, Ogg Vorbis, FLAC, and Ogg FLAC. It
can also read MPEG audio and Xing headers, FLAC stream info blocks,
and Ogg Vorbis and Ogg FLAC stream headers. Finally, it includes a
module to handle generic Ogg bitstreams.
"""
    )
