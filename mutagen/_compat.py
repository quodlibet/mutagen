# -*- coding: utf-8 -*-
# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from io import StringIO
StringIO = StringIO
from io import BytesIO
cBytesIO = BytesIO
from itertools import zip_longest

long_ = int
integer_types = (int,)
string_types = (str,)
text_type = str

izip_longest = zip_longest
izip = zip
xrange = range
cmp = lambda a, b: (a > b) - (a < b)
chr_ = lambda x: bytes([x])


def endswith(text, end):
    # usefull for paths which can be both, str and bytes
    if isinstance(text, str):
        if not isinstance(end, str):
            end = end.decode("ascii")
    else:
        if not isinstance(end, bytes):
            end = end.encode("ascii")
    return text.endswith(end)

iteritems = lambda d: iter(d.items())
itervalues = lambda d: iter(d.values())
iterkeys = lambda d: iter(d.keys())

iterbytes = lambda b: (bytes([v]) for v in b)


def reraise(tp, value, tb):
    raise tp(value).with_traceback(tb)


def swap_to_string(cls):
    return cls

import builtins
builtins
