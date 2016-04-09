# -*- coding: utf-8 -*-
# Copyright 2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import glob
import subprocess

from tests import TestCase

PEP8_NAME = "pep8"

has_pep8 = True
try:
    subprocess.check_output([PEP8_NAME, "--version"], stderr=subprocess.STDOUT)
except OSError:
    has_pep8 = False


class TPEP8(TestCase):
    IGNORE = ["E12", "W601", "E402", "E731", "E211"]

    def _run(self, path, ignore=None):
        if ignore is None:
            ignore = []
        ignore += self.IGNORE

        p = subprocess.Popen(
            [PEP8_NAME, "--ignore=" + ",".join(ignore), path],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        class Future(object):

            def __init__(self, p):
                self.p = p

            def result(self):
                if self.p.wait() != 0:
                    return self.p.communicate()

        return Future(p)

    def _run_package(self, mod, ignore=None):
        path = mod.__path__[0]
        files = glob.glob(os.path.join(path, "*.py"))
        assert files
        futures = []
        for file_ in files:
            futures.append(self._run(file_, ignore))

        errors = []
        for future in futures:
            status = future.result()
            if status is not None:
                errors.append(status[0].decode("utf-8"))

        if errors:
            raise Exception("\n".join(errors))

    def test_main_package(self):
        import mutagen
        self._run_package(mutagen)

    def test_id3_package(self):
        import mutagen.id3
        self._run_package(mutagen.id3)

    def test_tests(self):
        import tests
        self._run_package(tests)


if not has_pep8:
    del TPEP8
