#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name="mutagen", version="1.2",
      url="http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen",
      description="read and write ID3v1/ID3v2/APEv2/FLAC audio tags",
      author="Michael Urman",
      author_email="quodlibet@lists.sacredchao.net",
      license="GNU GPL v2",
      packages=["mutagen"],
      long_description="""\
Mutagen is an audio metadata tag reader and writer implemented in pure
Python. It supports reading ID3v1.1, ID3v2.2, ID3v2.3, ID3v2.4, APEv2, and
FLAC, and writing ID3v1.1, ID3v2.4, APEv2, and FLAC. It can also read
MPEG audio and Xing headers, and FLAC stream information.

With the help of pyvorbis (http://www.andrewchatham.com/pyogg/), it can
read and write Ogg Vorbis comments.
"""
    )
