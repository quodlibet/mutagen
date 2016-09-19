# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

import sys
import ctypes

from ._compat import PY2
from ._fsnative import is_unix
from . import _winapi as winapi


def create_argv():
    """Returns a unicode argv under Windows and standard sys.argv otherwise"""

    if is_unix or not PY2:
        return sys.argv

    argc = ctypes.c_int()
    try:
        argv = winapi.CommandLineToArgvW(
            winapi.GetCommandLineW(), ctypes.byref(argc))
    except WindowsError:
        return []

    if not argv:
        return []

    res = argv[max(0, argc.value - len(sys.argv)):argc.value]

    winapi.LocalFree(argv)

    return res


argv = create_argv()
