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

This module does not support 64 bit atom sizes, and so will not
work on files over 4GB.
"""

import struct
import sys

from cStringIO import StringIO

from mutagen import FileType, Metadata
from mutagen._constants import GENRES
from mutagen._util import cdata, DictMixin

class error(IOError): pass
class M4AMetadataError(error): pass
class M4AStreamInfoError(error): pass

# This is not an exhaustive list of container atoms, but just the
# ones this module needs to peek inside.
_CONTAINERS = ["moov", "udta", "trak", "mdia", "meta", "ilst"]
_SKIP_SIZE = { "meta": 4 }

class Atom(DictMixin):
    def __init__(self, fileobj):
        self.offset = fileobj.tell()
        self.length, self.name = struct.unpack(">I4s", fileobj.read(8))
        if self.length == 1:
            raise error("64 bit atom sizes are not supported")
        elif self.length == 0:
            return
        self.children = None

        if self.name in _CONTAINERS:
            self.children = []
            fileobj.seek(_SKIP_SIZE.get(self.name, 0), 1)
            while fileobj.tell() < self.offset + self.length:
                self.children.append(Atom(fileobj))
        else:
            fileobj.seek(self.offset + self.length, 0)

    def render(name, data):
        """Render raw atom data."""
        return struct.pack(">I4s", len(data) + 8, name) + data
    render = staticmethod(render)

    def __getitem__(self, remaining):
        if not remaining:
            return self
        elif self.children is None:
            raise KeyError("atom is not a container")
        for child in self.children:
            if child.name == remaining[0]:
                return child[remaining[1:]]
        else:
            raise KeyError, "%s not found" % remaining[0]

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
            return "<%s name=%r length=%r offset=%r\n%s>" % (
                klass, self.name, self.length, self.offset, children)

class Atoms(DictMixin):
    def __init__(self, fileobj):
        self.atoms = []
        fileobj.seek(0, 2)
        end = fileobj.tell()
        fileobj.seek(0)
        while fileobj.tell() < end:
            self.atoms.append(Atom(fileobj))

    def path(self, *names):
        path = [self]
        for name in names:
            path.append(path[-1][name,])
        return path[1:]

    def __getitem__(self, names):
        if isinstance(names, basestring):
            names = names.split(".")
        for child in self.atoms:
            if child.name == names[0]:
                return child[names[1:]]
        else:
            raise KeyError, "%s not found" % names[0]

    def keys(self):
        return sum([atom.keys() for atom in self.atoms], [])

    def __repr__(self):
        return "\n".join(repr(child) for child in self.atoms)

class M4ATags(Metadata):
    """Dictionary containing Apple iTunes metadata list key/values.

    Keys are four byte identifiers, except for freeform ('----')
    keys. Values are usually unicode strings, but some atoms have a
    special structure:
        cpil -- boolean
        trkn, disk -- tuple of 16 bit ints (current, total)
        tmpo -- 16 bit int
        covr -- raw str data
        gnre -- not supported. Use '\\xa9gen' instead.

    The freeform '----' frames use a key in the format '----:mean:name'
    where 'mean' is usually 'com.apple.iTunes' and 'name' is a unique
    identifier for this frame. The value is a str, but is probably
    text that can be decoded as UTF-8.
    """

    def __init__(self, atoms, fileobj):
        if atoms is None and fileobj is None:
            return
        try: ilst = atoms["moov.udta.meta.ilst"]
        except KeyError, key:
            raise M4AMetadataError(key)
        for atom in ilst.children:
            fileobj.seek(atom.offset + 8)
            data = fileobj.read(atom.length - 8)
            parse = self.atoms.get(atom.name, (M4ATags.__parse_text,))[0]
            parse(self, atom, data)

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        # Render all the current data
        values = []
        for key, value in self.iteritems():
            render = self.atoms.get(key[:4], (None, M4ATags.__render_text))[1]
            values.append(render(self, key, value))
        data = Atom.render("ilst", "".join(values))

        # Find the old atoms.
        fileobj = file(filename, "rb+")
        atoms = Atoms(fileobj)
        path = atoms.path("moov", "udta", "meta", "ilst")
        ilst = path.pop()

        # Replace the old ilst atom.
        delta = len(data) - ilst.length
        fileobj.seek(ilst.offset)
        if delta > 0:
            self._insert_space(fileobj, delta, ilst.offset)
        elif delta < 0:
            self._delete_bytes(fileobj, -delta, ilst.offset)
        fileobj.seek(ilst.offset)
        fileobj.write(data)

        # Update all parent atoms with the new size.
        for atom in path:
            fileobj.seek(atom.offset)
            size = cdata.uint_be(fileobj.read(4)) + delta
            fileobj.seek(atom.offset)
            fileobj.write(cdata.to_uint_be(size))
        fileobj.close()

    def __render_data(self, key, flags, data):
        data = struct.pack(">2I", flags, 0) + data
        return Atom.render(key, Atom.render("data", data))

    def __parse_freeform(self, atom, data):
        try:
            fileobj = StringIO(data)
            mean_length = cdata.uint_be(fileobj.read(4))
            # skip over 8 bytes of atom name, flags
            mean = fileobj.read(mean_length - 4)[8:]
            name_length = cdata.uint_be(fileobj.read(4))
            name = fileobj.read(name_length - 4)[8:]
            value_length = cdata.uint_be(fileobj.read(4))
            # Name, flags, and reserved bytes
            value = fileobj.read(value_length - 4)[12:]
        except struct.error:
            # Some ---- atoms have no data atom, I have no clue why
            # they actually end up in the file.
            pass
        else:
            self["%s:%s:%s" % (atom.name, mean, name)] = value
    def __render_freeform(self, key, value):
        dummy, mean, name = key.split(":", 2)
        mean = struct.pack(">I4sI", len(mean) + 12, "mean", 0) + mean
        name = struct.pack(">I4sI", len(name) + 12, "name", 0) + name
        value = struct.pack(">I4s2I", len(value) + 16, "data", 0x1, 0) + value
        final = mean + name + value
        return Atom.render("----", mean + name + value)

    def __parse_pair(self, atom, data):
        self[atom.name] = struct.unpack(">2H", data[18:22])
    def __render_pair(self, key, value):
        track, total = value
        data = struct.pack(">4H", 0, track, total, 0)
        return self.__render_data(key, 0, data)

    def __parse_genre(self, atom, data):
        # Translate to a freeform genre.
        genre = cdata.short_be(data[16:18])
        if "\xa9gen" not in self:
            try: self["\xa9gen"] = GENRES[genre - 1]
            except IndexError: pass

    def __parse_tempo(self, atom, data):
        self[atom.name] = cdata.short_be(data[16:18])
    def __render_tempo(self, key, value):
        return self.__render_data(key, 0x15, cdata.to_ushort_be(value))

    def __parse_compilation(self, atom, data):
        try: self[atom.name] = bool(ord(data[16:17]))
        except TypeError: self[atom.name] = False
    def __render_compilation(self, key, value):
        if value:            
            return self.__render_data(key, 0x15, "\x01")
        else: return ""

    def __parse_cover(self, atom, data):
        self[atom.name] = data[16:]
    def __render_cover(self, key, value):
        return self.__render_data(key, 0xD, value)

    def __parse_text(self, atom, data):
        self[atom.name] = data[16:].decode('utf-8', 'replace')
    def __render_text(self, key, value):
        return self.__render_data(key, 0x1, value.encode('utf-8'))

    atoms = {
        "----": (__parse_freeform, __render_freeform),
        "trkn": (__parse_pair, __render_pair),
        "disk": (__parse_pair, __render_pair),
        "gnre": (__parse_genre, None),
        "tmpo": (__parse_tempo, __render_tempo),
        "cpil": (__parse_compilation, __render_compilation),
        "covr": (__parse_cover, __render_cover),
        }

    def pprint(self):
        return "\n".join(["%s=%s" % (key.decode('latin1'), value)
                          for (key, value) in self.iteritems()])

class M4AInfo(object):
    def __init__(self, atoms, fileobj):
        atom = atoms["moov.trak.mdia.mdhd"]
        fileobj.seek(atom.offset)
        data = fileobj.read(atom.length)
        if ord(data[9]) == 0:
            offset = 20
            format = ">2I"
        else:
            offset = 28
            format = ">IQ"
        end = offset + struct.calcsize(format)
        unit, length = struct.unpack(format, data[offset:end])
        self.length = float(length) / unit

    def pprint(self):
        return "MPEG-4 audio, %.2f seconds" % (self.length)

class M4A(FileType):
    """An MPEG-4 audio file, probably containing AAC."""

    def __init__(self, filename):
        self.filename = filename
        fileobj = file(filename, "rb")
        atoms = Atoms(fileobj)
        try: self.info = M4AInfo(atoms, fileobj)
        except StandardError, err:
            raise M4AStreamInfoError, err, sys.exc_info()[2]
        try: self.tags = M4ATags(atoms, fileobj)
        except M4AMetadataError:
            self.tags = None
        except StandardError, err:
            raise M4AMetadataError, err, sys.exc_info()[2]

    def add_tags(self):
        self.tags = M4ATags(None, None)

    def score(filename, fileobj, header):
        return ("ftyp" in header) + ("mp4" in header)
    score = staticmethod(score)
