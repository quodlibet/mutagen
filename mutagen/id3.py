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
from struct import unpack, pack
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

    def __init__(self, filename=None, known_frames=None):
        self.unknown_frames = []
        self.__known_frames = known_frames
        self.__filename = None
        self.__flags = 0
        self.__size = 0
        self.__readbytes = 0
        self.__crc = None

        if filename is not None:
            self.load(filename)

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

    def load(self, filename):
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
                        map(self.loaded_frame, frames.keys(), frames.values())
                    else: raise err, None, stack
            else:
                frames = self.__known_frames
                if (2,3,0) <= self.version:
                    perframe = 10
                    if frames is None: frames = Frames
                if (2,2,0) <= self.version < (2,3,0):
                    perframe = 6
                    if frames is None: frames = Frames_2_2
                while self.__readbytes+perframe < self.__size:
                    try:
                        name, tag = self.load_frame(frames=frames)
                    except EOFError: break

                    if isinstance(tag, Frame): self.loaded_frame(name, tag)
                    else: self.unknown_frames.append([name, tag])
        finally:
            self.__fileobj.close()
            del self.__fileobj
            del self.__filesize

    def getall(self, key):
        if key in self: return [self[key]]
        else:
            key = key + ":"
            return [v for s,v in self.items() if s.startswith(key)]

    def delall(self, key):
        if key in self: del(self[key])
        else:
            key = key + ":"
            for k in filter(lambda s: s.startswith(key), self.keys()):
                del(self[k])

    def setall(self, key, values):
        self.delall(key)
        for tag in values:
            self[tag.HashKey] = tag

    def loaded_frame(self, name, tag):
        # turn 2.2 into 2.3/2.4 tags
        if len(name) == 3: tag = type(tag).__base__(tag)
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

    def load_frame(self, frames):
        if (2,3,0) <= self.version:
            data = self.fullread(10)
            name, size, flags = unpack('>4sLH', data)
            if (2,4,0) <= self.version: size = BitPaddedInt(size)
            #print '%#x' % (self.__fileobj.tell()-10), name, size
        elif (2,2,0) <= self.version:
            data = self.fullread(6)
            name, size = unpack('>3s3s', data)
            flags = 0
            size, = unpack('>L', '\x00'+size)
        if name.strip('\x00') == '': raise EOFError
        if size == 0: return name, data

        framedata = self.fullread(size)
        if self.f_unsynch or flags & 0x40:
            try: framedata = unsynch.decode(framedata)
            except ValueError: pass
            flags &= ~0x40
        try: tag = frames[name]
        except KeyError:
            return name, data + framedata
        else:
            try: tag = tag.fromData(self, flags, framedata)
            except NotImplementedError: return name, data + framedata
        return name, tag

    f_unsynch = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    #f_crc = property(lambda s: bool(s.__extflags & 0x8000))

    def save(self, filename=None):
        # don't trust this code yet - it could corrupt your files
        if filename is None: filename = self.__filename
        f = open(filename, 'rb+')
        try:
            idata = f.read(10)
            id3, ivmaj, ivrev, iflags, isize = unpack('>3sBBB4s', idata)
            isize = BitPaddedInt(isize)
            if id3 != 'ID3': isize = 0

            framedata = map(self.save_frame, self.values())
            framedata.extend([data for (name, data) in self.unknown_frames
                    if len(data) > 10])
            framedata = ''.join(framedata)
            framesize = len(framedata)

            if isize >= framesize:
                osize = isize
                framedata += '\x00' * (osize - framesize)
            else:
                osize = (framesize + 1023) & ~0x3FF

            framesize = BitPaddedInt.to_str(osize, width=4)
            flags = 0
            header = pack('>3sBBB4s', 'ID3', 4, 0, flags, framesize)
            data = header + framedata

            if (isize >= osize):
                f.seek(0)
                f.write(data)
            else:
                from os.path import getsize
                filesize = getsize(filename)
                m = mmap(f.fileno(), filesize)
                try:
                    m.resize(filesize + osize - isize)
                    m.move(osize+10, isize+10, filesize - isize - 10)
                    m[0:osize+10] = data
                finally:
                    m.close()
        finally:
            f.close()

    def save_frame(self, frame):
        flags = 0
        framedata = frame._writeData()
        if len(framedata) > 2048:
            framedata = framedata.encode('zlib')
            flags |= Frame.FLAG24_COMPRESS
        datasize = BitPaddedInt.to_str(len(framedata), width=4)
        header = pack('>4s4sH', type(frame).__name__, datasize, flags)
        return header + framedata

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
    def write(s, frame, value): return str(value)
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
    __seps = ['-', '-', 'T', ':', ':', 'x']
    def get_text(self):
        parts = [self.year, self.month, self.day,
                self.hour, self.minute, self.second]
        pieces = []
        for i, part in enumerate(iter(iter(parts).next, None)):
            pieces.append(self.__formats[i]%part + self.__seps[i])
        return ''.join(pieces)[:-1]

    def set_text(self, text, splitre=re.compile('[-T:]')):
        year, month, day, hour, minute, second = \
                splitre.split(text + ':::::')[:6]
        self.year = year and int(year) or None
        self.month = month and int(month) or None
        self.day = day and int(day) or None
        self.hour = hour and int(hour) or None
        self.minute = minute and int(minute) or None
        self.second = second and int(second) or None

    text = property(get_text, set_text, doc="ID3v2.4 datetime")

    def __str__(self): return self.text
    def __repr__(self): return repr(self.text)
    def __cmp__(self, other): return cmp(self.text, other.text)
    def encode(self, *args): return self.text.encode(*args)

