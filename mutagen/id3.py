#
# id3 support for mutagen
# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id$
#
#
# This is based off of the following references:
#   http://www.id3.org/id3v2.4.0-structure.txt
#   http://www.id3.org/id3v2.4.0-frames.txt
#   http://www.id3.org/id3v2.3.0.html
#   http://www.id3.org/id3v2-00.txt
#
# Its largest deviation from the above (versions 2.3 and 2.2) is that it will
# not interpret the / characters as a separator, and will almost always accept
# null separators to generate multi-valued text frames.

__all__ = ['ID3', 'Frames', 'Open']

import mutagen
import struct; from struct import unpack, pack
from mmap import mmap
from zlib import error as zlibError

PRINT_ERRORS = True

class error(Exception): pass
class ID3NoHeaderError(error, ValueError): pass
class ID3BadUnsynchData(error, ValueError): pass
class ID3BadCompressedData(error, ValueError): pass
class ID3UnsupportedVersionError(error, NotImplementedError): pass
class ID3EncryptionUnsupportedError(error, NotImplementedError): pass

class ID3(mutagen.Metadata):
    """ID3 is the mutagen.ID3 metadata class.

    It accepts a filename and a dictionary of frameid to frame handlers.
    """

    PEDANTIC = True
    version = (2,4,0)

    def __init__(self, filename=None, known_frames=None, translate=True):
        """Create a dict-like ID3 tag. If a filename is given, load it.
        known_frames contains a list of supported frames; it defaults
        to mutagen.id3.Frames. By adding new frame types you can load
        custom ('experimenta') frames.

        translate is passed directly to the load function."""

        self.unknown_frames = []
        self.__known_frames = known_frames
        self.__filename = None
        self.__flags = 0
        self.__size = 0
        self.__readbytes = 0
        self.__crc = None

        if filename is not None:
            self.load(filename, translate)

    def fullread(self, size):
        try:
            if size > self.__filesize or size < 0:
                if PRINT_ERRORS and self.__filesize:
                    print 'Requested %#x of %#x (%s)' % \
                        (size, self.__filesize, self.__filename)
                raise EOFError, 'Requested %#x of %#x (%s)' % \
                        (size, self.__filesize, self.__filename)
        except AttributeError: pass
        data = self.__fileobj.read(size)
        if len(data) != size: raise EOFError
        self.__readbytes += size
        return data

    def load(self, filename, translate=True):
        """Load tags from the filename. If translate is true, all
        tags are translated to ID3v2.4 internally (for example,
        the 2.3 TYER and TDAT tags are combined to form TDRC). You must
        do this if you intend to write the tag, or else other ID3
        libraries may not load it.

        ID3v2.2 tags are subclasses of the equivalent v2.3/4 tags, so
        you can treat them either way."""

        from os.path import getsize
        self.__filename = filename
        self.__fileobj = file(filename, 'rb')
        self.__filesize = getsize(filename)
        try:
            try:
                self.load_header()
            except EOFError:
                raise ID3NoHeaderError("%s: too small (%d bytes)" %(
                    filename, self.__filesize))
            except (ID3NoHeaderError, ID3UnsupportedVersionError), err:
                import sys
                stack = sys.exc_traceback
                try: self.__fileobj.seek(-128, 2)
                except EnvironmentError: raise err, None, stack
                else:
                    frames = ParseID3v1(self.__fileobj.read(128))
                    if frames is not None:
                        self.version = (1, 1)
                        map(self.loaded_frame, frames.values())
                    else: raise err, None, stack
            else:
                frames = self.__known_frames
                if frames is None:
                    if (2,3,0) <= self.version: frames = Frames
                    elif (2,2,0) <= self.version: frames = Frames_2_2
                data = self.fullread(self.__size)
                for frame in self.read_frames(data, frames=frames):
                    if isinstance(frame, Frame): self.loaded_frame(frame)
                    else: self.unknown_frames.append(frame)
        finally:
            self.__fileobj.close()
            del self.__fileobj
            del self.__filesize
            if translate:
                self.update_to_v24()

    def getall(self, key):
        """Return all frames with a given name (the list may be empty). E.g.
        id3.getall('TTTT') == []
        id3.getall('TIT2') == [id3['TIT2']]
        id3.getall('TXXX') == [TXXX(desc='woo', text='bar'),
                               TXXX(desc='baz', text='quuuux'), ...]

        Since this is based on the frame's HashKey, you can abuse it to do
        things like getall('COMM:MusicMatch') or getall('TXXX:QuodLibet:')."""

        if key in self: return [self[key]]
        else:
            key = key + ":"
            return [v for s,v in self.items() if s.startswith(key)]

    def delall(self, key):
        """Delete all tags of a given kind; see getall."""
        if key in self: del(self[key])
        else:
            key = key + ":"
            for k in filter(lambda s: s.startswith(key), self.keys()):
                del(self[k])

    def setall(self, key, values):
        """Equivalent to delall(key) and adding each frame in 'values'."""
        self.delall(key)
        for tag in values:
            self[tag.HashKey] = tag

    def loaded_frame(self, tag):
        # turn 2.2 into 2.3/2.4 tags
        if len(type(tag).__name__) == 3: tag = type(tag).__base__(tag)
        self[tag.HashKey] = tag

    def load_header(self):
        fn = self.__filename
        data = self.fullread(10)
        id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', data)
        self.__flags = flags
        self.__size = BitPaddedInt(size)
        self.version = (2, vmaj, vrev)

        if id3 != 'ID3':
            raise ID3NoHeaderError("'%s' doesn't start with an ID3 tag" % fn)
        if vmaj not in [2, 3, 4]:
            raise ID3UnsupportedVersionError("'%s' ID3v2.%d not supported"
                    % (fn, vmaj))

        if self.PEDANTIC:
            if (2,4,0) <= self.version and (flags & 0x0f):
                raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))
            elif (2,3,0) <= self.version and (flags & 0x1f):
                raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))


        if self.f_extended:
            self.__extsize = BitPaddedInt(self.fullread(4))
            self.__extdata = self.fullread(self.__extsize - 4)

    def __determine_bpi(self, data, frames):
        if self.version < (2,4,0): return int
        # have to special case whether to use bitpaddedints here
        # spec says to use them, but iTunes has it wrong

        # count number of tags found as BitPaddedInt and how far past
        o = 0
        asbpi = 0
        while o < len(data)-10:
            name, size, flags = unpack('>4sLH', data[o:o+10])
            size = BitPaddedInt(size)
            o += 10+size
            if name in frames: asbpi += 1
        bpioff = o - len(data)

        # count number of tags found as int and how far past
        o = 0
        asint = 0
        while o < len(data)-10:
            name, size, flags = unpack('>4sLH', data[o:o+10])
            o += 10+size
            if name in frames: asint += 1
        intoff = o - len(data)

        # if more tags as int, or equal and bpi is past and int is not
        if asint > asbpi or (asint == asbpi and (bpioff >= 1 and intoff <= 1)):
            return int
        return BitPaddedInt

    def read_frames(self, data, frames):
        if (2,3,0) <= self.version:
            bpi = self.__determine_bpi(data, frames)
            while data:
                header = data[:10]
                try: name, size, flags = unpack('>4sLH', header)
                except struct.error: return # not enough header
                if name.strip('\x00') == '': return
                size = bpi(size)
                framedata = data[10:10+size]
                data = data[10+size:]
                if size == 0: continue # drop empty frames
                try: tag = frames[name]
                except KeyError: yield header + framedata
                else:
                    try: yield self.load_framedata(tag, flags, framedata)
                    except NotImplementedError: yield header + framedata

        elif (2,2,0) <= self.version:
            while data:
                header = data[0:6]
                try: name, size = unpack('>3s3s', header)
                except struct.error: return # not enough header
                size, = struct.unpack('>L', '\x00'+size)
                if name.strip('\x00') == '': return
                frame = data[:6+size]
                framedata = data[6:6+size]
                data = data[6+size:]
                if size == 0: continue # drop empty frames
                try: tag = frames[name]
                except KeyError: yield header + framedata
                else:
                    try: yield self.load_framedata(tag, 0, framedata)
                    except NotImplementedError: yield header + framedata

    def load_framedata(self, tag, flags, framedata):
        if self.f_unsynch or flags & 0x40:
            try: framedata = unsynch.decode(framedata)
            except ValueError: pass
            flags &= ~0x40
        return tag.fromData(self, flags, framedata)
            
    f_unsynch = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    #f_crc = property(lambda s: bool(s.__extflags & 0x8000))

    def save(self, filename=None, v1=1):
        """Save changes to a file, overwriting an old ID3v2 tag but
        preserving any other (e.g. MPEG) data. The default filename is
        the one this tag was created with.

        If v1 is 0, any ID3v1 tag will be removed. If it is 1, the ID3v1
        will be updated if present but not created (this is the default).
        If 2, an ID3v1 tag will be created or updated.

        The lack of a way to neither update nor remove an ID3v1 tag is
        intentional."""
    
        # don't trust this code yet - it could corrupt your files
        if filename is None: filename = self.__filename
        try: f = open(filename, 'rb+')
        except IOError, err:
            from errno import ENOENT
            if err.errno != ENOENT: raise
            f = open(filename, 'ab+')
        try:
            idata = f.read(10)
            try: id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
            except struct.error: id3, insize = '', 0
            insize = BitPaddedInt(insize)
            if id3 != 'ID3': insize = -10

            framedata = map(self.save_frame, self.values())
            framedata.extend([data for data in self.unknown_frames
                    if len(data) > 10])
            framedata = ''.join(framedata)
            framesize = len(framedata)

            if insize >= framesize: outsize = insize
            else: outsize = (framesize + 1023) & ~0x3FF
            framedata += '\x00' * (outsize - framesize)

            framesize = BitPaddedInt.to_str(outsize, width=4)
            flags = 0
            header = pack('>3sBBB4s', 'ID3', 4, 0, flags, framesize)
            data = header + framedata

            if (insize < outsize):
                self.insert_space(f, outsize-insize, insize+10)
            f.seek(0)
            f.write(data)

            f.seek(-128, 2)
            if f.read(3) == "TAG":
                f.seek(-128, 2)
                if v1 > 0: f.write(MakeID3v1(self))
                else: f.truncate()
            elif v1 == 2:
                f.seek(0, 2)
                f.write(MakeID3v1(self))

        finally:
            f.close()

    def insert_space(self, fobj, size, offset):
        """insert size bytes of empty space starting at offset. fobj must be
        an open file object, open rb+ or equivalent."""
        assert 0 < size
        assert 0 <= offset

        fobj.seek(offset)
        backbuf = fobj.read(size)
        if len(backbuf) < size:
            fobj.write('\x00' * (size - len(backbuf)))
        while len(backbuf) == size:
            frontbuf = fobj.read(size)
            fobj.seek(-len(frontbuf), 1)
            fobj.write(backbuf)
            backbuf = frontbuf
        fobj.write(backbuf)

    def save_frame(self, frame):
        flags = 0
        if self.PEDANTIC and isinstance(frame, TextFrame):
            if len(str(frame)) == 0: return ''
        framedata = frame._writeData()
        if len(framedata) > 2048:
            framedata = framedata.encode('zlib')
            flags |= Frame.FLAG24_COMPRESS
        datasize = BitPaddedInt.to_str(len(framedata), width=4)
        header = pack('>4s4sH', type(frame).__name__, datasize, flags)
        return header + framedata

    def update_to_v24(self):
        """Convert an ID3v2.3 tag into an ID3v2.4 tag, either replacing
        or deleting obsolete frames."""

        if self.version < (2,3,0):
            del self.unknown_frames[:] # unsafe to write

        # TDAT, TYER, and TIME have been turned into TDRC.
        if str(self.get("TYER", "")).strip("\x00"):
            date = str(self.pop("TYER"))
            if str(self.get("TDAT", "")).strip("\x00"):
                dat = str(self.pop("TDAT"))
                date = "%s-%s-%s" % (date, dat[:2], dat[2:])
                if str(self.get("TIME", "")).strip("\x00"):
                    time = str(self.pop("TIME"))
                    date += "T%s:%s:00" % (time[:2], time[2:])
            if "TDRC" not in self:
                self.loaded_frame(TDRC(encoding=0, text=date))

        # TORY can be the first part of a TDOR.
        if "TORY" in self:
            date = str(self.pop("TORY"))
            if "TDOR" not in self:
                self.loaded_frame(TDOR(encoding=0, text=date))

        # IPLS is now TIPL.
        if "IPLS" in self:
            if "TIPL" not in self:
                f = self.pop("IPLS")
                self.loaded_frame(TIPL(encoding=f.encoding, people=f.people))

        if "TCON" in self:
            # Get rid of "(xx)Foobr" format.
            self["TCON"].genres = self["TCON"].genres

        # These can't be trivially translated to any ID3v2.4 tags, or
        # should have been removed already.
        for key in ["RVAD", "EQUA", "TRDA", "TSIZ", "TDAT", "TIME"]:
            if key in self: del(self[key])

