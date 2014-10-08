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
from mutagen._compat import long_, text_type
from mutagen._util import cdata


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


class ElementSpec(object):
    """Specifies characteristics of an EBML element, including which
    element type to use, the name of the element to be created, whether
    the element is mandatory within the parent and whether multiple
    elements are allowed.
    """
    
    def __init__(self, id, name, element_type, range=None,
                 default=None, mandatory=True, multiple=False):
        self.id = id
        self.name = name
        self.type = element_type
        self.range = range
        self.default = default
        self.mandatory = mandatory
        self.multiple = multiple
        
    def create_element(self, e_id, d_size, data):
        """Creates a new element using this specification."""
        
        return self.type(e_id, d_size, data)
        

indentation = 0

class Element(object):
    def __init__(self, element_id, data_size, data):
        self.id = element_id
        self.data_size = data_size
        self.data = data


class VoidElement(Element):
    def read(self, dataobj):
        pass

class UnsignedInteger(long_, Element):
    def __new__(cls, element_id, data_size, data):
        # Pad the raw data to 8 octets
        value = (b'\x00'*8 + data)[-8:]
        return long_.__new__(UnsignedInteger, cdata.ulonglong_be(value))

    def write(self):
        self.data = cdata.to_ulonglong_be(self.val).strip(b'\x00')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class String(text_type, Element):
    def __new__(cls, element_id, data_size, data):
        return text_type.__new__(String, data.strip(b'\x00').decode('ascii'))

    def write(self):
        self.data = self.val.encode('ascii')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class UTF8String(text_type, Element):
    def __new__(cls, element_id, data_size, data):
        return text_type.__new__(UTF8String, data.strip(b'\x00').decode('utf-8'))

    def write(self):
        self.data = self.val.encode('utf-8')
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class Binary(bytes, Element):
    def __new__(cls, element_id, data_size, data):
        return bytes.__new__(Binary, data)

    def write(self):
        self.data = self.val
        self.data_size = len(data)
        return self.id.write() + self.data_size.write() + self.data

class MasterElement(Element):
    # Child elements, in format {ID: ElementSpec(id, name, type)}
    _child_specs = {}
    
    def __init__(self, element_id, data_size, data):
        super(MasterElement, self).__init__(element_id, data_size, data)

        self.children = []
        self.dataobj = io.BytesIO(data)
        self.read()

    def read(self):
        while 1:
            try:
                e_id, d_size, data = self.read_element()
            except EOFError:
                break

            spec = self._child_specs.get(e_id, None)
            if spec is None:
                # Append tuple indicating element was unrecognised, then
                # move on to the next element.
                self.children.append((e_id, d_size, data))
                continue
                
            if not spec.multiple:
                # Check that there are no elements with the same ID
                if any(child.id == spec.id for child in self.children):
                    raise Exception("Attempt to set multiple values for non multi element")

            self.children.append(spec.create_element(e_id, d_size, data))

        # Check that all mandatory elements are set, otherwise raise Exception
        mandatory_specs = [
            k for k,v in self._child_specs.items() if v.mandatory
        ]
                
        for child in self.children:
            if isinstance(child, Element):
                if child.id in mandatory_specs:
                    mandatory_specs.remove(child.id)
        
        if mandatory_specs:
            missing = ", ".join("0x{:02x}".format(m) for m in mandatory_specs)
            raise Exception("The following mandatory elements are missing: {}".format(missing))
            
        # Set attributes
        for child in self.children:
            if isinstance(child, Element):
                spec = self._child_specs[child.id]
                
                try:
                    existing_element = getattr(self, spec.name)
                except AttributeError:
                    if spec.multiple:
                        child = [child]
                        
                    setattr(self, spec.name, child)
                else:
                    # Since we know the children are all valid already,
                    # this must be a multi-element
                    existing_element.append(child)
                        
            

    def read_element(self):
        if self.dataobj.read(1):
            self.dataobj.seek(-1, 1)
        else:
            # Now that we know that stream hasn't ended, go back a byte
            raise EOFError

        e_id = ElementID(self.dataobj)
        data_size = DataSize(self.dataobj)
        data = self.dataobj.read(data_size)
        return e_id, data_size, data

    def write(self):
        """Calls write for all children, and concatenates the output into own
        write result.
        """

        #for e in _mandatory_elements:
        #for e in _optional_elements:
        raise NotImplementedError


class EBMLHeader(MasterElement):
    _child_specs = {
        0x4286: ElementSpec(0x4286, 'version', UnsignedInteger),
        0x42F7: ElementSpec(0x42F7, 'read_version', UnsignedInteger),
        0x42F2: ElementSpec(0x42F2, 'max_id_length', UnsignedInteger),
        0x42F3: ElementSpec(0x42F3, 'max_size_length', UnsignedInteger),
        0x4282: ElementSpec(0x4282, 'doc_type', String),
        0x4287: ElementSpec(0x4287, 'doc_type_version', UnsignedInteger),
        0x4285: ElementSpec(0x4285, 'doc_type_read_version',
                            UnsignedInteger),
    }

class Document(MasterElement):

    _child_specs = {
        0x1A45DFA3: ElementSpec(0x1A45DFA3, 'ebml', EBMLHeader,
                                multiple=True),
    }
    

    def __init__(self, fileobj):
        self.children = []

        self.dataobj = fileobj
        self.read()

    def write(self):
        pass
