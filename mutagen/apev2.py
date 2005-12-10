# An APEv2 tag reader
#
# Copyright 2005 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

# Based off the documentation found at
# http://wiki.hydrogenaudio.org/index.php?title=APEv2_specification
# which is in turn a copy of the old
# http://www.personal.uni-jena.de/~pfk/mpp/sv8/apetag.html

"""This module reads and writes APEv2 metadata tags, the kind
usually found in Musepack files. For more information, see
http://wiki.hydrogenaudio.org/index.php?title=APEv2_specification

It does not support APE tags at the start of a file, only at the end."""

import os, struct
from cStringIO import StringIO

# There are three different kinds of APE tag values.
# "0: Item contains text information coded in UTF-8
#  1: Item contains binary information
#  2: Item is a locator of external stored information [e.g. URL]
#  3: reserved"
TEXT, BINARY, EXTERNAL = range(3)

HAS_HEADER = 1 << 31L
HAS_FOOTER = 1 << 30
IS_HEADER  = 1 << 29

class error(IOError): pass
class APENoHeaderError(error, ValueError): pass
class APEUnsupportedVersionError(error, ValueError): pass
class APEBadItemError(error, ValueError): pass

from mutagen import Metadata

class APEv2(Metadata):
    """An APEv2 contains the tags in the file. It behaves much like a
    dictionary of key/value pairs, except that the keys must be strings,
    and the values a support APE tag value."""
    def __init__(self, filename=None):
        self.filename = filename
        if filename: self.load(filename)

    def load(self, filename):
        """Load tags from the filename."""
        self.filename = filename

        fileobj = file(filename, "rb")
        try:
            tag, count = self.__find_tag(fileobj)
        except EOFError:
            raise APENoHeaderError("%s: too small (%d bytes)" %(
                filename, os.path.getsize(filename)))

        fileobj.close()
        if tag: self.__parse_tag(tag, count)
        else: raise APENoHeaderError("No APE tag found")

    def __parse_tag(self, tag, count):
        f = StringIO(tag)

        for i in range(count):
            size = _read_int(f.read(4))
            flags = _read_int(f.read(4))

            # Bits 1 and 2 bits are flags, 0-3
            # Bit 0 is read/write flag, ignored
            kind = (flags & 6) >> 1
            if kind == 3:
                raise APEBadItemError("value type must be 0, 1, or 2")
            key = ""
            while key[-1:] != '\0': key += f.read(1)
            key = key[:-1]
            value = f.read(size)
            self[key] = APEValue(value, kind)

    def __tag_start(self, f):
        try: f.seek(-32, 2)
        except IOError: f.seek(0, 0)
        if f.read(8) == "APETAGEX":
            f.read(4) # version
            tag_size = _read_int(f.read(4))
            f.seek(-(tag_size + 32), 2) # start of header
            value = f.tell()

            while value > 0:
                # Clean up broken writing from pre-Mutagen PyMusepack.
                # It didn't remove the first 24 bytes of header.
                try: f.seek(-24, 1)
                except IOError: return value
                else:
                    if f.read(8) == "APETAGEX":
                        value = f.tell() - 8
                        f.seek(-8, 1)
                    else: return value
            else: return value
        else:
            f.seek(0, 2)
            return f.tell()

    # 32 bytes header/footer; they should be identical except
    # for the IS_HEADER bit.
    # 4B: Int tag version (== 2000, 2.000)
    # 4B: Tag size including footer, not including header
    # 4B: Item count
    # 4B: Global flags; the important part is the IS_HEADER flag.

    # "An APE tag at the end of a file (strongly recommended) must have at
    # least a footer, a APE tag in the beginning of a file (strongly
    # unrcommneded) must have at least a header."
    # This module only supports tags at the end.

    def __find_tag(self, f):
        try: f.seek(-32, 2)
        except IOError: return None, 0
        data = f.read(32)
        if data.startswith("APETAGEX"):
            # 4 byte version
            version = _read_int(data[8:12])
            if version < 2000 or version >= 3000:
                raise APEUnsupportedVersionError(
                    "module only supports APEv2 (2000-2999), has %d" % version)

            # 4 byte tag size
            tag_size = _read_int(data[12:16])

            # 4 byte item count
            item_count = _read_int(data[16:20])

            # 4 byte flags
            flags = _read_int(data[20:24])
            if flags & IS_HEADER:
                raise APENoHeaderError("Found header at end of file")

            f.seek(-tag_size, 2)
            # tag size includes footer
            return f.read(tag_size - 32), item_count
        else:
            f.seek(0, 0)
            if f.read(8) == "APETAGEX":
                raise APENoHeaderError(
                    "APEv2 at start of file is not (yet) supported")
            return None, 0

    def __contains__(self, k):
        return super(APEv2, self).__contains__(APEKey(k))
    def __getitem__(self, k):
        return super(APEv2, self).__getitem__(APEKey(k))
    def __delitem__(self, k):
        return super(APEv2, self).__delitem__(APEKey(k))
    def __setitem__(self, k, v):
        """This function tries (and usually succeeds) to guess at what
        kind of value you want to store. If you pass in a valid UTF-8
        or Unicode string, it treats it as a text value. If you pass
        in a list, it treats it as a list of string/Unicode values.
        If you pass in a string that is not valid UTF-8, it assumes
        it is a binary value."""
        if not isinstance(v, _APEValue):
            # let's guess at the content if we're not already a value...
            if isinstance(v, unicode):
                # unicode? we've got to be text.
                v = APEValue(_utf8(v), TEXT)
            elif isinstance(v, list):
                # list? text.
                v = APEValue("\0".join(map(_utf8, v)), TEXT)
            else:
                try: dummy = k.decode("utf-8")
                except UnicodeError:
                    # invalid UTF8 text, probably binary
                    v = APEValue(v, BINARY)
                else:
                    # valid UTF8, probably text
                    v = APEValue(v, TEXT)
        super(APEv2, self).__setitem__(APEKey(k), v)

    def save(self, filename=None):
        """Saves any changes you've made to the file, or to a different
        file if you specify one. Any existing tag will be removed.

        Tags are always written at the end of the file, and include
        a header and a footer."""
        filename = filename or self.filename
        f = file(filename, "ab+")
        offset = self.__tag_start(f)

        f.seek(offset, 0)
        f.truncate()

        # "APE tags items should be sorted ascending by size... This is
        # not a MUST, but STRONGLY recommended. Actually the items should
        # be sorted by importance/byte, but this is not feasible."
        tags = [v._internal(k) for k, v in self.items()]
        tags.sort(lambda a, b: cmp(len(a), len(b)))
        num_tags = len(tags)
        tags = "".join(tags)

        header = "APETAGEX%s%s" %(
            # version, tag size, item count, flags
            struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                        HAS_HEADER | HAS_FOOTER | IS_HEADER),
            "\0" * 8)
        f.write(header)

        f.write(tags)

        footer = "APETAGEX%s%s" %(
            # version, tag size, item count, flags
            struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                        HAS_HEADER | HAS_FOOTER),
            "\0" * 8)
        f.write(footer)
        f.close()

    def delete(self, filename=None):
        """Remove tags from a file."""
        filename = filename or self.filename
        f = file(filename, "ab+")
        offset = self.__tag_start(f)
        f.seek(offset, 0)
        f.truncate()
        f.close()