class BitPaddedInt(int):
    def __new__(cls, value, bits=7, bigendian=True):
        "Strips 8-bits bits out of every byte"
        mask = (1<<(bits))-1
        if isinstance(value, (int, long)):
            bytes = []
            while value:
                bytes.append(value & ((1<<bits)-1))
                value = value >> 8
        if isinstance(value, str):
            bytes = [ord(byte) & mask for byte in value]
            if bigendian: bytes.reverse()
        numeric_value = 0
        for shift, byte in zip(range(0, len(bytes)*bits, bits), bytes):
            numeric_value += byte << shift
        return super(BitPaddedInt, cls).__new__(cls, numeric_value)

    def __init__(self, value, bits=7, bigendian=True):
        "Strips 8-bits bits out of every byte"
        self.bits = bits
        self.bigendian = bigendian
        super(BitPaddedInt, self).__init__(value)
    
    def as_str(value, bits=7, bigendian=True, width=4):
        bits = getattr(value, 'bits', bits)
        bigendian = getattr(value, 'bigendian', bigendian)
        value = int(value)
        mask = (1<<bits)-1
        bytes = []
        while value:
            bytes.append(value & mask)
            value = value >> bits
        # PCNT and POPM use growing integers of at least 4 bytes as counters.
        if width == -1: width = max(4, len(bytes))
        if len(bytes) > width:
            raise ValueError, 'Value too wide (%d bytes)' % len(bytes)
        else: bytes.extend([0] * (width-len(bytes)))
        if bigendian: bytes.reverse()
        return ''.join(map(chr, bytes))
    to_str = staticmethod(as_str)

