#!/usr/bin/env python

import glob
import os
import shutil
import sys

from distutils.core import setup, Command

from distutils.command.clean import clean as distutils_clean
from distutils.command.sdist import sdist as distutils_sdist

class release(Command):
    description = "release a new version of Mutagen"
    user_options = [
        ("all-the-way", None, "svn commit a new tag")
        ]

    def initialize_options(self):
        self.all_the_way = False

    def finalize_options(self):
        pass

    def rewrite_version(self, target, version):
        filename = os.path.join(target, "mutagen", "__init__.py")
        lines = file(filename, "rU").readlines()
        fileout = file(filename, "w")
        for line in lines:
            if line.startswith("version ="):
                fileout.write("version = %s\n" % repr(version))
            else:
                fileout.write(line)
        fileout.close()

    def run(self):
        from mutagen import version
        self.run_command("test")
        if version[-1] >= 0:
            raise SystemExit("%r: version number to release." % version)
        sversion = ".".join(map(str, version[:-1])) 
        target = "../tags/mutagen-%s" % sversion
        if os.path.isdir(target):
            raise SystemExit("%r was already released." % sversion)
        self.spawn(["svn", "export", os.getcwd(), target])
        self.spawn(["svn", "add", target])

        self.rewrite_version(target, version[:-1])

        if self.all_the_way:
            self.spawn(
                ["svn", "commit", "-m", "Mutagen %s." % sversion, target])
            os.chdir(target)
            print "Building release tarball."
            self.spawn(["./setup.py", "sdist"])
            self.spawn(["./setup.py", "register"])

class clean(distutils_clean):
    def run(self):
        # In addition to what the normal clean run does, remove pyc
        # and pyo and backup files from the source tree.
        distutils_clean.run(self)
        def should_remove(filename):
            if (filename.lower()[-4:] in [".pyc", ".pyo"] or
                filename.endswith("~") or
                (filename.startswith("#") and filename.endswith("#"))):
                return True
            else:
                return False
        for pathname, dirs, files in os.walk(os.path.dirname(__file__)):
            for filename in filter(should_remove, files):
                try: os.unlink(os.path.join(pathname, filename))
                except EnvironmentError, err:
                    print str(err)

        try: os.unlink("MANIFEST")
        except OSError: pass

        for base in ["coverage", "build", "dist"]:
             path = os.path.join(os.path.dirname(__file__), base)
             if os.path.isdir(path):
                 shutil.rmtree(path)

class sdist(distutils_sdist):
    def run(self):
        import mutagen
        if mutagen.version[-1] < 0:
            raise SystemExit(
                "Refusing to create a source distribution for a prerelease.")
        else:
            self.run_command("test")
            distutils_sdist.run(self)

class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("quick", None, "don't run slow mmap-failing tests"),
        ]

    def initialize_options(self):
        self.to_run = []
        self.quick = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")

    def run(self):
        import mmap

        print "Running tests with real mmap."
        self.__test()

        if self.quick:
            return

        def uses_mmap(Kind):
            return getattr(Kind, 'uses_mmap', True)

        try: import fcntl
        except ImportError:
            print "Unable to run mocked fcntl.lockf tests."
        else:
            def MockLockF(*args, **kwargs):
                raise IOError
            fcntl.lockf = MockLockF
            print "Running tests with mocked failing fcntl.lockf."
            self.__test(uses_mmap)

        class MockMMap(object):
            def __init__(self, *args, **kwargs): pass
            def move(self, dest, src, count): raise ValueError
            def close(self): pass
        print "Running tests with mocked failing mmap.move."
        mmap.mmap = MockMMap
        self.__test(uses_mmap)

        def MockMMap2(*args, **kwargs):
            raise EnvironmentError
        mmap.mmap = MockMMap2
        print "Running tests with mocked failing mmap.mmap."
        self.__test(uses_mmap)

    def __test(self, filter=None):
        import tests
        if tests.unit(self.to_run, filter):
            if sys.version[:3] == (2, 4, 2):
                print "You're running Python 2.4.2, which has known mmap bugs."
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
            count=True, trace=False,
            ignoredirs=[sys.prefix, sys.exec_prefix])
        def run_tests():
            import mutagen
            import mutagen._util
            reload(mutagen._util)
            reload(mutagen)
            self.run_command("test")
        tracer.runfunc(run_tests)
        results = tracer.results()
        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        results.write_results(show_missing=True, coverdir=coverage)
        map(os.unlink, glob.glob(os.path.join(coverage, "[!m]*.cover")))
        try: os.unlink(os.path.join(coverage, "..setup.cover"))
        except OSError: pass

        total_lines = 0
        bad_lines = 0
        for filename in glob.glob(os.path.join(coverage, "*.cover")):
            lines = file(filename, "rU").readlines()
            total_lines += len(lines)
            bad_lines += len(
                [line for line in lines if
                 (line.startswith(">>>>>>") and
                  "finally:" not in line and '"""' not in line)])
        pct = 100.0 * (total_lines - bad_lines) / float(total_lines)
        print "Coverage data written to", coverage, "(%d/%d, %0.2f%%)" % (
            total_lines - bad_lines, total_lines, pct)
        if pct < 98.66:
            raise SystemExit("Coverage percentage went down; write more tests.")
        if pct > 98.7:
            raise SystemExit("Coverage percentage went up; change setup.py.")

if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

if __name__ == "__main__":
    from mutagen import version_string
    setup(cmdclass={'clean': clean, 'test': test_cmd, 'coverage': coverage_cmd,
                    "sdist": sdist, "release": release},
          name="mutagen", version=version_string,
          url="http://code.google.com/p/mutagen/",
          description="read and write audio tags for many formats",
          author="Michael Urman",
          author_email="quod-libet-development@groups.google.com",
          license="GNU GPL v2",
          packages=["mutagen"],
          data_files=data_files,
          scripts=glob.glob("tools/m*[!~]"),
          long_description="""\
Mutagen is a Python module to handle audio metadata. It supports ASF,
FLAC, M4A, Monkey's Audio, MP3, Musepack, Ogg FLAC, Ogg Speex, Ogg
Theora, Ogg Vorbis, True Audio, WavPack and OptimFROG audio files. All
versions of ID3v2 are supported, and all standard ID3v2.4 frames are
parsed. It can read Xing headers to accurately calculate the bitrate
and length of MP3s. ID3 and APEv2 tags can be edited regardless of
audio format. It can also manipulate Ogg streams on an individual
packet/page level.
"""
          )
