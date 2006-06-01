#!/usr/bin/env python

import os
import sys
import glob

from distutils.core import setup, Extension, Command

from distutils.command.clean import clean as distutils_clean

class clean(distutils_clean):
    def run(self):
        # In addition to what the normal clean run does, remove pyc
        # and pyo files from the source tree.
        distutils_clean.run(self)
        def should_remove(filename):
            if filename.lower()[-4:] in [".pyc", ".pyo"]:
                return True
            else:
                return False
        for pathname, dirs, files in os.walk(os.path.dirname(__file__)):
            for filename in filter(should_remove, files):
                try: os.unlink(os.path.join(pathname, filename))
                except EnvironmentError, err:
                    print str(err)

class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)")
        ]

    def initialize_options(self):
        self.to_run = []

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")

    def run(self):
        import tests
        if tests.unit(self.to_run):
            raise SystemExit("Test failures are listed above.")

if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

setup(cmdclass={'clean': clean, 'test': test_cmd},
      name="mutagen", version="1.3",
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