class unsynch(object):
    def decode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                safe = val != '\xFF'
            else:
                if val > '\xE0': raise ValueError('invalid sync-safe string')
                elif val != '\x00': append(val)
                safe = True
        if not safe: raise ValueError('string ended unsafe')
        return ''.join(output)
    decode = staticmethod(decode)

    def encode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                if val == '\xFF': safe = False
            elif val == '\x00' or val >= '\xE0':
                append('\x00')
                append(val)
                safe = val != '\xFF'
            else:
                append(val)
                safe = True
        if not safe: append('\x00')
        return ''.join(output)
    encode = staticmethod(encode)

class Spec(object):
    def __init__(self, name): self.name = name

class ByteSpec(Spec):
    def read(self, frame, data): return ord(data[0]), data[1:]
    def write(self, frame, value): return chr(value)
    def validate(self, frame, value): return value

class IntegerSpec(Spec):
    def read(self, frame, data):
        return int(BitPaddedInt(data, bits=8)), ''
    def write(self, frame, value):
        return BitPaddedInt.to_str(value, bits=8, width=-1)
    def validate(self, frame, value):
        return value

class EncodingSpec(ByteSpec):
    def read(self, frame, data):
        enc, data = super(EncodingSpec, self).read(frame, data)
        if enc < 16: return enc, data
        else: return 0, chr(enc)+data

    def validate(self, frame, value):
        if 0 <= value <= 3: return value
        if value is None: return None
        raise ValueError, 'Invalid Encoding: %r' % value

