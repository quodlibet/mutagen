# Vorbis comment support for Mutagen
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import struct
from cStringIO import StringIO

"""Read and write Vorbis comment data, used in Ogg Vorbis and FLAC
files. Vorbis comments are Unicode values with a key that is
case-insensitive ASCII between 0x20 and 0x7D inclusive, excluding '=' and '~'.

Specification at http://www.xiph.org/vorbis/doc/v-comment.html."""

def istag(key):
    """Return true if 'key' is a valid Vorbis comment key. This means
    it contains ASCII from 0x20 to 0x7D inclusive, barring '~' and '='."""
    for c in key:
        if c < " " or c > "}" or c == "=": return False
    else: return bool(key)

class VComment(list):
    """Since Vorbis comments are always wrapped in something like an
    Ogg Vorbis bitstream or a FLAC metadata block, this takes
    string data or a file-like object, not a filename.

    This isn't really intended to be used directly. File-specific classes
    should wrap it and put its output in the appropriate places.

    All comment ordering is preserved.

    The default vendor if you make a new tag is 'Mutagen'. Otherwise,
    any vendor tag will be preserved."""

    vendor = u"Mutagen"

    def __init__(self, data=None, errors='replace'):
        if data is not None:
            if isinstance(data, str): data = StringIO(data)
            elif not hasattr(data, 'read'):
                raise TypeError("VComment requires string data or a file-like")
            self.load(data, errors)

    def load(self, data, errors='replace'):
        """Load a file-like object."""

        try:
            vendor_length = struct.unpack("<I", data.read(4))[0]
            self.vendor = data.read(vendor_length).decode('utf-8', errors)
            count = struct.unpack("<I", data.read(4))[0]
            for i in range(count):
                length = struct.unpack("<I", data.read(4))[0]
                string = data.read(length).decode('utf-8', 'replace')
                tag, value = string.split('=', 1)
                try: tag = tag.encode('ascii')
                except UnicodeEncodeError: pass
                else:
                    if istag(tag): self.append((tag, value))
                # "[framing_bit] = read a single bit as boolean". All Ogg
                # Vorbis files I've checked use 0x01. All FLAC files use 0x81.
                # So, what to do? Check both.
            if not ord(data.read(1)) & 0x81:
                raise IOError("framing bit was unset")
        except (struct.error, TypeError):
            raise IOError("data is not a valid Vorbis comment")

    def validate(self):
        """Validate keys and values, raising a ValueError if there
        are any problems."""

        if not isinstance(self.vendor, unicode):
            try: self.vendor.decode('utf-8')
            except UnicodeDecodeError: raise ValueError

        for key, value in self:
            try:
                if not istag(key): raise ValueError
            except: raise ValueError("%r is not a valid key" % key)
            if not isinstance(value, unicode):
                try: value.encode("utf-8")
                except: raise ValueError("%r is not a valid value" % value)
        else: return True

    def write(self):
        """Return a string encoding the comment data. Validation is
        always done before writing."""
        assert self.validate()

        f = StringIO()
        f.write(struct.pack("<I", len(self.vendor.encode('utf-8'))))
        f.write(self.vendor.encode('utf-8'))
        f.write(struct.pack("<I", len(self)))
        for tag, value in self:
            comment = "%s=%s" % (tag, value.encode('utf-8'))
            f.write(struct.pack("<I", len(comment)))
            f.write(comment)
        f.write("\x81")
        return f.getvalue()

class VCommentDict(VComment):
    """Wrap a VComment in a way that looks a bit like a dictionary.
    The weakness of this method is that inter-key ordering can
    be lost.

    Note that most of these operations happen in linear time on
    the number of values (not keys), and are not optimized."""

    def __getitem__(self, key):
        """Return a ''copy'' of the values for this key.
        comment['title'].append('a title') will not work."""

        key = key.lower()
        values = [value for (k, value) in self if k == key]
        if not values: raise KeyError, key
        else: return values

    def __delitem__(self, key):
        key = key.lower()
        to_delete = filter(lambda x: x[0] == key, self)
        if not to_delete: raise KeyError, key
        else: map(self.remove, to_delete)

    def __contains__(self, key):
        key = key.lower()
        for k, value in self:
            if k == key: return True
        else: return False

    def __setitem__(self, key, values):
        """Setting a value overwrites all old ones. The value give may be
        a UTF-8 string, a unicode object, or a list of either."""
        key = key.lower()
        if not isinstance(values, list): values = [values]
        try: del(self[key])
        except KeyError: pass
        for value in values: self.append((key, value))
