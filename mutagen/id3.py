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

__all__ = ['ID3', 'Frames', 'Open']

import mutagen
from struct import unpack
from mmap import mmap

PRINT_ERRORS = True

class ID3NoHeaderError(ValueError): pass
class ID3UnsupportedVersionError(NotImplementedError): pass

class ID3(mutagen.Metadata):
    """ID3 is the mutagen.ID3 metadata class.

    It accepts a filename and a dictionary of frameid to frame handlers.
    """

    PEDANTIC = True

    def __init__(self, filename=None, known_frames=None):
        if known_frames is None: known_frames = Frames
        self.unknown_frames = []
        self.__known_frames = known_frames
        self.__filename = None
        self.__flags = 0
        self.__size = 0
        self.__padding = 0
        self.__crc = None
        self.__frames = {}

        if filename is not None:
            self.load(filename)

    def open_mmap(name):
        from os import stat
        from stat import ST_SIZE
        s = stat(name)[ST_SIZE]
        f = file(name, 'rb+')
        return mmap(f.fileno(), s), s
    open_mmap = staticmethod(open_mmap)

    def load(self, filename):
        self.__filename = filename
        self.__map, filesize = ID3.open_mmap(filename)
        try:
            if filesize < 10: raise ID3NoHeaderError(
                    "%s: too small (%d bytes)" % (filename,filesize))
            self.load_header(self.__map, 0)

            offset = self.__frame_offset
            while offset+self.__padding+10 < self.__size:
                name, tag, size = self.load_frame(offset=offset,
                        known_frames=self.__known_frames)
                if name != '\x00\x00\x00\x00':
                    if tag is None:
                        self.unknown_frames.append([name, offset])
                    else:
                        self.loaded_frame(name, tag)

                offset += size
        finally:
            self.__map.close()
            del self.__map

    def loaded_frame(self, name, tag):
        if name == 'TXXX' or name == 'WXXX':
            name += ':' + tag.desc
        self[name] = tag

    def load_header(self, mmapobj, offset=0):
        fn = self.__filename
        o = offset
        f = mmapobj
        id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', f[o:o+10])
        o += 10
        if id3 != 'ID3':
            raise ID3NoHeaderError("'%s' doesn't start with an ID3 tag" % fn)
        if vmaj not in [3, 4]:
            raise ID3UnsupportedVersionError("'%s' ID3v2.%d not supported"
                    % (fn, vmaj))
        if self.PEDANTIC and vmaj == 3 and (flags & 0x1f):
            raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))
        if self.PEDANTIC and vmaj == 4 and (flags & 0x0f):
            raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))

        self.version = (2, vmaj, vrev)
        self.__flags = flags
        self.__size = BitPaddedInt(size)

        if self.f_extended:
            extsize, extflags, padding = unpack('>4sH4s', f[o:o+10])
            o += 10
            extsize = BitPaddedInt(extsize)
            if extsize not in [6, 10]:
                raise ValueError("'%s': invalid extended header size: %d"
                        % (fn, extsize))
            self.__extflags = extflags
            if self.PEDANTIC and (self.__extflags & 0x7fff):
                raise ValueError("'%s': invalid extended flags %#04x"
                        % (fn, extflags))
            self.__padding = BitPaddedInt(padding)
            if self.f_crc:
                self.__crc = BitPaddedInt(unpack('>L', f[o:o+4]))
                o += 4

        self.__frame_offset = o

    def load_frame(self, offset, known_frames):
        f = self.__map
        name, size, flags = unpack('>4s4sH', f[offset:offset+10])
        offset += 10
        size = BitPaddedInt(size)
        if name == '\x00\x00\x00\x00': return name, None, size+10
        try: tag = known_frames[name]
        except KeyError: return name, None, size+10
        else:
            data = f[offset:offset+size]
            if self.f_unsync: data = unsynch.decode(data)
            tag = tag.fromData(self, flags, data)
        return name, tag, size+10

    f_unsync = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    f_crc = property(lambda s: bool(s.__extflags & 0x8000))