class StringSpec(Spec):
    def __init__(self, name, length):
        super(StringSpec, self).__init__(name)
        self.len = length
    def read(s, frame, data): return data[:s.len], data[s.len:]
    def write(s, frame, value):
        if value is None: return '\x00' * s.len
        else: return (str(value) + '\x00' * s.len)[:s.len]
        return str(value)
    def validate(s, frame, value):
        if value is None: return None
        if isinstance(value, basestring) and len(value) == s.len: return value
        raise ValueError, 'Invalid StringSpec[%d] data: %r' % (s.len, value)

class BinaryDataSpec(Spec):
    def read(self, frame, data): return data, ''
    def write(self, frame, value): return str(value)
    def validate(self, frame, value): return str(value)

class EncodedTextSpec(Spec):
    encodings = [ ('latin1', '\x00'), ('utf16', '\x00\x00'),
                  ('utf_16_be', '\x00\x00'), ('utf8', '\x00') ]

    def read(self, frame, data):
        enc, term = self.encodings[frame.encoding]
        ret = ''
        if len(term) == 1:
            if term in data:
                data, ret = data.split(term, 1)
        else:
            offset = -1
            try:
                while True:
                    offset = data.index(term, offset+1)
                    if offset & 1: continue
                    data, ret = data[0:offset], data[offset+2:]; break
            except ValueError: pass

        if len(data) < len(term): return u'', ret
        return data.decode(enc), ret

    def write(self, frame, value):
        enc, term = self.encodings[frame.encoding]
        return value.encode(enc) + term

    def validate(self, frame, value): return unicode(value)

class MultiSpec(Spec):
    def __init__(self, name, *specs, **kw):
        super(MultiSpec, self).__init__(name)
        self.specs = specs
        self.sep = kw.get('sep')

    def read(self, frame, data):
        values = []
        while data:
            record = []
            for spec in self.specs:
                value, data = spec.read(frame, data)
                record.append(value)
            if len(self.specs) != 1: values.append(record)
            else: values.append(record[0])
        return values, data

    def write(self, frame, value):
        data = []
        if len(self.specs) == 1:
            for v in value:
                data.append(self.specs[0].write(frame, v))
        else:
            for record in value:
                for v, s in zip(record, self.specs):
                    data.append(s.write(frame, v))
        return ''.join(data)

    def validate(self, frame, value):
        if value is None: return []
        if self.sep and isinstance(value, basestring):
            value = value.split(self.sep)
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [ 
                    [s.validate(frame, v) for (v,s) in zip(val, self.specs)]
                    for val in value ]
        raise ValueError, 'Invalid MultiSpec data: %r' % value

class EncodedNumericTextSpec(EncodedTextSpec): pass
class EncodedNumericPartTextSpec(EncodedTextSpec): pass

class Latin1TextSpec(EncodedTextSpec):
    def read(self, frame, data):
        if '\x00' in data: data, ret = data.split('\x00',1)
        else: ret = ''
        return data.decode('latin1'), ret

    def write(self, data, value):
        return value.encode('latin1') + '\x00'

    def validate(self, frame, value): return unicode(value)

class ID3TimeStamp(object):
    import re
    def __init__(self, text):
        if isinstance(text, ID3TimeStamp): text = text.text
        self.text = text

    __formats = ['%04d'] + ['%02d'] * 5
    __seps = ['-', '-', ' ', ':', ':', 'x']
    def get_text(self):
        parts = [self.year, self.month, self.day,
                self.hour, self.minute, self.second]
        pieces = []
        for i, part in enumerate(iter(iter(parts).next, None)):
            pieces.append(self.__formats[i]%part + self.__seps[i])
        return u''.join(pieces)[:-1]

    def set_text(self, text, splitre=re.compile('[-T:/.]|\s+')):
        year, month, day, hour, minute, second = \
                splitre.split(text + ':::::')[:6]
        for a in 'year month day hour minute second'.split():
            try: v = int(locals()[a])
            except ValueError: v = None
            setattr(self, a, v)

    text = property(get_text, set_text, doc="ID3v2.4 datetime")

    def __str__(self): return self.text
    def __repr__(self): return repr(self.text)
    def __cmp__(self, other): return cmp(self.text, other.text)
    def encode(self, *args): return self.text.encode(*args)

class TimeStampSpec(EncodedTextSpec):
    def read(self, frame, data):
        value, data = super(TimeStampSpec, self).read(frame, data)
        return self.validate(frame, value), data

    def write(self, frame, data):
        return super(TimeStampSpec, self).write(frame,
                data.text.replace(' ', 'T'))

    def validate(self, frame, value):
        try: return ID3TimeStamp(value)
        except TypeError: raise ValueError, "Invalid ID3TimeStamp: %r" % value

