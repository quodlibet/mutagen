# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Utility classes for Mutagen.

You should not rely on the interfaces here being stable. They are
intended for internal use in Mutagen only.
"""

import struct
import codecs

from fnmatch import fnmatchcase

from ._compat import chr_, text_type, PY2, iteritems, iterbytes


def total_ordering(cls):
    assert hasattr(cls, "__eq__")
    assert hasattr(cls, "__lt__")

    cls.__le__ = lambda self, other: self == other or self < other
    cls.__gt__ = lambda self, other: not (self == other or self < other)
    cls.__ge__ = lambda self, other: not self < other
    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


@total_ordering
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

    def __has_key(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    if PY2:
        has_key = __has_key

    __contains__ = __has_key

    iterkeys = lambda self: iter(self.keys())

    def values(self):
        return [self[k] for k in self.keys()]

    itervalues = lambda self: iter(self.values())

    def items(self):
        return list(zip(self.keys(), self.values()))

    iteritems = lambda s: iter(s.items())

    def clear(self):
        for key in list(self.keys()):
            self.__delitem__(key)

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop takes at most two arguments")
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            else:
                raise
        del(self[key])
        return value

    def popitem(self):
        for key in self.keys():
            break
        else:
            raise KeyError("dictionary is empty")
        return key, self.pop(key)

    def update(self, other=None, **kwargs):
        if other is None:
            self.update(kwargs)
            other = {}

        try:
            for key, value in other.items():
                self.__setitem__(key, value)
        except AttributeError:
            for key, value in other:
                self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __eq__(self, other):
        return dict(self.items()) == other

    def __lt__(self, other):
        return dict(self.items()) < other

    __hash__ = object.__hash__

    def __len__(self):
        return len(self.keys())


class DictProxy(DictMixin):
    def __init__(self, *args, **kwargs):
        self.__dict = {}
        super(DictProxy, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, value):
        self.__dict[key] = value

    def __delitem__(self, key):
        del(self.__dict[key])

    def keys(self):
        return self.__dict.keys()


class cdata(object):
    """C character buffer to Python numeric type conversions."""

    from struct import error
    error = error

    short_le = staticmethod(lambda data: struct.unpack('<h', data)[0])
    ushort_le = staticmethod(lambda data: struct.unpack('<H', data)[0])

    short_be = staticmethod(lambda data: struct.unpack('>h', data)[0])
    ushort_be = staticmethod(lambda data: struct.unpack('>H', data)[0])

    int_le = staticmethod(lambda data: struct.unpack('<i', data)[0])
    uint_le = staticmethod(lambda data: struct.unpack('<I', data)[0])

    int_be = staticmethod(lambda data: struct.unpack('>i', data)[0])
    uint_be = staticmethod(lambda data: struct.unpack('>I', data)[0])

    longlong_le = staticmethod(lambda data: struct.unpack('<q', data)[0])
    ulonglong_le = staticmethod(lambda data: struct.unpack('<Q', data)[0])

    longlong_be = staticmethod(lambda data: struct.unpack('>q', data)[0])
    ulonglong_be = staticmethod(lambda data: struct.unpack('>Q', data)[0])

    to_short_le = staticmethod(lambda data: struct.pack('<h', data))
    to_ushort_le = staticmethod(lambda data: struct.pack('<H', data))

    to_short_be = staticmethod(lambda data: struct.pack('>h', data))
    to_ushort_be = staticmethod(lambda data: struct.pack('>H', data))

    to_int_le = staticmethod(lambda data: struct.pack('<i', data))
    to_uint_le = staticmethod(lambda data: struct.pack('<I', data))

    to_int_be = staticmethod(lambda data: struct.pack('>i', data))
    to_uint_be = staticmethod(lambda data: struct.pack('>I', data))

    to_longlong_le = staticmethod(lambda data: struct.pack('<q', data))
    to_ulonglong_le = staticmethod(lambda data: struct.pack('<Q', data))

    to_longlong_be = staticmethod(lambda data: struct.pack('>q', data))
    to_ulonglong_be = staticmethod(lambda data: struct.pack('>Q', data))

    bitswap = b''.join([chr_(sum([((val >> i) & 1) << (7-i)
                        for i in range(8)]))
                        for val in range(256)])

    try:
        del(i)
        del(val)
    except NameError:
        pass

    test_bit = staticmethod(lambda value, n: bool((value >> n) & 1))


def lock(fileobj):
    """Lock a file object 'safely'.

    That means a failure to lock because the platform doesn't
    support fcntl or filesystem locks is not considered a
    failure. This call does block.

    Returns whether or not the lock was successful, or
    raises an exception in more extreme circumstances (full
    lock table, invalid file).
    """

    try:
        import fcntl
    except ImportError:
        return False
    else:
        try:
            fcntl.lockf(fileobj, fcntl.LOCK_EX)
        except IOError:
            # FIXME: There's possibly a lot of complicated
            # logic that needs to go here in case the IOError
            # is EACCES or EAGAIN.
            return False
        else:
            return True


def unlock(fileobj):
    """Unlock a file object.

    Don't call this on a file object unless a call to lock()
    returned true.
    """

    # If this fails there's a mismatched lock/unlock pair,
    # so we definitely don't want to ignore errors.
    import fcntl
    fcntl.lockf(fileobj, fcntl.LOCK_UN)


def insert_bytes(fobj, size, offset, BUFFER_SIZE=2**16):
    """Insert size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent. Mutagen tries to use mmap to resize the file, but
    falls back to a significantly slower method if mmap fails.
    """

    assert 0 < size
    assert 0 <= offset
    locked = False
    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset
    fobj.write(b'\x00' * size)
    fobj.flush()
    try:
        try:
            import mmap
            map = mmap.mmap(fobj.fileno(), filesize + size)
            try:
                map.move(offset + size, offset, movesize)
            finally:
                map.close()
        except (ValueError, EnvironmentError, ImportError):
            # handle broken mmap scenarios
            locked = lock(fobj)
            fobj.truncate(filesize)

            fobj.seek(0, 2)
            padsize = size
            # Don't generate an enormous string if we need to pad
            # the file out several megs.
            while padsize:
                addsize = min(BUFFER_SIZE, padsize)
                fobj.write(b"\x00" * addsize)
                padsize -= addsize

            fobj.seek(filesize, 0)
            while movesize:
                # At the start of this loop, fobj is pointing at the end
                # of the data we need to move, which is of movesize length.
                thismove = min(BUFFER_SIZE, movesize)
                # Seek back however much we're going to read this frame.
                fobj.seek(-thismove, 1)
                nextpos = fobj.tell()
                # Read it, so we're back at the end.
                data = fobj.read(thismove)
                # Seek back to where we need to write it.
                fobj.seek(-thismove + size, 1)
                # Write it.
                fobj.write(data)
                # And seek back to the end of the unmoved data.
                fobj.seek(nextpos)
                movesize -= thismove

            fobj.flush()
    finally:
        if locked:
            unlock(fobj)


def delete_bytes(fobj, size, offset, BUFFER_SIZE=2**16):
    """Delete size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent. Mutagen tries to use mmap to resize the file, but
    falls back to a significantly slower method if mmap fails.
    """

    locked = False
    assert 0 < size
    assert 0 <= offset
    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset - size
    assert 0 <= movesize
    try:
        if movesize > 0:
            fobj.flush()
            try:
                import mmap
                map = mmap.mmap(fobj.fileno(), filesize)
                try:
                    map.move(offset, offset + size, movesize)
                finally:
                    map.close()
            except (ValueError, EnvironmentError, ImportError):
                # handle broken mmap scenarios
                locked = lock(fobj)
                fobj.seek(offset + size)
                buf = fobj.read(BUFFER_SIZE)
                while buf:
                    fobj.seek(offset)
                    fobj.write(buf)
                    offset += len(buf)
                    fobj.seek(offset + size)
                    buf = fobj.read(BUFFER_SIZE)
        fobj.truncate(filesize - size)
        fobj.flush()
    finally:
        if locked:
            unlock(fobj)


def utf8(data):
    """Convert a basestring to a valid UTF-8 str."""

    if isinstance(data, bytes):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, text_type):
        return data.encode("utf-8")
    else:
        raise TypeError("only unicode/str types can be converted to UTF-8")


def dict_match(d, key, default=None):
    try:
        return d[key]
    except KeyError:
        for pattern, value in iteritems(d):
            if fnmatchcase(key, pattern):
                return value
    return default


def decode_terminated(data, encoding, strict=True):
    """Returns the decoded data until the first NULL terminator
    and all data after it.

    In case the data can't be decoded raises UnicodeError.
    In case the encoding is not found raises LookupError.
    In case the data isn't null terminated (even if it is encoded correctly)
    raises ValueError except if strict is False, then the decoded string
    will be returned anyway.
    """

    codec_info = codecs.lookup(encoding)

    # normalize encoding name so we can compare by name
    encoding = codec_info.name

    # fast path
    if encoding in ("utf-8", "iso8859-1"):
        index = data.find(b"\x00")
        if index == -1:
            # make sure we raise UnicodeError first, like in the slow path
            res = data.decode(encoding), b""
            if strict:
                raise ValueError("not null terminated")
            else:
                return res
        return data[:index].decode(encoding), data[index + 1:]

    # slow path
    decoder = codec_info.incrementaldecoder()
    r = []
    for i, b in enumerate(iterbytes(data)):
        c = decoder.decode(b)
        if c == u"\x00":
            return u"".join(r), data[i + 1:]
        r.append(c)
    else:
        # make sure the decoder is finished
        r.append(decoder.decode(b"", True))
        if strict:
            raise ValueError("not null terminated")
        return u"".join(r), b""
