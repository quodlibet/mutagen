# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

"""Read and write M4A files.

This module will read MPEG-4 audio information and metadata,
as found in Apple's M4A (aka MP4, M4B, M4P) files.

There is no official specification for this format. The source code
for TagLib, FAAD, and various MPEG specifications at
http://developer.apple.com/documentation/QuickTime/QTFF/,
http://www.geocities.com/xhelmboyx/quicktime/formats/mp4-layout.txt,
and http://wiki.multimedia.cx/index.php?title=Apple_QuickTime were all
consulted.
"""

import struct

from mutagen import FileType, Metadata
from mutagen._util import cdata, DictMixin

class error(IOError): pass
class M4AMetadataError(error): pass
class M4AStreamInfoError(error): pass

_CONTAINERS = ["moov", "udta", "trak", "mdia", "minf", "dinf",
               "stbl", "meta", "ilst"]
_SKIP_SIZE = { "meta": 4 }

class Atom(DictMixin):
    def __init__(self, fileobj):
        self.offset = fileobj.tell()
        self.length, self.name = struct.unpack(">I4s", fileobj.read(8))
        if self.length == 1:
            raise error("64 bit atom sizes are not supported")
        self.children = None

        if self.name in _CONTAINERS:
            self.children = []
            fileobj.seek(_SKIP_SIZE.get(self.name, 0), 1)
            while fileobj.tell() < self.offset + self.length:
                self.children.append(Atom(fileobj))
        else:
            fileobj.seek(self.offset + self.length, 0)

    def __getitem__(self, remaining):
        if not remaining:
            return self
        elif self.children is None:
            raise KeyError("atom is not a container")
        for child in self.children:
            if child.name == remaining[0]:
                return child[remaining[1:]]
        else:
            raise KeyError("unable to resolve %r" % remaining)

    def keys(self):
        if not self.children:
            return []
        else:
            keys = []
            for child in self.children:
                if child.children is None:
                    keys.append((child.name,))
                else:
                    keys.extend(child.keys())
            return map((self.name,).__add__, keys)

    def __repr__(self):
        klass = self.__class__.__name__
        if self.children is None:
            return "<%s name=%r length=%r offset=%r>" % (
                klass, self.name, self.length, self.offset)
        else:
            children = "\n".join([" " + line for child in self.children
                                  for line in repr(child).splitlines()])
            return "<%s name=%s length=%r offset=%r\n%s>" % (
                klass, self.name, self.length, self.offset, children)

class Atoms(DictMixin):
    def __init__(self, fileobj):
        self.atoms = []
        fileobj.seek(0, 2)
        end = fileobj.tell()
        fileobj.seek(0)
        while fileobj.tell() < end:
            self.atoms.append(Atom(fileobj))

    def __getitem__(self, names):
        if isinstance(names, basestring):
            names = names.split(".")
        for child in self.atoms:
            if child.name == names[0]:
                return child[names[1:]]
        else:
            raise KeyError("unable to resolve %r" % names[0])

    def keys(self):
        return sum([atom.keys() for atom in self.atoms], [])

    def __repr__(self):
        return "\n".join(repr(child) for child in self.atoms)

class M4ATags(Metadata):
    def __init__(self, fileobj):
        pass

class M4AInfo(object):
    def __init__(self, fileobj):
        pass

    def pprint(self):
        return "MPEG-4 AAC"

class M4A(FileType):
    def __init__(self, filename):
        self.filename = filename
        fileobj = file(filename, "rb")
        self.info = M4AInfo(fileobj)
        self.tags = M4ATags(fileobj)

    def score(filename, fileobj, header):
        return ("ftyp" in header + "mp4" in header)
    score = staticmethod(score)