class BitPaddedInt(int):
    def __new__(cls, value, bits=7, bigendian=True):
        mask = (1<<(bits))-1
        if isinstance(value, str):
            bytes = [ord(byte) & mask for byte in value]
            if bigendian: bytes.reverse()
            numeric_value = 0
            for shift, byte in zip(range(0, len(bytes)*bits, bits), bytes):
                numeric_value += byte << shift
            return super(BitPaddedInt, cls).__new__(cls, numeric_value)
        else:
            return super(BitPaddedInt, cls).__new__(cls, value)

    def __init__(self, value, bits=7, bigendian=True):
        self.bits = bits
        self.bigendian = bigendian
        return super(BitPaddedInt, self).__init__(value)
    
    def as_str(value, bits=7, bigendian=True, width=4):
        bits = getattr(value, 'bits', bits)
        bigendian = getattr(value, 'bigendian', bigendian)
        value = int(value)
        mask = (1<<bits)-1
        bytes = []
        while value:
            bytes.append(value & mask)
            value = value >> bits
        for i in range(len(bytes), width): bytes.append(0)
        if len(bytes) != width:
            raise ValueError, 'Value too wide (%d bytes)' % len(bytes)
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
                if val != '\x00': raise ValueError('invalid sync-safe string')
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

class EncodingSpec(ByteSpec):
    def validate(self, frame, value):
        if 0 <= value <= 1: return value
        if value is None: return None
        raise ValueError('%s: invalid encoding' % value)

class LanguageSpec(Spec):
    def read(self, frame, data): return data[:3], data[3:]
    def write(self, frame, value): return str(value)
    def validate(self, frame, value):
        if value is None: return None
        if isinstance(value, basestring) and len(value) == 3: return value
        raise ValueError('%s: invalid language' % value)

class BinaryDataSpec(Spec):
    def read(self, frame, data): return data, ''
    def write(self, frame, value): return str(value)
    def validate(self, frame, value): return str(value)

class EncodedTextSpec(Spec):
    encodings = [ ('latin1', '\x00'), ('utf16', '\x00\x00') ]

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

        return data.decode(enc), ret


    def write(self, frame, value):
        enc, term = self.encodings[frame.encoding]
        return value.encode(enc) + term

    def validate(self, frame, value): return unicode(value)

class EncodedSlashTextSpec(EncodedTextSpec):
    def read(self, frame, data):
        value, data = super(EncodedSlashTextSpec, self).read(frame, data)
        return value.split('/'), data

    def write(self, frame, value):
        return super(EncodedSlashTextSpec, self).write(frame, '/'.join(value))
    def validate(self, frame, value):
        if value is None: return []
        if isinstance(value, list): return value
        raise ValueError

class MultiSpec(Spec):
    def __init__(self, name, *specs):
        super(MultiSpec, self).__init__(name)
        self.specs = specs

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
        if isinstance(value, list): return value
        raise ValueError

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

class Frame(object):
    FLAG_ALTERTAG   = 0x8000
    FLAG_ALTERFILE  = 0x4000
    FLAG_READONLY   = 0x2000
    FLAG_ZLIB       = 0x80
    FLAG_ENCRYPT    = 0x40
    FLAG_GROUP      = 0x20

    def __init__(self, *args, **kwargs):
        for checker, val in zip(self._framespec, args):
            setattr(self, checker.name, checker.validate(self, val))
        for checker in self._framespec[len(args):]:
            validated = checker.validate(self, kwargs.get(checker.name, None))
            setattr(self, checker.name, validated)

    def _readData(self, data):
        odata = data
        for reader in self._framespec:
            try: value, data = reader.read(self, data)
            except IndexError:
                print 'IndexError: %s: %r (from %r)' % (
                        type(self).__name__, data, odata)
                raise
            setattr(self, reader.name, value)
        if data.strip('\x00'):
            if PRINT_ERRORS: print 'Leftover data: %s: %r (from %r)' % (
                    type(self).__name__, data, odata)

    def _writeData(self):
        data = []
        for writer in self._framespec:
            data.append(writer.write(self, getattr(self, writer.name)))

    def fromData(cls, id3, tflags, data):
        if tflags & Frame.FLAG_ZLIB: data = data.decode('zlib')
        frame = cls()
        frame._rawdata = data
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

class SlashTextFrame(TextFrame):
    _framespec = [ EncodingSpec('encoding'), EncodedSlashTextSpec('text') ]
    def __str__(self): return '/'.join(self.text).encode('utf-8')
    def __unicode__(self): return '/'.join(self.text)
    def __eq__(self, other):
        if isinstance(other, basestring): return str(self) == other
        return self.text == other
    def __getitem__(self, item): return self.text[item]
    def __iter__(self): return iter(self.text)
    def append(self, value): return self.text.append(value)
    def extend(self, value): return self.text.extend(value)

