# Copyright 2006 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: apev2.py 2866 2006-02-21 05:59:20Z piman $

class DictMixin(object):
    """Similar to UserDict.DictMixin, this takes a class that defines
    __getitem__, __setitem__, __delitem__, and keys(), and turns it into
    a full(er) dictionary-like object.

    UserDict.DictMixin is not suitable for this purpose because it's an
    old-style class.

    This class is not optimized for very large dictionaries; many
    functions have linear memory requirements.
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

    def update(self, other):
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