class ChannelSpec(ByteSpec):
    (OTHER, MASTER, FRONTRIGHT, FRONTLEFT, BACKRIGHT, BACKLEFT, FRONTCENTRE,
     BACKCENTRE, SUBWOOFER) = range(9)

class VolumeAdjustmentSpec(Spec):
    def read(self, frame, data):
        value, = unpack('>h', data[0:2])
        return value/512.0, data[2:]

    def write(self, frame, value):
        return pack('>h', round(value * 512))

    def validate(self, frame, value): return value

class VolumePeakSpec(Spec):
    def read(self, frame, data):
        bits = ord(data[0])
        bytes = min(4, (bits + 7) >> 3)
        if bits and PRINT_ERRORS:
            print "RVA2 peak reading unsupported (%r)" % data
        return 0, data[1+bytes:]

    def write(self, frame, value):
        if value and PRINT_ERRORS:
            print "RVA2 peak writing unsupported (%r)" % value
        return "\x00"

    def validate(self, frame, value): return value

class Frame(object):
    FLAG23_ALTERTAG     = 0x8000
    FLAG23_ALTERFILE    = 0x4000
    FLAG23_READONLY     = 0x2000
    FLAG23_COMPRESS     = 0x0080
    FLAG23_ENCRYPT      = 0x0040
    FLAG23_GROUP        = 0x0020

    FLAG24_ALTERTAG     = 0x4000
    FLAG24_ALTERFILE    = 0x2000
    FLAG24_READONLY     = 0x1000
    FLAG24_GROUPID      = 0x0040
    FLAG24_COMPRESS     = 0x0008
    FLAG24_ENCRYPT      = 0x0004
    FLAG24_UNSYNCH      = 0x0002
    FLAG24_DATALEN      = 0x0001

    _framespec = []
    def __init__(self, *args, **kwargs):
        if len(args)==1 and len(kwargs)==0 and isinstance(args[0], type(self)):
            other = args[0]
            for checker in self._framespec:
                val = checker.validate(self, getattr(other, checker.name))
                setattr(self, checker.name, val)
        else:
            for checker, val in zip(self._framespec, args):
                setattr(self, checker.name, checker.validate(self, val))
            for checker in self._framespec[len(args):]:
                validated = checker.validate(self, kwargs.get(checker.name, None))
                setattr(self, checker.name, validated)

    HashKey = property(lambda s: s.FrameID, doc="serves as a hash key")
    FrameID = property(lambda s: type(s).__name__, doc="ID3 Frame ID")

    def __repr__(self):
        """eval(repr(frame)) == frame, for all frames."""
        kw = []
        for attr in self._framespec:
            kw.append('%s=%r' % (attr.name, getattr(self, attr.name)))
        return '%s(%s)' % (type(self).__name__, ', '.join(kw))

    def _readData(self, data):
        odata = data
        for reader in self._framespec:
            value, data = reader.read(self, data)
            setattr(self, reader.name, value)
        if data.strip('\x00'):
            if PRINT_ERRORS: print 'Leftover data: %s: %r (from %r)' % (
                    type(self).__name__, data, odata)

    def _writeData(self):
        data = []
        for writer in self._framespec:
            data.append(writer.write(self, getattr(self, writer.name)))
        return ''.join(data)

    def fromData(cls, id3, tflags, data):

        if (2,4,0) <= id3.version:
            if tflags & Frame.FLAG24_UNSYNCH and not id3.f_unsynch:
                try: data = unsynch.decode(data)
                except ValueError, err:
                    if id3.PEDANTIC:
                        raise ID3BadUnsynchData, '%s: %r' % (err, data)
            if tflags & Frame.FLAG24_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG24_COMPRESS:
                try: data = data.decode('zlib')
                except zlibError, err:
                    if id3.PEDANTIC:
                        raise ID3BadCompressedData, '%s: %r' % (err, data)

        elif (2,3,0) <= id3.version:
            if tflags & Frame.FLAG23_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG23_COMPRESS:
                try: data = data.decode('zlib')
                except zlibError, err:
                    if id3.PEDANTIC:
                        raise ID3BadCompressedData, '%s: %r' % (err, data)

        frame = cls()
        frame._rawdata = data
        frame._flags = tflags
        frame._readData(data)
        return frame
    fromData = classmethod(fromData)

class TextFrame(Frame):
    """Text frames support multiple values; it can be streated as a
    single null-separated string, or a list of values (with append,
    extend, and a [] accessor)."""

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return u'\u0000'.join(self.text)
    def __eq__(self, other):
        if isinstance(other, str): return str(self) == other
        elif isinstance(other, unicode):
            return u'\u0000'.join(self.text) == other
        return self.text == other
    def __getitem__(self, item): return self.text[item]
    def __iter__(self): return iter(self.text)
    def append(self, value): return self.text.append(value)
    def extend(self, value): return self.text.extend(value)

class NumericTextFrame(TextFrame):
    """In addition to the TextFrame methods, these frames support the
    unary plus operation (+frame) to return the first number in the list."""

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedNumericTextSpec('text'), sep=u'\u0000') ]
    def __pos__(self): return int(self.text[0])

