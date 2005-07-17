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
from struct import unpack, pack
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
        self.__readbytes = 0
        self.__crc = None

        if filename is not None:
            self.load(filename)

    def fullread(self, size):
        data = self.__fileobj.read(size)
        if len(data) != size: raise EOFError
        self.__readbytes += size
        return data

    def load(self, filename):
        self.__filename = filename
        self.__fileobj = file(filename, 'rb')
        try:
            try:
                self.load_header()
            except EOFError:
                from os.path import getsize
                raise ID3NoHeaderError("%s: too small (%d bytes)" %(
                    filename, getsize(filename)))
            except (ID3NoHeaderError, ID3UnsupportedVersionError), err:
                import sys
                stack = sys.exc_traceback
                try: self.__fileobj.seek(-128, 2)
                except EnvironmentError: raise err, None, stack
                else:
                    frames = ParseID3v1(self.__fileobj.read(128))
                    if frames is not None:
                        map(self.loaded_frame, frames.keys(), frames.values())
                    else: raise err, None, stack
            else:
                while self.__readbytes+10 < self.__size:
                    try:
                        name, tag = self.load_frame(frames=self.__known_frames)
                    except EOFError: break

                    if name != '\x00\x00\x00\x00':
                        if isinstance(tag, Frame):
                            self.loaded_frame(name, tag)
                        else:
                            self.unknown_frames.append([name, tag])
        finally:
            self.__fileobj.close()
            del self.__fileobj

    def loaded_frame(self, name, tag):
        if name == 'TXXX' or name == 'WXXX':
            name += ':' + tag.desc
        self[name] = tag

    def load_header(self):
        fn = self.__filename
        data = self.fullread(10)
        id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', data)
        self.__flags = flags
        self.__size = BitPaddedInt(size)
        self.version = (2, vmaj, vrev)

        if id3 != 'ID3':
            raise ID3NoHeaderError("'%s' doesn't start with an ID3 tag" % fn)
        if vmaj not in [3, 4]:
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
        data = self.fullread(10)
        name, size, flags = unpack('>4s4sH', data)
        size = BitPaddedInt(size)
        if name == '\x00\x00\x00\x00': return name, None
        if size == 0: return name, data
        framedata = self.fullread(size)
        try: tag = frames[name]
        except KeyError:
            return name, data + framedata
        else:
            if self.f_unsynch or flags & 0x40:
                framedata = unsynch.decode(framedata)
            tag = tag.fromData(self, flags, framedata)
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

            framedata = map(self.save_frame, frame.values())
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
    def read(self, frame, data):
        enc, data = super(EncodingSpec, self).read(frame, data)
        if enc < 16: return enc, data
        else: return 0, chr(enc)+data

    def validate(self, frame, value):
        if 0 <= value <= 3: return value
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

        return data.decode(enc), ret

    def write(self, frame, value):
        enc, term = self.encodings[frame.encoding]
        return value.encode(enc) + term

    def validate(self, frame, value): return unicode(value)

class EncodedMultiTextSpec(EncodedTextSpec):
    def read(self, frame, data):
        values = []
        while 1:
            value, data = super(EncodedMultiTextSpec, self).read(frame, data)
            values.append(value)
            if not data: break
        return values, data

    def write(self, frame, value):
        return super(EncodedMultiTextSpec, self).write(frame, u'\u0000'.join(value))
    def validate(self, frame, value):
        enc, term = self.encodings[frame.encoding or 0]
        if value is None: return []
        if isinstance(value, list): return value
        if isinstance(value, str): return value.decode(enc).split(u'\u0000')
        if isinstance(value, unicode): return value.split(u'\u0000')
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
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [ 
                    [s.validate(frame, v) for (v,s) in zip(val, self.specs)]
                    for val in value ]
        raise ValueError, repr(value)

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
        except TypeError: raise ValueError, repr(value)

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

    def __init__(self, *args, **kwargs):
        for checker, val in zip(self._framespec, args):
            setattr(self, checker.name, checker.validate(self, val))
        for checker in self._framespec[len(args):]:
            validated = checker.validate(self, kwargs.get(checker.name, None))
            setattr(self, checker.name, validated)

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
                data = unsynch.decode(data)
            if tflags & Frame.FLAG24_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG24_COMPRESS:
                data = data.decode('zlib')

        elif (2,3,0) <= id3.version:
            if tflags & Frame.FLAG24_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG23_COMPRESS:
                data = data.decode('zlib')

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
    _framespec = [ EncodingSpec('encoding'), EncodedMultiTextSpec('text') ]
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
    _framespec = [ EncodingSpec('encoding'), MultiSpec('text', TimeStampSpec('stamp')) ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return ','.join([stamp.text for stamp in self.text])


class UrlFrame(Frame):
    _framespec = [ Latin1TextSpec('url') ]
    def __str__(self): return self.url.encode('utf-8')
    def __unicode__(self): return self.url
    def __eq__(self, other): return self.url == other

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
class TMED(MultiTextFrame): "Original Media"
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
class TPOS(NumericPartTextFrame): "Track Number"
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

class WCOM(UrlFrame): "Commercial Information"
class WCOP(UrlFrame): "Copyright Information"
class WOAF(UrlFrame): "Official File Information"
class WOAR(UrlFrame): "Official Artist/Performer Information"
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

class RVA2(Frame):
    "Relative volume adjustment (2)"
    _framespec = [ Latin1TextSpec('desc'), ChannelSpec('channel'),
        VolumeAdjustment('gain'), VolumePeak('peak') ]
    _channels = ["Other", "Master volume", "Front right", "Front left",
                 "Back right", "Back left", "Front centre", "Back centre",
                 "Subwoofer"]

    def __eq__(self, other):
        return ((str(self) == other) or
                (self.desc == other.desc and
                 self.channel == other.channel and
                 self.gain == other.gain and
                 self.peak == other.peak))

    def __str__(self):
        return "%s: %+f dB/%f" % (
            self._channels[self.channel], self.gain, self.peak)

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
    # FIXME: Needs to be TDAT if 2.4 was requested (if we have a way
    # to request tag versions).
    if year: frames["TYER"] = TYER(encoding=0, text=year)
    if comment: frames["COMM"] = COMM(
        encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)
    if track: frames["TRCK"] = TRCK(encoding=0, text=str(track))
    frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames
