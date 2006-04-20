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
"""

__all__ = ["APEv2", "Open", "delete"]

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

class _APEv2Data(object):
    # Store offsets of the important parts of the file.
    start = header = data = footer = end = None
    # Footer or header; seek here and read 32 to get version/size/items/flags
    metadata = None
    # Actual tag data
    tag = None

    version = None
    size = None
    items = None
    flags = 0

    # The tag is at the start rather than the end. A tag at both
    # the start and end of the file (i.e. the tag is the whole file)
    # is not considered to be at the start.
    is_at_start = False

    def __init__(self, fileobj):
        self.__find_metadata(fileobj)
        self.metadata = max(self.header, self.footer)
        if self.metadata is None: return
        self.__fill_missing(fileobj)
        self.__fix_brokenness(fileobj)
        if self.data is not None:
            fileobj.seek(self.data)
            self.tag = fileobj.read(self.size)

    def __find_metadata(self, fileobj):
        # Try to find a header or footer.

        # Check for a simple footer.
        try: fileobj.seek(-32, 2)
        except IOError:
            fileobj.seek(0, 2)
            return
        if fileobj.read(8) == "APETAGEX":
            fileobj.seek(-8, 1)
            self.footer = self.metadata = fileobj.tell()
            return

        # Check for an APEv2 tag followed by an ID3v1 tag at the end.
        try: fileobj.seek(-128, 2)
        except IOError: pass
        else:
            if fileobj.read(3) == "TAG":
                try: fileobj.seek(-35, 1) # "TAG" + header length
                except IOError: pass
                else:
                    if fileobj.read(8) == "APETAGEX":
                        fileobj.seek(-8, 1)
                        self.footer = fileobj.tell()
                        return

        # Check for a tag at the start.
        fileobj.seek(0, 0)
        if fileobj.read(8) == "APETAGEX":
            fileobj.seek(0, 0)
            self.is_at_start = True
            self.header = fileobj.tell()

    def __fill_missing(self, fileobj):
        fileobj.seek(self.metadata)
        if fileobj.read(8) != "APETAGEX":
            raise APENoHeaderError("the header disappeared")

        self.version = fileobj.read(4)
        self.size = _read_int(fileobj.read(4))
        self.items = _read_int(fileobj.read(4))
        self.flags = _read_int(fileobj.read(4))

        if self.header is not None:
            # If we're reading the header, the size is the header
            # offset + the size, which includes the footer.
            self.end = self.header + self.size
            fileobj.seek(self.end - 32, 0)
            if fileobj.read(8) == "APETAGEX":
                self.footer = self.end - 32
            self.data = self.header + 32
        elif self.footer is not None:
            self.end = self.footer + 32
            self.data = self.end - self.size
            if self.flags & HAS_HEADER: self.header = self.data - 32
            else: self.header = self.data
        else: raise APENoHeaderError("No APE tag found")

    def __fix_brokenness(self, fileobj):
        # Fix broken tags written with PyMusepack.
        if self.header is not None: start = self.header
        else: start = self.data
        fileobj.seek(start)

        while start > 0:
            # Clean up broken writing from pre-Mutagen PyMusepack.
            # It didn't remove the first 24 bytes of header.
            try: fileobj.seek(-24, 1)
            except IOError: break
            else:
                if fileobj.read(8) == "APETAGEX":
                    fileobj.seek(-8, 1)
                    start = fileobj.tell()
                else: break
        self.start = start

class APEv2(Metadata):
    """An APEv2 contains the tags in the file. It behaves much like a
    dictionary of key/value pairs, except that the keys must be strings,
    and the values a support APE tag value.

    ID3v1 tags are silently ignored and overwritten."""

    def __init__(self, filename=None):
        self.filename = filename
        if filename: self.load(filename)

    def pprint(self):
        items = self.items()
        items.sort()
        return "\n".join(["%s=%s" % (k, v.pprint()) for k, v in items])

    def load(self, filename):
        """Load tags from the filename."""
        self.filename = filename

        fileobj = file(filename, "rb")
        try: data = _APEv2Data(fileobj)
        except EOFError:
            raise APENoHeaderError("%s: too small (%d bytes)" %(
                filename, os.path.getsize(filename)))
        fileobj.close()
        if data.tag: self.__parse_tag(data.tag, data.items)
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
        data = _APEv2Data(f)

        if data.is_at_start:
            f.close()
            self.delete(filename)
            return self.save(filename)
        elif data.start is not None:
            f.seek(data.start)
            f.truncate()
        else: f.seek(0, 2)

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
        fileobj = file(filename, "ab+")
        data = _APEv2Data(fileobj)
        if data.start is not None and data.size is not None:
            self._delete_bytes(fileobj, data.end - data.start, data.start)

Open = APEv2

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

    def pprint(self): return " / ".join(self)

class APEBinaryValue(_APEValue):
    """Binary values may be converted to a string of bytes. They are
    used for anything not intended to be human-readable."""

    def pprint(self): return "[%d bytes]" % len(self)

class APEExtValue(_APEValue):
    """An external value is a string containing a URI (http://..., file://...)
    that contains the actual value of the tag."""

    def pprint(self): return "[External] %s" % unicode(self)

# The standard doesn't say anything about the byte ordering, but
# based on files tested, it's little-endian.
def _read_int(data): return struct.unpack('<I', data)[0]

def _utf8(data):
    if isinstance(data, str):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, unicode):
        return data.encode("utf-8")
    else: raise TypeError("only unicode/str types can be converted to UTF-8")