class NumericPartTextFrame(TextFrame):
    """In addition to the TextFrame methods, these frames support the
    unary plus operation (+frame) to return the first number in the list."""
    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedNumericPartTextSpec('text'), sep=u'\u0000') ]
    def __pos__(self):
        t = self.text[0]
        return int('/' in t and t[:t.find('/')] or t)

class TimeStampTextFrame(TextFrame):
    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', TimeStampSpec('stamp'), sep=u',') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return ','.join([stamp.text for stamp in self.text])

class UrlFrame(Frame):
    _framespec = [ Latin1TextSpec('url') ]
    def __str__(self): return self.url.encode('utf-8')
    def __unicode__(self): return self.url
    def __eq__(self, other): return self.url == other

class UrlFrameU(UrlFrame):
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.url))

class TALB(TextFrame): "Album"
class TBPM(NumericTextFrame): "Beats per minute"
class TCOM(TextFrame): "Composer"

class TCON(TextFrame):
    """Content type (Genre)

    The raw text data for a genre may be in one of several formats, either
    string data or a numeric code. For friendly access, use the genres
    property."""

    from mutagen._constants import GENRES

    def __get_genres(self):
        genres = []
        import re
        genre_re = re.compile(r"((?:\((?P<id>[0-9]+|RX|CR)\))*)(?P<str>.+)?")
        for value in self.text:
            if value.isdigit():
                try: genres.append(self.GENRES[int(value)])
                except IndexError: genres.append(u"Unknown")
            elif value == "CR": genres.append(u"Cover")
            elif value == "RX": genres.append(u"Remix")
            elif value:
                newgenres = []
                genreid, dummy, genrename = genre_re.match(value).groups()

                if genreid:
                    for gid in genreid[1:-1].split(")("):
                        if gid.isdigit() and int(gid) < len(self.GENRES):
                            gid = unicode(self.GENRES[int(gid)])
                            newgenres.append(gid)
                        elif gid == "CR": newgenres.append(u"Cover")
                        elif gid == "RX": newgenres.append(u"Remix")
                        else: newgenres.append(u"Unknown")

                if genrename:
                    # "Unescaping" the first parenthesis
                    if genrename.startswith("(("): genrename = genrename[1:]
                    if genrename not in newgenres: newgenres.append(genrename)

                genres.extend(newgenres)

        return genres

    def __set_genres(self, genres):
        if isinstance(genres, basestring): genres = [genres]
        self.text = map(self.__decode, genres)

    def __decode(self, value):
        if isinstance(value, str):
            enc = EncodedTextSpec.encodings[self.encoding][0]
            return value.decode(enc)
        else: return value

    genres = property(__get_genres, __set_genres, None,
                      "A list of genres parsed from the raw text data.")

class TCOP(TextFrame): "Copyright (c)"
class TDAT(TextFrame): "Date of recording (DDMM)"
class TDEN(TimeStampTextFrame): "Encoding Time"
class TDOR(TimeStampTextFrame): "Original Release Time"
class TDLY(NumericTextFrame): "Audio Delay (ms)"
class TDRC(TimeStampTextFrame): "Recording Time"
class TDRL(TimeStampTextFrame): "Release Time"
class TDTG(TimeStampTextFrame): "Tagging Time"
class TENC(TextFrame): "Encoder"
class TEXT(TextFrame): "Lyricist"
class TFLT(TextFrame): "File type"
class TIME(TextFrame): "Time of recording (HHMM)"
class TIT1(TextFrame): "Content group description"
class TIT2(TextFrame): "Title"
class TIT3(TextFrame): "Subtitle/Description refinement"
class TKEY(TextFrame): "Starting Key"
class TLAN(TextFrame): "Audio Languages"
class TLEN(NumericTextFrame): "Audio Length (ms)"
class TMED(TextFrame): "Source Media Type"
class TMOO(TextFrame): "Mood"
class TOAL(TextFrame): "Original Album"
class TOFN(TextFrame): "Original Filename"
class TOLY(TextFrame): "Original Lyricist"
class TOPE(TextFrame): "Original Artist/Performer"
class TORY(NumericTextFrame): "Original Release Year"
class TOWN(TextFrame): "Owner/Licensee"
class TPE1(TextFrame): "Lead Artist/Performer/Soloist/Group"
class TPE2(TextFrame): "Band/Orchestra/Accompaniment"
class TPE3(TextFrame): "Conductor"
class TPE4(TextFrame): "Interpreter/Remixer/Modifier"
class TPOS(NumericPartTextFrame): "Part of set"
class TPRO(TextFrame): "Produced (P)"
class TPUB(TextFrame): "Publisher"
class TRCK(NumericPartTextFrame): "Track Number"
class TRDA(TextFrame): "Recording Dates"
class TRSN(TextFrame): "Internet Radio Station Name"
class TRSO(TextFrame): "Internet Radio Station Owner"
class TSIZ(NumericTextFrame): "Size of audio data (bytes)"
class TSOA(TextFrame): "Album Sort Order key"
class TSOP(TextFrame): "Perfomer Sort Order key"
class TSOT(TextFrame): "Title Sort Order key"
class TSRC(TextFrame): "International Standard Recording Code (ISRC)"
class TSSE(TextFrame): "Encoder settings"
class TSST(TextFrame): "Set Subtitle"
class TYER(NumericTextFrame): "Year of recording"

