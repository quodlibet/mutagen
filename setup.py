#!/usr/bin/env python
# Copyright 2005-2009,2011 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
import sys
import subprocess
import tarfile

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


class distcheck(distutils_sdist):

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
        distutils_sdist.run(self)
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


if __name__ == "__main__":
    if sys.version_info[0] < 3:
        raise Exception("Python 2 no longer supported")

    # required for PEP 517
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    from mutagen import version

    # convert to a setuptools compatible version string
    if version[-1] == -1:
        version_string = ".".join(map(str, version[:-1])) + ".dev0"
    else:
        version_string = ".".join(map(str, version))

    cmd_classes = {
        "clean": clean,
        "distcheck": distcheck,
        "build_sphinx": build_sphinx,
    }

    setup(cmdclass=cmd_classes,
          version=version_string,
    )
