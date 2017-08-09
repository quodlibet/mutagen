# -*- coding: utf-8 -*-
# Copyright 2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import pytest
import mutagen

from .. import TestCase, capture_output
from .util import setup_cfg

try:
    import pep8 as pycodestyle
except ImportError:
    try:
        import pycodestyle
    except ImportError:
        pycodestyle = None


@pytest.mark.quality
class TPEP8(TestCase):

    def test_all(self):
        paths = [os.path.dirname(os.path.abspath(mutagen.__path__[0]))]

        errors = []
        for path in paths:
            style = pycodestyle.StyleGuide(ignore=setup_cfg.ignore)
            with capture_output() as (o, e):
                style.input_dir(path)
            errors.extend(o.getvalue().splitlines())

        if errors:
            raise Exception("\n".join(errors))
