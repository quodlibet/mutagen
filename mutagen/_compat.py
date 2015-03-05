# -*- coding: utf-8 -*-

# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os
import sys
import locale


PY2 = sys.version_info[0] == 2
PY3 = not PY2

if PY2:
    from StringIO import StringIO
    BytesIO = StringIO
    from cStringIO import StringIO as cBytesIO

    long_ = long
    integer_types = (int, long)
    string_types = (str, unicode)
    text_type = unicode

    xrange = xrange
    cmp = cmp
    chr_ = chr

    def endswith(text, end):
        return text.endswith(end)

    iteritems = lambda d: d.iteritems()
    itervalues = lambda d: d.itervalues()
    iterkeys = lambda d: d.iterkeys()

    iterbytes = lambda b: iter(b)

    exec("def reraise(tp, value, tb):\n raise tp, value, tb")

    def swap_to_string(cls):
        if "__str__" in cls.__dict__:
            cls.__unicode__ = cls.__str__

        if "__bytes__" in cls.__dict__:
            cls.__str__ = cls.__bytes__

        return cls

elif PY3:
    from io import StringIO
    StringIO = StringIO
    from io import BytesIO
    cBytesIO = BytesIO

    long_ = int
    integer_types = (int,)
    string_types = (str,)
    text_type = str

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


def print_(*objects, **kwargs):
    """A print which supports bytes and str+surrogates under python3.

    Arguments:
        objects: one or more bytes/text
        linesep (bool): whether a line separator should be appended
        sep (bool): whether objects should be printed separated by spaces
    """

    encoding = locale.getpreferredencoding() or "utf-8"
    linesep = kwargs.pop("linesep", True)
    sep = kwargs.pop("sep", True)
    file_ = kwargs.pop("file", sys.stdout)
    if linesep:
        objects = list(objects) + [os.linesep]

    parts = []
    for text in objects:
        if isinstance(text, text_type):
            if PY3:
                text = text.encode(encoding, 'surrogateescape')
            else:
                text = text.encode(encoding, 'replace')
        parts.append(text)

    data = (b" " if sep else b"").join(parts)
    try:
        fileno = file_.fileno()
    except (AttributeError, OSError, ValueError):
        # for tests when stdout is replaced
        try:
            file_.write(data)
        except TypeError:
            file_.write(data.decode(encoding, "replace"))
    else:
        file_.flush()
        os.write(fileno, data)