def delete(filename):
    """Remove tags from a file."""
    try: APEv2(filename).delete()
    except APENoHeaderError: pass

class APEKey(str):
    """An APE key is an ASCII string of length 2 to 255. The specification's
    case rules are silly, so this object is case-preserving but not
    case-sensitive, i.e. "album" == "Album"."""

    # "APE Tags Item Key are case sensitive. Nevertheless it is forbidden
    # to use APE Tags Item Key which only differs in case. And nevertheless
    # Tag readers are recommended to be case insensitive."

    def __cmp__(self, o):
        return cmp(str(self).lower(), str(o).lower())
    
    def __eq__(self, o):
        return str(self).lower() == str(o).lower()
    
    def __hash__(self):
        return str.__hash__(self.lower())

    def __repr__(self): return "%s(%r)" % (type(self), str(self))

def APEValue(value, kind):
    """It is not recommended you construct APE values manually; instead
    use APEv2's __setitem__."""
    if kind == TEXT: return APETextValue(value, kind)
    elif kind == BINARY: return APEBinaryValue(value, kind)
    elif kind == EXTERNAL: return APEExtValue(value, kind)
    else: raise ValueError("kind must be TEXT, BINARY, or EXTERNAL")

class _APEValue(object):
    def __init__(self, value, kind):
        self.kind = kind
        self.value = value

    def __len__(self): return len(self.value)
    def __str__(self): return self.value

    # Packed format for an item:
    # 4B: Value length
    # 4B: Value type
    # Key name
    # 1B: Null
    # Key value
    def _internal(self, key):
        return "%s%s\0%s" %(
            struct.pack("<2I", len(self.value), self.kind << 1),
            key, self.value)

    def __repr__(self):
        return "%s(%r, %d)" % (type(self).__name__, self.value, self.kind)

class APETextValue(_APEValue):
    """APE text values are Unicode/UTF-8 strings. They can be accessed
    like strings (with a null seperating the values), or arrays of strings."""
    def __unicode__(self):
        return unicode(str(self), "utf-8")

    def __iter__(self):
        """Iterating over an APETextValue will iterate over the Unicode
        strings, not the characters in the string."""
        return iter(unicode(self).split("\0"))

    def __getitem__(self, i):
        return unicode(self).split("\0")[i]

    def __len__(self): return self.value.count("\0") + 1

    def __cmp__(self, other):
        return cmp(unicode(self), other)

    def __setitem__(self, i, v):
        l = list(self)
        l[i] = v.encode("utf-8")
        self.value = "\0".join(l).encode("utf-8")

class APEBinaryValue(_APEValue):
    """Binary values may be converted to a string of bytes. They are
    used for anything not intended to be human-readable."""

class APEExtValue(_APEValue):
    """An external value is a string containing a URI (http://..., file://...)
    that contains the actual value of the tag."""

# The standard doesn't say anything about the byte ordering, but
# based on files tested, it's little-endian.
def _read_int(data): return struct.unpack('<I', data)[0]

def _utf8(data):
    if isinstance(data, str):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, unicode):
        return data.encode("utf-8")
    else: raise TypeError("only unicode/str types can be converted to UTF-8")