class UrlFrame(Frame):
    _framespec = [ Latin1TextSpec('url') ]
    def __str__(self): return self.url.encode('utf-8')
    def __unicode__(self): return self.url
    def __eq__(self, other): return self.url == other

class TALB(TextFrame): "Album"
class TBPM(NumericTextFrame): "Beats per minute"
class TCOM(SlashTextFrame): "Composer"
class TCON(TextFrame): "Content type (Genre)"
class TCOP(TextFrame): "Copyright"
class TDAT(TextFrame): "Date of recording (DDMM)"
class TDLY(NumericTextFrame): "Audio Delay (ms)"
class TENC(TextFrame): "Encoder"
class TEXT(SlashTextFrame): "Lyricist"
class TFLT(TextFrame): "File type"
class TIME(TextFrame): "Time of recording (HHMM)"
class TIT1(TextFrame): "Content group description"
class TIT2(TextFrame): "Title"
class TIT3(TextFrame): "Subtitle/Description refinement"
class TKEY(TextFrame): "Starting Key"
class TLAN(TextFrame): "Audio Languages"
class TLEN(NumericTextFrame): "Audio Length (ms)"
class TMED(TextFrame): "Original Media"
class TOAL(TextFrame): "Original Album"
class TOFN(TextFrame): "Original Filename"
class TOLY(TextFrame): "Original Lyricist"
class TOPE(TextFrame): "Original Artist/Performer"
class TORY(NumericTextFrame): "Original Release Year"
class TOWN(TextFrame): "Owner/Licensee"
class TPE1(SlashTextFrame): "Lead Artist/Performer/Soloist/Group"
class TPE2(SlashTextFrame): "Band/Orchestra/Accompaniment"
class TPE3(SlashTextFrame): "Conductor"
class TPE4(SlashTextFrame): "Interpreter/Remixer/Modifier"
class TPOS(NumericPartTextFrame): "Track Number"
class TPUB(TextFrame): "Publisher"
class TRCK(NumericPartTextFrame): "Track Number"
class TRDA(TextFrame): "Recording Dates"
class TRSN(TextFrame): "Internet Radio Station Name"
class TRSO(TextFrame): "Internet Radio Station Owner"
class TSIZ(NumericTextFrame): "Size of audio data (bytes)"
class TSRC(TextFrame): "International Standard Recording Code (ISRC)"
class TSSE(TextFrame): "Encoder settings"
class TYER(NumericTextFrame): "Year of recording"

class TXXX(TextFrame):
    "User-defined Text"
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        EncodedTextSpec('text') ]

class WCOM(UrlFrame): "Commercial Information"
class WCOP(UrlFrame): "Copyright Information"
class WOAF(UrlFrame): "Official File Information"
class WOAS(UrlFrame): "Official Source Information"
class WORS(UrlFrame): "Official Internet Radio Information"
class WPAY(UrlFrame): "Payment Information"
class WPUB(UrlFrame): "Official Publisher Information"

class WXXX(UrlFrame):
    "User-defined URL"
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        Latin1TextSpec('url') ]

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

class COMM(TextFrame):
    "User comment"
    _framespec = [ EncodingSpec('encoding'), LanguageSpec('lang'),
        EncodedTextSpec('desc'), EncodedTextSpec('text') ]
        
# class RVAD: unsupported
# class EQUA: unsupported
# class RVRB: unsupported

class APIC(Frame):
    "Attached (or linked) Picture"
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('mime'),
        ByteSpec('type'), EncodedTextSpec('desc'), BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

# class GEOB: unsupported
# class PCNT: unsupported
# class POPM: unsupported
# class GEOB: unsupported
# class RBUF: unsupported
# class AENC: unsupported
# class LINK: unsupported
# class POSS: unsupported

class USER(TextFrame):
    "Terms of use"
    _framespec = [ EncodingSpec('encoding'), LanguageSpec('lang'),
        EncodedTextSpec('text') ]

# class OWNE: unsupported
# class COMR: unsupported
# class ENCR: unsupported
# class GRID: unsupported
# class PRIV: unsupported

Frames = dict([(k,v) for (k,v) in globals().items()
        if len(k)==4 and isinstance(v, type) and issubclass(v, Frame)])

# support open(filename) as interface
Open = ID3
