#!/usr/bin/env python

import glob
import os
import shutil
import sys

from distutils.core import setup, Command

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

        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        if os.path.isdir(coverage):
            shutil.rmtree(coverage)

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
        import mmap
        from mmap import mmap as real_mmap
        class MockMMap(object):
            def __init__(self, *args, **kwargs): pass
            def move(self, dest, src, count): raise ValueError
            def close(self): pass
        print "Running tests with real mmap."
        if tests.unit(self.to_run):
            raise SystemExit("Test failures are listed above.")
        mmap.mmap = MockMMap
        print "Running tests with mocked failing mmap."
        if tests.unit(self.to_run):
            raise SystemExit("Test failures are listed above.")
        

class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = []

    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass

    def run(self):
        import trace
        tracer = trace.Trace(
            count=True, trace=False, ignoremods=["tests"],
            ignoredirs=[sys.prefix, sys.exec_prefix, "tests"])
        def run_tests():
            import tests
            tests.unit()
        tracer.runfunc(run_tests)
        results = tracer.results()
        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        results.write_results(show_missing=True, coverdir=coverage)
        map(os.unlink, glob.glob(os.path.join(coverage, "[!m]*.cover")))
        print "Coverage data written to", coverage

if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

setup(cmdclass={'clean': clean, 'test': test_cmd, 'coverage': coverage_cmd},
      name="mutagen", version="1.4",
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
