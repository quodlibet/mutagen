#!/usr/bin/env python
# Copyright 2005-2009,2011 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import glob
import os
import shutil
import sys
import subprocess
import tarfile
import warnings

from setuptools import setup, Command, Distribution


def get_command_class(name):
    # Returns the right class for either distutils or setuptools
    return Distribution({}).get_command_class(name)


distutils_clean = get_command_class("clean")


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


distutils_sdist = get_command_class("sdist")


def check_setuptools_for_dist():
    if "setuptools" not in sys.modules:
        raise Exception("setuptools not available")
    version = tuple(map(int, sys.modules["setuptools"].__version__.split(".")))
    if version < (24, 2, 0):
        raise Exception("setuptools too old")


class sdist(distutils_sdist):

    def run(self):
        check_setuptools_for_dist()
        distutils_sdist.run(self)


class distcheck(sdist):

    def _check_manifest(self):
        assert self.get_archive_files()

        # make sure MANIFEST.in includes all tracked files
        if subprocess.call(["git", "status"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0:
            # contains the packaged files after run() is finished
            included_files = self.filelist.files
            assert included_files

            process = subprocess.Popen(
                ["git", "ls-tree", "-r", "HEAD", "--name-only"],
                stdout=subprocess.PIPE, universal_newlines=True)
            out, err = process.communicate()
            assert process.returncode == 0

            tracked_files = out.splitlines()
            to_ignore = [
                ".gitignore",
                ".codecov.yml",
                ".github/workflows/test.yml",
                ".readthedocs.yaml",
                "docs/requirements.txt",
            ]
            for ignore in to_ignore:
                tracked_files.remove(ignore)

            tracked_files = [
                f for f in tracked_files if os.path.dirname(f) != "fuzzing"]

            diff = set(tracked_files) - set(included_files)
            assert not diff, (
                "Not all tracked files included in tarball, check MANIFEST.in",
                diff)

    def _check_dist(self):
        assert self.get_archive_files()

        distcheck_dir = os.path.join(self.dist_dir, "distcheck")
        if os.path.exists(distcheck_dir):
            shutil.rmtree(distcheck_dir)
        self.mkpath(distcheck_dir)

        archive = self.get_archive_files()[0]
        tfile = tarfile.open(archive, "r:gz")
        tfile.extractall(distcheck_dir)
        tfile.close()

        name = self.distribution.get_fullname()
        extract_dir = os.path.join(distcheck_dir, name)

        old_pwd = os.getcwd()
        os.chdir(extract_dir)
        self.spawn([sys.executable, "setup.py", "test"])
        self.spawn([sys.executable, "setup.py", "build"])
        self.spawn([sys.executable, "setup.py", "build_sphinx"])
        self.spawn([sys.executable, "setup.py", "install",
                    "--root", "../prefix", "--record", "../log.txt"])
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
        self.spawn([
            sys.executable, "-m", "sphinx", "-b", "html", "-n", docs, target])


class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("exitfirst", "x", "stop after first failing test"),
        ("no-quality", None, "skip code quality tests"),
    ]

    def initialize_options(self):
        self.to_run = []
        self.exitfirst = False
        self.no_quality = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.exitfirst = bool(self.exitfirst)
        self.no_quality = bool(self.no_quality)
        if self.no_quality:
            warnings.warn(
                "--no-quality is deprecated and doesn't do anything anymore",
                DeprecationWarning)

    def run(self):
        import tests

        status = tests.unit(self.to_run, self.exitfirst)
        if status != 0:
            raise SystemExit(status)


class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

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
                del sys.modules[key]

        cov = coverage()
        cov.start()

        cmd = self.reinitialize_command("test")
        cmd.ensure_finalized()
        cmd.run()

        dest = os.path.join(os.getcwd(), "coverage")

        cov.stop()
        cov.html_report(
            directory=dest,
            ignore_errors=True,
            include=["mutagen/*"])

        print("Coverage summary: file://%s/index.html" % dest)


if __name__ == "__main__":
    if sys.version_info[0] < 3:
        raise Exception("Python 2 no longer supported")

    # required for PEP 517
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    from mutagen import version

    with open('README.rst', encoding='utf-8') as h:
        long_description = h.read()

    # convert to a setuptools compatible version string
    if version[-1] == -1:
        version_string = ".".join(map(str, version[:-1])) + ".dev0"
    else:
        version_string = ".".join(map(str, version))

    cmd_classes = {
        "clean": clean,
        "test": test_cmd,
        "coverage": coverage_cmd,
        "distcheck": distcheck,
        "build_sphinx": build_sphinx,
        "sdist": sdist,
    }

    setup(cmdclass=cmd_classes,
          name="mutagen",
          version=version_string,
          url="https://github.com/quodlibet/mutagen",
          description="read and write audio tags for many formats",
          author="Christoph Reiter",
          author_email="reiter.christoph@gmail.com",
          license="GPL-2.0-or-later",
          classifiers=[
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            ('License :: OSI Approved :: '
             'GNU General Public License v2 or later (GPLv2+)'),
            'Topic :: Multimedia :: Sound/Audio',
          ],
          packages=[
            "mutagen",
            "mutagen.id3",
            "mutagen.mp4",
            "mutagen.asf",
            "mutagen.mp3",
            "mutagen._tools",
          ],
          package_data={
            "mutagen": ["py.typed"],
          },
          data_files=[
            ('share/man/man1', glob.glob("man/*.1")),
          ],
          python_requires=(
            '>=3.7'),
          entry_points={
            'console_scripts': [
              'mid3cp=mutagen._tools.mid3cp:entry_point',
              'mid3iconv=mutagen._tools.mid3iconv:entry_point',
              'mid3v2=mutagen._tools.mid3v2:entry_point',
              'moggsplit=mutagen._tools.moggsplit:entry_point',
              'mutagen-inspect=mutagen._tools.mutagen_inspect:entry_point',
              'mutagen-pony=mutagen._tools.mutagen_pony:entry_point',
            ],
          },
          long_description=long_description,
    )
