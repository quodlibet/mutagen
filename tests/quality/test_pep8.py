# -*- coding: utf-8 -*-
# Copyright 2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess

import pytest

import mutagen
import tests
from tests import TestCase


@pytest.mark.quality
class TPEP8(TestCase):
    IGNORE = ["E128", "W601", "E402", "E731", "W503", "E741", "E305"]

    def _run(self, path, ignore=None):
        if ignore is None:
            ignore = []
        ignore += self.IGNORE

        p = subprocess.Popen(
            ["pep8", "--ignore=" + ",".join(ignore), path],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        class Future(object):

            def __init__(self, p):
                self.p = p

            def result(self):
                result = self.p.communicate()
                if self.p.returncode != 0:
                    return result

        return Future(p)

    def test_all(self):
        paths = [mutagen.__path__[0], tests.__path__[0]]

        futures = []
        for path in paths:
            assert os.path.exists(path)
            futures.append(self._run(path))

        errors = []
        for future in futures:
            status = future.result()
            if status is not None:
                errors.append(status[0].decode("utf-8"))

        if errors:
            raise Exception("\n".join(errors))