class TXXX(TextFrame):
    "User-defined Text"
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))

class WCOM(UrlFrameU): "Commercial Information"
class WCOP(UrlFrame): "Copyright Information"
class WOAF(UrlFrame): "Official File Information"
class WOAR(UrlFrameU): "Official Artist/Performer Information"
class WOAS(UrlFrame): "Official Source Information"
class WORS(UrlFrame): "Official Internet Radio Information"
class WPAY(UrlFrame): "Payment Information"
class WPUB(UrlFrame): "Official Publisher Information"

class WXXX(UrlFrame):
    "User-defined URL"
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        Latin1TextSpec('url') ]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))

class PairedTextFrame(Frame):
    _framespec = [ EncodingSpec('encoding'), MultiSpec('people',
        EncodedTextSpec('involvement'), EncodedTextSpec('person')) ]
    def __eq__(self, other):
        return self.people == other

class TIPL(PairedTextFrame): "Involved People List"
class TMCL(PairedTextFrame): "Musicians Credits List"
class IPLS(TIPL): "Involved People List"

class MCDI(Frame):
    "Binary dump of CD's TOC"
    _framespec = [ BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

# class ETCO: unsupported
# class MLLT: unsupported
# class SYTC: unsupported
# class USLT: unsupported
# class SYLT: unsupported
#     HashKey = property(lambda s: '%s:%s:%r'%(s.FrameID, s.desc, s.lang))

class COMM(TextFrame):
    "User comment"
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    HashKey = property(lambda s: '%s:%s:%r'%(s.FrameID, s.desc, s.lang))

class RVA2(Frame):
    """Relative volume adjustment (2)

    Peak levels are not supported because the ID3 standard does not
    describe how they are stored."""
    _framespec = [ Latin1TextSpec('desc'), ChannelSpec('channel'),
        VolumeAdjustmentSpec('gain'), VolumePeakSpec('peak') ]
    _channels = ["Other", "Master volume", "Front right", "Front left",
                 "Back right", "Back left", "Front centre", "Back centre",
                 "Subwoofer"]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))

    def __eq__(self, other):
        return ((str(self) == other) or
                (self.desc == other.desc and
                 self.channel == other.channel and
                 self.gain == other.gain and
                 self.peak == other.peak))

    def __str__(self):
        return "%s: %+f dB/%f" % (
            self._channels[self.channel], self.gain, self.peak)

# class EQU2: unsupported
#     HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))
# class RVAD: unsupported
# class EQUA: unsupported
# class RVRB: unsupported

class APIC(Frame):
    "Attached (or linked) Picture"
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('mime'),
        ByteSpec('type'), EncodedTextSpec('desc'), BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))

class PCNT(Frame):
    "Play counter"
    _framespec = [ IntegerSpec('count') ]

    def __eq__(self, other): return self.count == other
    def __pos__(self): return self.count

class POPM(Frame):
    "Popularimeter"
    _framespec = [ Latin1TextSpec('email'), ByteSpec('rating'),
        IntegerSpec('count') ]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.email))

    def __eq__(self, other): return self.rating == other
    def __pos__(self): return self.rating

class GEOB(Frame):
    "General Encapsulated Object"
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('mime'),
        EncodedTextSpec('filename'), EncodedTextSpec('desc'), 
        BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.desc))

    def __eq__(self, other): return self.data == other

# class RBUF: unsupported
# class AENC: unsupported
#     HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.owner))
# class LINK: unsupported
#     HashKey = property(lambda s: '%s:%s:%s:%s'%(s.FrameID, s.frameid, s.url,    s.data))
# class POSS: unsupported

class UFID(Frame):
    _framespec = [ Latin1TextSpec('owner'), BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.owner))
    def __eq__(s, o):
        if isinstance(o, UFI): return s.owner == o.owner and s.data == o.data
        else: return s.data == o

class USER(Frame):
    "Terms of use"
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%r'%(s.FrameID, s.lang))

    def __str__(self): return self.text.encode('utf-8')
    def __unicode__(self): return self.text
    def __eq__(self, other): return self.text == other

# class OWNE: unsupported
# class COMR: unsupported
#     HashKey = property(lambda s: '%s:%s'%(s.FrameID, s._writeData()))
# class ENCR: unsupported
# class GRID: unsupported
#     HashKey = property(lambda s: '%s:%s:%s'%(s.FrameID, s.owner, s.group))
# class PRIV: unsupported
#     HashKey = property(lambda s: '%s:%s'%(s.FrameID, s._writeData()))
# class SIGN: unsupported
#     HashKey = property(lambda s: '%s:%s'%(s.FrameID, s._writeData()))
# class SEEK: unsupported
# class ASPI: unsupported

Frames = dict([(k,v) for (k,v) in globals().items()
        if len(k)==4 and isinstance(v, type) and issubclass(v, Frame)])

# ID3v2.2 frames
class UFI(UFID): "Unique File Identifier"