class TimeStampSpec(EncodedTextSpec):
    def read(self, frame, data):
        value, data = super(TimeStampSpec, self).read(frame, data)
        return self.validate(frame, value), data

    def validate(self, frame, value):
        try: return ID3TimeStamp(value)
        except TypeError: raise ValueError, "Invalid ID3TimeStamp: %r" % value

class ChannelSpec(ByteSpec):
    (OTHER, MASTER, FRONTRIGHT, FRONTLEFT, BACKRIGHT, BACKLEFT, FRONTCENTRE,
     BACKCENTRE, SUBWOOFER) = range(9)

class VolumeAdjustment(Spec):
    def read(self, frame, data):
        value = (ord(data[0]) << 8) + ord(data[1])
        return ((value/512.0) - 128.0), data[2:]

    def write(self, frame, value):
        value = int((value + 128) * 512)
        return chr(value >> 8) + chr(value & 0xFF)

    def validate(self, frame, value): return value

class VolumePeak(Spec):
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
                except zlibError:
                    if id3.PEDANTIC:
                        raise ID3BadCompressedData, '%s: %r' % (err, data)

        frame = cls()
        frame._rawdata = data
        frame._flags = tflags
        frame._readData(data)
        return frame
    fromData = classmethod(fromData)

class TextFrame(Frame):
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('text') ]
    def __str__(self): return self.text.encode('utf-8')
    def __unicode__(self): return self.text
    def __eq__(self, other): return self.text == other

class NumericTextFrame(TextFrame):
    _framespec = [ EncodingSpec('encoding'), EncodedNumericTextSpec('text') ]
    def __pos__(self): return int(self.text)

class NumericPartTextFrame(TextFrame):
    _framespec = [ EncodingSpec('encoding'),
        EncodedNumericPartTextSpec('text') ]
    def __pos__(self):
        t = self.text
        return int('/' in t and t[:t.find('/')] or t)

