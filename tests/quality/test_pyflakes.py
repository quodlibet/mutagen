# -*- coding: utf-8 -*-
# Copyright 2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

import pytest
from mutagen._compat import StringIO

from .. import TestCase
from .util import setup_cfg

os.environ["PYFLAKES_NODOCTEST"] = "1"
os.environ["PYFLAKES_BUILTINS"] = ",".join(setup_cfg.builtins)

try:
    from pyflakes.scripts import pyflakes
except ImportError:
    pyflakes = None


@pytest.mark.quality
class TPyFlakes(TestCase):

    def _run(self, path):
        old_stdout = sys.stdout
        stream = StringIO()
        try:
            sys.stdout = stream
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.py'):
                        pyflakes.checkPath(os.path.join(dirpath, filename))
        finally:
            sys.stdout = old_stdout
        lines = stream.getvalue()
        if lines:
            raise Exception(lines)

    def _run_package(self, mod):
        path = mod.__path__[0]
        self._run(path)

    def test_main(self):
        import mutagen
        self._run_package(mutagen)

    def test_tests(self):
        import tests
        self._run_package(tests)
