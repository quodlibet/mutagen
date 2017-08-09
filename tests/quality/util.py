# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from collections import namedtuple
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import mutagen


SetupConfig = namedtuple("SetupConfig", ["ignore", "builtins", "exclude"])


def parse_setup_cfg():
    """Parses the flake8 config from the setup.cfg file in the root dir

    Returns:
        SetupConfig
    """

    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(mutagen.__file__)))

    cfg = os.path.join(base_dir, "setup.cfg")
    config = configparser.RawConfigParser()
    config.read(cfg)

    ignore = str(config.get("flake8", "ignore")).split(",")
    builtins = str(config.get("flake8", "builtins")).split(",")
    exclude = str(config.get("flake8", "exclude")).split(",")
    exclude = [
        os.path.join(base_dir, e.replace("/", os.sep)) for e in exclude]

    return SetupConfig(ignore, builtins, exclude)


setup_cfg = parse_setup_cfg()