class MultiTextFrame(TextFrame):
    _framespec = [ EncodingSpec('encoding'), MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return u'\u0000'.join(self.text)
    def __eq__(self, other):
        if isinstance(other, str): return str(self) == other
        elif isinstance(other, unicode): return u'\u0000'.join(self.text) == other
        return self.text == other
    def __getitem__(self, item): return self.text[item]
    def __iter__(self): return iter(self.text)
    def append(self, value): return self.text.append(value)
    def extend(self, value): return self.text.extend(value)

class TimeStampTextFrame(MultiTextFrame):
    _framespec = [ EncodingSpec('encoding'), MultiSpec('text', TimeStampSpec('stamp'), sep=u',') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return ','.join([stamp.text for stamp in self.text])


class UrlFrame(Frame):
    _framespec = [ Latin1TextSpec('url') ]
    def __str__(self): return self.url.encode('utf-8')
    def __unicode__(self): return self.url
    def __eq__(self, other): return self.url == other

class UrlFrameU(UrlFrame):
    HashKey = property(lambda s: '%s:%s'%(s.FrameID, s.url))

class TALB(MultiTextFrame): "Album"
class TBPM(NumericTextFrame): "Beats per minute"
class TCOM(MultiTextFrame): "Composer"

class TCON(MultiTextFrame):
    "Content type (Genre)"

    from mutagen._constants import GENRES

    def __get_genres(self):
        genres = []
        import re
        genre_re = re.compile(r"((?:\((?P<id>[0-9]+|RX|CR)\))*)(?P<str>.+)?")
        for value in self.text:
            if value.isdigit():
                try: genres.append(self.GENRES[int(value)])
                except IndexError: genres.append("Unknown")
            elif value == "CR": genres.append("Cover")
            elif value == "RX": genres.append("Remix")
            elif value:
                newgenres = []
                genreid, dummy, genrename = genre_re.match(value).groups()

                if genreid:
                    for gid in genreid[1:-1].split(")("):
                        if gid.isdigit() and int(gid) < len(self.GENRES):
                            gid = unicode(self.GENRES[int(gid)])
                            newgenres.append(gid)
                        elif gid == "CR": newgenres.append("Cover")
                        elif gid == "RX": newgenres.append("Remix")
                        else: newgenres.append("Unknown")

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

    genres = property(__get_genres, __set_genres)

class TCOP(MultiTextFrame): "Copyright (c)"
class TDAT(MultiTextFrame): "Date of recording (DDMM)"
class TDEN(TimeStampTextFrame): "Encoding Time"
class TDOR(TimeStampTextFrame): "Original Release Time"
class TDLY(NumericTextFrame): "Audio Delay (ms)"
class TDRC(TimeStampTextFrame): "Recording Time"
class TDRL(TimeStampTextFrame): "Release Time"
class TDTG(TimeStampTextFrame): "Tagging Time"
class TENC(MultiTextFrame): "Encoder"
class TEXT(MultiTextFrame): "Lyricist"
class TFLT(MultiTextFrame): "File type"
class TIME(MultiTextFrame): "Time of recording (HHMM)"
class TIPL(MultiTextFrame): "Involved People List"
class TIT1(MultiTextFrame): "Content group description"
class TIT2(MultiTextFrame): "Title"
class TIT3(MultiTextFrame): "Subtitle/Description refinement"
class TKEY(MultiTextFrame): "Starting Key"
class TLAN(MultiTextFrame): "Audio Languages"
class TLEN(NumericTextFrame): "Audio Length (ms)"
class TMCL(MultiTextFrame): "Musician Credits List"
class TMED(MultiTextFrame): "Source Media Type"
class TMOO(MultiTextFrame): "Mood"
class TOAL(MultiTextFrame): "Original Album"
class TOFN(MultiTextFrame): "Original Filename"
class TOLY(MultiTextFrame): "Original Lyricist"
class TOPE(MultiTextFrame): "Original Artist/Performer"
class TORY(NumericTextFrame): "Original Release Year"
class TOWN(MultiTextFrame): "Owner/Licensee"
class TPE1(MultiTextFrame): "Lead Artist/Performer/Soloist/Group"
class TPE2(MultiTextFrame): "Band/Orchestra/Accompaniment"
class TPE3(MultiTextFrame): "Conductor"
class TPE4(MultiTextFrame): "Interpreter/Remixer/Modifier"
class TPOS(NumericPartTextFrame): "Part of set"
class TPRO(MultiTextFrame): "Produced (P)"
class TPUB(MultiTextFrame): "Publisher"
class TRCK(NumericPartTextFrame): "Track Number"
class TRDA(MultiTextFrame): "Recording Dates"
class TRSN(MultiTextFrame): "Internet Radio Station Name"
class TRSO(MultiTextFrame): "Internet Radio Station Owner"
class TSIZ(NumericTextFrame): "Size of audio data (bytes)"
class TSOA(MultiTextFrame): "Album Sort Order key"
class TSOP(MultiTextFrame): "Perfomer Sort Order key"
class TSOT(MultiTextFrame): "Title Sort Order key"
class TSRC(MultiTextFrame): "International Standard Recording Code (ISRC)"
class TSSE(MultiTextFrame): "Encoder settings"
class TSST(MultiTextFrame): "Set Subtitle"
class TYER(NumericTextFrame): "Year of recording"

class TXXX(TextFrame):
    "User-defined Text"
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        EncodedTextSpec('text') ]
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

class IPLS(Frame):
    "Involved People List"
    _framespec = [ EncodingSpec('encoding'), MultiSpec('people',
            EncodedTextSpec('involvement'), EncodedTextSpec('person')) ]
    def __eq__(self, other):
        return self.people == other

class MCDI(Frame):
    "Binary dump of CD's TOC"
    _framespec = [ BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

# class ETCO: unsupported
# class MLLT: unsupported
# class SYTC: unsupported
# class USLT: unsupported
# class SYLT: unsupported
#     HashKey = property(lambda s: '%s:%r:%s'%(s.FrameID, s.lang, s.desc))

class COMM(TextFrame):
    "User comment"
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('desc'), EncodedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%r:%s'%(s.FrameID, s.lang, s.desc))

class RVA2(Frame):
    "Relative volume adjustment (2)"
    _framespec = [ Latin1TextSpec('desc'), ChannelSpec('channel'),
        VolumeAdjustment('gain'), VolumePeak('peak') ]
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

class USER(TextFrame):
    "Terms of use"
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%r'%(s.FrameID, s.lang))

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
    frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames
