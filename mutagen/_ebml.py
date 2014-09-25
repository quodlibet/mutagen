# -*- coding: utf-8 -*-
#
# Copyright 2014 Ben Ockmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""EBML document parser.

This module provides parsing for only the barebones tags specified by the EBML
specification at:

    http://ebml.sourceforge.net/specs/

For an example of how to use it for specific formats, see the matroska.py file.
"""

import io
from mutagen._compat import long_
from mutagen._util import cdata

class VoidElement(object):
    def read(self, dataobj):
        pass

_global_ignored_elements = {
    0xEC: "void"
}


class EBMLParseError(Exception):
    pass


class VariableIntMixin(object):
    @staticmethod
    def _get_required_bytes(fileobj, unset_ld):
        data = bytearray(fileobj.read(1))

        if not data:
            print(fileobj.getvalue())
            print(data[0])
            raise ValueError("Could not read first byte of {}".format(fileobj))

        length_descriptor = VariableIntMixin._determine_length(data[0])

        if length_descriptor:
            data.extend(fileobj.read(length_descriptor))

        # Unset length descriptor byte, if requested
        if unset_ld:
            data[0] &= (0x80 >> length_descriptor) - 1

        return data

    @staticmethod
    def _determine_length(first_byte):
        if first_byte == 0x0:
            raise ValueError("Must be a bit set in the first byte")

        bval = 0
        if first_byte & 0b11110000:
            first_byte = first_byte >> 4
            bval += 4
        if first_byte & 0b00001100:
            first_byte = first_byte >> 2
            bval += 2
        if first_byte & 0b00000010:
            bval += 1

        return 7-bval

class ElementID(int, VariableIntMixin):
    def __new__(cls, fileobj):
        data = cls._get_required_bytes(fileobj, unset_ld=False)

        if len(data) > 4:
            raise EBMLParseError("More than four bytes read for element ID.")

        # Pad to 4 bytes
        data[0:0] = b'\x00'*4
        data = data[-4:]

        # Get integer value
        return int.__new__(ElementID, cdata.uint_be(data))

    def write(self):
        data = cdata.to_uint_be(self)
        return data.lstrip(b'\x00')

class DataSize(long_, VariableIntMixin):
    def __new__(cls, fileobj):
        data = cls._get_required_bytes(fileobj, unset_ld=True)

        if len(data) > 8:
            raise EBMLParseError("More than eight bytes read for data size.")

        # Pad to 8 bytes
        data[0:0] = b'\x00'*8
        data = data[-8:]

        # Get 64-bit integer value
        return long_.__new__(DataSize, cdata.ulonglong_be(data))

    def write(self):
        data = cdata.to_ulonglong_be(self)
        data = bytearray(data.lstrip(b'\x00'))
        length_descriptor = 0x80 >> (len(data) - 1)
        data[0] |= length_descriptor
        return bytes(data)


class UnsignedInteger(object):
    def __init__(self, document, element_id, data_size, data):
        self.id = element_id
        self.data_size = data_size

        # Pad the raw data to 8 octets
        data = (b'\x00'*8 + data)[-8:]
        self.val = cdata.ulonglong_be(data)

    def write(self):
        self.data = cdata.to_ulonglong_be(self.val).strip(b'\x00')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class String(object):
    def __init__(self, document, element_id, data_size, data):
        self.id = element_id
        self.data_size = data_size

        self.val = data.strip(b'\x00').decode('ascii')

    def write(self):
        self.data = self.val.encode('ascii')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class UTF8String(object):
    def __init__(self, document, element_id, data_size, data):
        self.id = element_id
        self.data_size = data_size

        self.val = data.strip(b'\x00').decode('utf-8')

    def write(self):
        self.data = self.val.encode('utf-8')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class Binary(object):
    def __init__(self, document, element_id, data_size, data):
        self.id = element_id
        self.data_size = data_size

        self.val = data

    def write(self):
        self.data = self.val
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class MasterElement(object):
    # Child elements, in format {ID: (name (string), (type), multi (bool))}
    _mandatory_elements = {}

    _optional_elements = {}

    _ignored_elements = {}

    def __init__(self, document, element_id, data_size, data):
        self.document = document
        self.element_id = element_id
        self.data_size = data_size

        dataobj = io.BytesIO(data)
        self.read(dataobj)

    def read(self, dataobj, root=False):
        while 1:
            try:
                e_id, d_size, data = self.document.read_element(dataobj)
            except EOFError:
                break

            if e_id in self._mandatory_elements:
                e_name, e_type, multi = self._mandatory_elements[e_id]
            elif e_id in self._optional_elements:
                e_name, e_type, multi = self._optional_elements[e_id]
            elif (e_id in self._ignored_elements) or (e_id in _global_ignored_elements):
                continue
            else:
                # Raise exception, since element ID is not valid in this master
                if root:
                    raise EOFError("End of EBML document.")
                else:
                    raise EBMLParseError("Element ID {:02X} in {} not recognized.".format(e_id, type(self)))

            new_element = e_type(self.document, e_id, d_size, data)

            # Test whether element has already been set
            try:
                existing_element = getattr(self, e_name)
            except AttributeError:
                setattr(self, e_name, [new_element])
            else:
                # Check that this element can be multi-set
                if multi:
                    existing_element.append(new_element)
                else:
                    # if not, raise exception
                    raise Exception("Attempt to set multiple values for non multi element")

        for e in self._mandatory_elements.values():
            # Check that all mandatory elements are set, otherwise raise Exception
            if not hasattr(self, e[0]):
                raise Exception("{} is mandatory but not set!".format(e[0]))

    def write(self):
        """Calls write for all children, and concatenates the output into own
        write result.
        """

        #for e in _mandatory_elements:
        #for e in _optional_elements:
        raise NotImplementedError


class EBMLHeader(MasterElement):
    _mandatory_elements = {
        0x4286: ("version", UnsignedInteger, False),
        0x42F7: ("read_version", UnsignedInteger, False),
        0x42F2: ("max_id_length", UnsignedInteger, False),
        0x42F3: ("max_size_length", UnsignedInteger, False),
        0x4282: ("doc_type", String, False),
        0x4287: ("doc_type_version", UnsignedInteger, False),
        0x4285: ("doc_type_read_version", UnsignedInteger, False),
    }

class Document(MasterElement):

    _mandatory_elements = {
        0x1A45DFA3: ("ebml", EBMLHeader, True),
    }

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.document = self

        try:
            self.read(self.fileobj)
        except EOFError:
            # This means that no more valid tags were found - stop parsing.
            pass

    def read_element(self, dataobj=None):
        if dataobj is None:
            dataobj = self.fileobj

        if dataobj.read(1):
            dataobj.seek(-1, 1)
        else:
            # Now that we know that stream hasn't ended, go back a byte
            raise EOFError

        e_id = ElementID(dataobj)
        data_size = DataSize(dataobj)
        data = dataobj.read(data_size)
        return e_id, data_size, data
