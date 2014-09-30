#!/usr/bin/env python
# Copyright 2005-2009,2011 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import glob
import os
import shutil
import sys
import subprocess
import tarfile

from distutils.core import setup, Command
from distutils import dir_util

from distutils.command.clean import clean as distutils_clean
from distutils.command.sdist import sdist


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
                try:
                    os.unlink(os.path.join(pathname, filename))
                except EnvironmentError as err:
                    print(str(err))

        try:
            os.unlink("MANIFEST")
        except OSError:
            pass

        for base in ["coverage", "build", "dist"]:
            path = os.path.join(os.path.dirname(__file__), base)
            if os.path.isdir(path):
                shutil.rmtree(path)


class distcheck(sdist):

    def _check_manifest(self):
        assert self.get_archive_files()

        # make sure MANIFEST.in includes all tracked files
        if subprocess.call(["hg", "status"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0:
            # contains the packaged files after run() is finished
            included_files = self.filelist.files
            assert included_files

            process = subprocess.Popen(["hg", "locate"],
                                       stdout=subprocess.PIPE)
            out, err = process.communicate()
            assert process.returncode == 0

            tracked_files = out.splitlines()
            for ignore in [".hgignore", ".hgtags"]:
                tracked_files.remove(ignore)

            assert not set(tracked_files) - set(included_files), \
                "Not all tracked files included in tarball, update MANIFEST.in"

    def _check_dist(self):
        assert self.get_archive_files()

        distcheck_dir = os.path.join(self.dist_dir, "distcheck")
        if os.path.exists(distcheck_dir):
            dir_util.remove_tree(distcheck_dir)
        self.mkpath(distcheck_dir)

        archive = self.get_archive_files()[0]
        tfile = tarfile.open(archive, "r:gz")
        tfile.extractall(distcheck_dir)
        tfile.close()

        name = self.distribution.get_fullname()
        extract_dir =  os.path.join(distcheck_dir, name)

        old_pwd = os.getcwd()
        os.chdir(extract_dir)
        self.spawn([sys.executable, "setup.py", "test"])
        self.spawn([sys.executable, "setup.py", "build"])
        self.spawn([sys.executable, "setup.py", "build_sphinx"])
        self.spawn([sys.executable, "setup.py", "install",
                    "--prefix", "../prefix", "--record", "../log.txt"])
        os.environ["LC_ALL"] = "C"
        self.spawn([sys.executable, "setup.py", "test"])
        os.chdir(old_pwd)

    def run(self):
        sdist.run(self)
        self._check_manifest()
        self._check_dist()


class build_sphinx(Command):
    description = "build sphinx documentation"
    user_options = [
        ("build-dir=", "d", "build directory"),
    ]

    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        self.build_dir = self.build_dir or "build"

    def run(self):
        docs = "docs"
        target = os.path.join(self.build_dir, "sphinx")
        self.spawn(["sphinx-build", "-b", "html", "-n", docs, target])


class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("exitfirst", "x", "stop after first failing test"),
    ]

    def initialize_options(self):
        self.to_run = []
        self.quick = False
        self.exitfirst = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.exitfirst = bool(self.exitfirst)

    def run(self):
        import tests

        count, failures = tests.unit(self.to_run, self.exitfirst)
        if failures:
            print("%d out of %d failed" % (failures, count))
            raise SystemExit("Test failures are listed above.")


class quality_cmd(Command):
    description = "run pyflakes/pep8 tests"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import tests

        count, failures = tests.check()
        if failures:
            print("%d out of %d failed" % (failures, count))
            raise SystemExit("Test failures are listed above.")


class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = [
        ("quick", None, "don't run slow mmap-failing tests"),
    ]

    def initialize_options(self):
        self.quick = None

    def finalize_options(self):
        self.quick = bool(self.quick)

    def run(self):
        try:
            from coverage import coverage
        except ImportError:
            raise SystemExit(
                "Missing 'coverage' module. See "
                "https://pypi.python.org/pypi/coverage or try "
                "`apt-get install python-coverage python3-coverage`")

        for key in list(sys.modules.keys()):
            if key.startswith('mutagen'):
                del(sys.modules[key])

        cov = coverage()
        cov.start()

        cmd = self.reinitialize_command("test")
        cmd.quick = self.quick
        cmd.ensure_finalized()
        cmd.run()

        dest = os.path.join(os.getcwd(), "coverage")

        cov.stop()
        cov.html_report(
            directory=dest,
            ignore_errors=True,
            include=["mutagen/*", "tools/*"])

        print("Coverage summary: file://%s/index.html" % dest)


if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

if __name__ == "__main__":
    from mutagen import version_string

    cmd_classes = {
        "clean": clean,
        "test": test_cmd,
        "quality": quality_cmd,
        "coverage": coverage_cmd,
        "distcheck": distcheck,
        "build_sphinx": build_sphinx,
    }

    setup(cmdclass=cmd_classes,
          name="mutagen", version=version_string,
          url="https://bitbucket.org/lazka/mutagen",
          description="read and write audio tags for many formats",
          author="Michael Urman",
          author_email="quod-libet-development@groups.google.com",
          license="GNU GPL v2",
          classifiers=[
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
            'Topic :: Multimedia :: Sound/Audio',
          ],
          packages=["mutagen", "mutagen.id3"],
          data_files=data_files,
          scripts=[os.path.join("tools", name) for name in [
            "mid3cp",
            "mid3iconv",
            "mid3v2",
            "moggsplit",
            "mutagen-inspect",
            "mutagen-pony",
          ]],
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
