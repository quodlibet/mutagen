# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.


class error(Exception):
    pass


class ID3NoHeaderError(error, ValueError):
    pass


class ID3BadUnsynchData(error, ValueError):
    pass


class ID3BadCompressedData(error, ValueError):
    pass


class ID3TagError(error, ValueError):
    pass


class ID3UnsupportedVersionError(error, NotImplementedError):
    pass


class ID3EncryptionUnsupportedError(error, NotImplementedError):
    pass


class ID3JunkFrameError(error, ValueError):
    pass


class ID3Warning(error, UserWarning):
    pass


class unsynch(object):
    @staticmethod
    def decode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                safe = val != '\xFF'
            else:
                if val >= '\xE0':
                    raise ValueError('invalid sync-safe string')
                elif val != '\x00':
                    append(val)
                safe = True
        if not safe:
            raise ValueError('string ended unsafe')
        return ''.join(output)

    @staticmethod
    def encode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                if val == '\xFF':
                    safe = False
            elif val == '\x00' or val >= '\xE0':
                append('\x00')
                append(val)
                safe = val != '\xFF'
            else:
                append(val)
                safe = True
        if not safe:
            append('\x00')
        return ''.join(output)


class BitPaddedInt(int):
    def __new__(cls, value, bits=7, bigendian=True):
        "Strips 8-bits bits out of every byte"
        mask = (1 << (bits)) - 1
        if isinstance(value, (int, long)):
            bytes = []
            while value:
                bytes.append(value & ((1 << bits) - 1))
                value = value >> 8
        if isinstance(value, str):
            bytes = [ord(byte) & mask for byte in value]
            if bigendian:
                bytes.reverse()
        numeric_value = 0
        for shift, byte in zip(range(0, len(bytes)*bits, bits), bytes):
            numeric_value += byte << shift
        if isinstance(numeric_value, long):
            self = long.__new__(BitPaddedLong, numeric_value)
        else:
            self = int.__new__(BitPaddedInt, numeric_value)
        self.bits = bits
        self.bigendian = bigendian
        return self

    def as_str(value, bits=7, bigendian=True, width=4):
        bits = getattr(value, 'bits', bits)
        bigendian = getattr(value, 'bigendian', bigendian)
        value = int(value)
        mask = (1 << bits) - 1
        bytes = []
        while value:
            bytes.append(value & mask)
            value = value >> bits
        # PCNT and POPM use growing integers of at least 4 bytes as counters.
        if width == -1:
            width = max(4, len(bytes))
        if len(bytes) > width:
            raise ValueError('Value too wide (%d bytes)' % len(bytes))
        else:
            bytes.extend([0] * (width-len(bytes)))
        if bigendian:
            bytes.reverse()
        return ''.join(map(chr, bytes))

    to_str = staticmethod(as_str)


class BitPaddedLong(long):
    def as_str(value, bits=7, bigendian=True, width=4):
        return BitPaddedInt.to_str(value, bits, bigendian, width)

    to_str = staticmethod(as_str)
