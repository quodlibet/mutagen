# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: apev2.py 2866 2006-02-21 05:59:20Z piman $

"""Utility classes for Mutagen.

You should not rely on the interfaces here being stable. They are
intended for internal use in Mutagen only.
"""

import struct

class DictMixin(object):
    """Implement the dict API using keys() and __*item__ methods.

    Similar to UserDict.DictMixin, this takes a class that defines
    __getitem__, __setitem__, __delitem__, and keys(), and turns it
    into a full dict-like object.

    UserDict.DictMixin is not suitable for this purpose because it's
    an old-style class.

    This class is not optimized for very large dictionaries; many
    functions have linear memory requirements. I recommend you
    override some of these functions if speed is required.
    """

    def __iter__(self):
        return iter(self.keys())

    def has_key(self, key):
        try: self[key]
        except KeyError: return False
        else: return True
    __contains__ = has_key

    iterkeys = lambda s: iter(s.keys())

    def values(self):
        return map(self.__getitem__, self.keys())
    itervalues = lambda s: iter(s.values())

    def items(self):
        return zip(self.keys(), self.values())
    iteritems = lambda s: iter(s.items())

    def clear(self):
        map(self.__delitem__, self.keys())

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop takes at most two arguments")
        try: value = self[key]
        except KeyError:
            if args: return args[0]
            else: raise
        del(self[key])
        return value

    def popitem(self):
        try:
            key = self.keys()[0]
            return key, self.pop(key)
        except IndexError: raise KeyError("dictionary is empty")

    def update(self, other=None, **kwargs):
        if other is None:
            self.update(kwargs)
            other = {}

        try: map(self.__setitem__, other.keys(), other.values())
        except AttributeError:
            for key, value in other:
                self[key] = value

    def setdefault(self, key, default=None):
        try: return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default=None):
        try: return self[key]
        except KeyError: return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __cmp__(self, other):
        if other is None: return 1
        else: return cmp(dict(self.items()), other)

    def __len__(self):
        return len(self.keys())

class BitSet(int):
    """An integer with convenient methods for bit arithmetic.

    Integer operations on a BitSet will return an int.

    Based on the C++ STL bitset type. For more information see
    http://www.cppreference.com/cppbitset/all.html. Methods should be
    implemented as needed.
    """

    def test(self, n):
        """Return true if the nth bit is set."""
        return bool((self >> n) & 1)

class cdata(object):
    """C character buffer to Python numeric type conversions."""

    from struct import error

    int_le = staticmethod(lambda data: struct.unpack('<i', data)[0])
    uint_le = staticmethod(lambda data: struct.unpack('<I', data)[0])

    longlong_le = staticmethod(lambda data: struct.unpack('<q', data)[0])
    ulonglong_le = staticmethod(lambda data: struct.unpack('<Q', data)[0])

    to_uint_le = staticmethod(lambda data: struct.pack('<I', data))