class TT1(TIT1): "Content group description"
class TT2(TIT2): "Title"
class TT3(TIT3): "Subtitle/Description refinement"
class TP1(TPE1): "Lead Artist/Performer/Soloist/Group"
class TP2(TPE2): "Band/Orchestra/Accompaniment"
class TP3(TPE3): "Conductor"
class TP4(TPE4): "Interpreter/Remixer/Modifier"
class TCM(TCOM): "Composer"
class TXT(TEXT): "Lyricist"
class TLA(TLAN): "Audio Language(s)"
class TCO(TCON): "Content Type (Genre)"
class TAL(TALB): "Album"
class TPA(TPOS): "Part of set"
class TRK(TRCK): "Track Number"
class TRC(TSRC): "International Standard Recording Code (ISRC)"
class TYE(TYER): "Year of recording"
class TDA(TDAT): "Date of recording (DDMM)"
class TIM(TIME): "Time of recording (HHMM)"
class TRD(TRDA): "Recording Dates"
class TMT(TMED): "Source Media Type"
class TFT(TFLT): "File Type"
class TBP(TBPM): "Beats per minute"
class TCR(TCOP): "Copyright (C)"
class TPB(TPUB): "Publisher"
class TEN(TENC): "Encoder"
class TSS(TSSE): "Encoder settings"
class TOF(TOFN): "Original Filename"
class TLE(TLEN): "Audio Length (ms)"
class TSI(TSIZ): "Audio Data size (bytes)"
class TDY(TDLY): "Audio Delay (ms)"
class TKE(TKEY): "Starting Key"
class TOT(TOAL): "Original Album"
class TOA(TOPE): "Original Artist/Perfomer"
class TOL(TOLY): "Original Lyricist"
class TOR(TORY): "Original Release Year"

class TXX(TXXX): "User-defined Text"

class WAF(WOAF): "Official File Information"
class WAR(WOAR): "Official Artist/Performer Information"
class WAS(WOAS): "Official Source Information"
class WCM(WCOM): "Commercial Information"
class WCP(WCOP): "Copyright Information"
class WPB(WPUB): "Official Publisher Information"

class WXX(WXXX): "User-defined URL"

class IPL(IPLS): "Involved people list"
class MCI(MCDI): "Binary dump of CD's TOC"
#class ETC(ETCO)
#class MLL(MLLT)
#class STC(SYTC)
#class ULT(USLT)
#class SLT(SYLT)
class COM(COMM): "Comment"
#class RVA(RVAD)
#class EQU(EQUA)
#class REV(RVRB)
class PIC(APIC):
    "Attached Picture"
    _framespec = [ EncodingSpec('encoding'), StringSpec('mime', 3),
        ByteSpec('type'), EncodedTextSpec('desc'), BinaryDataSpec('data') ]
class GEO(GEOB): "General Encapsulated Object"
class CNT(PCNT): "Play counter"
class POP(POPM): "Popularimeter"
#class BUF(RBUF)
#class CRM(????)
#class CRA(AENC)
#class LNK(LINK)

Frames_2_2 = dict([(k,v) for (k,v) in globals().items()
        if len(k)==3 and isinstance(v, type) and issubclass(v, Frame)])

# support open(filename) as interface
Open = ID3

# ID3v1.1 support.
def ParseID3v1(string):
    """Parse a 128-byte string as an ID3v1.1 tag, returning a dict of
    ID3v2.4 frames."""
    from struct import error as StructError
    frames = {}
    try:
        tag, title, artist, album, year, comment, track, genre = unpack(
            "3s30s30s30s4s29sbb", string)
    except StructError: return None

    if tag != "TAG": return None
    title = title.strip("\x00").strip().decode('latin1')
    artist = artist.strip("\x00").strip().decode('latin1')
    album = album.strip("\x00").strip().decode('latin1')
    year = year.strip("\x00").strip().decode('latin1')
    comment = comment.strip("\x00").strip().decode('latin1')

    if title: frames["TIT2"] = TIT2(encoding=0, text=title)
    if artist: frames["TPE1"] = TPE1(encoding=0, text=[artist])
    if album: frames["TALB"] = TALB(encoding=0, text=album)
    if year: frames["TDRC"] = TDRC(encoding=0, text=year)
    if comment: frames["COMM"] = COMM(
        encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)
    if track: frames["TRCK"] = TRCK(encoding=0, text=str(track))
    if genre != -1: frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames

def MakeID3v1(id3):
    """Generate an ID3v1.1 tag string from a dictionary of ID3v2.4 frames
    (like a mutagen.id3.ID3 instance)."""

    v1 = {}

    for v2id, name in {"TIT2": "title", "TPE1": "artist",
                       "TALB": "album", "COMM:": "comment"}.items():
        if v2id in id3:
            text = id3[v2id].text[0].encode('latin1', 'replace')[:30]
        else: text = ""
        v1[name] = text + ("\x00" * (30 - len(text)))

    if "TRCK" in id3:
        try: v1["track"] = chr(+id3["TRCK"])
        except ValueError: v1["track"] = "\x00"
    else: v1["track"] = "\x00"

    if "TCON" in id3:
        try: genre = id3["TCON"].genres[0]
        except IndexError: pass
        else:
            if genre in TCON.GENRES:
                v1["genre"] = chr(TCON.GENRES.index(genre))
    if "genre" not in v1: v1["genre"] = "\xff"

    if "TDRC" in id3: v1["year"] = str(id3["TDRC"])[:4]
    else: v1["year"] = "\x00\x00\x00\x00"

    return "TAG%(title)s%(artist)s%(album)s%(year)s%(comment)s%(genre)s" % v1 
