# -*- coding: utf-8 -*-
# Copyright 2020 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import mutagen

import pytest

try:
    from flake8.api import legacy as flake8
except ImportError:
    flake8 = None

from .. import TestCase, capture_output


@pytest.mark.quality
class TFlake8(TestCase):

    def test_all(self):
        assert flake8 is not None, "flake8 is missing"
        style_guide = flake8.get_style_guide()
        root = os.path.dirname(mutagen.__path__[0])
        root = os.path.relpath(root, os.getcwd())
        with capture_output() as (o, e):
            style_guide.check_files([root])
        errors = o.getvalue().splitlines()
        if errors:
            raise Exception("\n" + "\n".join(errors))
