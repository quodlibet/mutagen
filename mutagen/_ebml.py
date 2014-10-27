# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Ben Ockmore
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

from ._compat import long_, text_type
from mutagen._util import cdata, insert_bytes, delete_bytes


class EBMLParseError(Exception):
    pass


class Element(object):

    def __init__(self, _id, value):
        self.id = _id

        self.bytes_read = 0
        self.bytes_read = self._get_byte_difference()

    @staticmethod
    def _determine_vint_length(first_byte):
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

    @staticmethod
    def _read_vint_bytes(buf, unset_ld):
        data = bytearray(buf.read(1))

        if not data:
            raise ValueError("Could not read first byte of {}".format(buf))

        length_descriptor = Element._determine_vint_length(data[0])

        if length_descriptor:
            data.extend(buf.read(length_descriptor))

        # Unset length descriptor byte, if requested
        if unset_ld:
            data[0] &= (0x80 >> length_descriptor) - 1

        return data

    @staticmethod
    def _vint_length(vint):
        data = cdata.to_uint_be(vint)
        return len(data.lstrip(b'\x00'))

    @staticmethod
    def _read_id(buf):
        data = Element._read_vint_bytes(buf, unset_ld=False)

        if len(data) > 4:
            raise EBMLParseError("More than four bytes read for element ID.")

        # Pad to 4 bytes
        data[0:0] = b'\x00'*4
        data = data[-4:]

        return cdata.uint_be(bytes(data))

    @staticmethod
    def _write_id(buf, _id):
        data = cdata.to_uint_be(_id)
        buf.write(data.lstrip(b'\x00'))

    @staticmethod
    def _read_size(buf):
        data = Element._read_vint_bytes(buf, unset_ld=True)

        if len(data) > 8:
            raise EBMLParseError("More than eight bytes read for data size.")

        # Pad to 8 bytes
        data[0:0] = b'\x00'*8
        data = data[-8:]

        return cdata.ulonglong_be(bytes(data))

    @staticmethod
    def _write_size(buf, size):
        data = cdata.to_ulonglong_be(size)
        data = bytearray(data.lstrip(b'\x00'))
        length_descriptor = 0x80 >> (len(data) - 1)
        data[0] |= length_descriptor
        buf.write(data)

    def bytes_to_write(self):
        size = self.data_size
        return (Element._vint_length(self.id) +
                Element._vint_length(size) +
                size)

    def _get_byte_difference(self):
        return self.bytes_to_write() - self.bytes_read

    def _insert_or_delete_bytes(self, buf):
        difference = self._get_byte_difference()

        # Insert into or delete byte from dataobj at the current
        # position to make room for content
        if difference > 0:
            insert_bytes(buf, difference, buf.tell())
        elif difference < 0:
            delete_bytes(buf, -difference, buf.tell())

        self.bytes_read += difference

    def write(self, buf):
        self._insert_or_delete_bytes(buf)

        Element._write_id(buf, self.id)
        Element._write_size(buf, self.data_size)
        self._write_data(buf)

    @classmethod
    def from_buffer(cls, _id, size, buf):
        raise NotImplementedError

    def _write_data(self, buf):
        raise NotImplementedError

    @property
    def data_size(self):
        raise NotImplementedError


class UnsignedElement(long_, Element):

    def __new__(cls, _id, value):
        return long_.__new__(UnsignedElement, value)

    @classmethod
    def from_buffer(cls, _id, size, buf):
        data = buf.read(size)
        # Pad the raw data to 8 octets
        data = (b'\x00'*8 + data)[-8:]
        return cls(_id, cdata.ulonglong_be(data))

    def _write_data(self, buf):
        data = cdata.to_ulonglong_be(self).strip(b'\x00')
        buf.write(data)

    @property
    def data_size(self):
        return len(cdata.to_ulonglong_be(self).strip(b'\x00'))


class ASCIIElement(text_type, Element):
    def __new__(cls, _id, value):
        return text_type.__new__(ASCIIElement, value)

    @classmethod
    def from_buffer(cls, _id, size, buf):
        data = buf.read(size)
        return cls(_id, data.strip(b'\x00').decode('ascii'))

    def _write_data(self, buf):
        data = self.encode('ascii')
        buf.write(data)

    @property
    def data_size(self):
        return len(self.encode('ascii'))


class UTF8Element(text_type, Element):
    def __new__(cls, _id, value):
        return text_type.__new__(UTF8Element, value)

    @classmethod
    def from_buffer(cls, _id, size, buf):
        data = buf.read(size)
        return cls(_id, data.strip(b'\x00').decode('utf8'))

    def _write_data(self, buf):
        data = self.encode('utf8')
        buf.write(data)

    @property
    def data_size(self):
        return len(self.encode('utf8'))


class BinaryElement(bytes, Element):
    def __new__(cls, _id, value):
        return bytes.__new__(BinaryElement, value)

    @classmethod
    def from_buffer(cls, _id, size, buf):
        return cls(_id, buf.read(size))

    def _write_data(self, buf):
        buf.write(self)

    @property
    def data_size(self):
        return len(self)


class ElementSpec(object):
    """Specifies characteristics of an EBML element, including which
    element type to use, the name of the element to be created, whether
    the element is mandatory within the parent and whether multiple
    elements are allowed.
    """

    def __init__(self, _id, name, element_type, _range=None,
                 default=None, mandatory=True, multiple=False):
        self.id = _id
        self.name = name
        self.type = element_type
        self.range = _range
        self.default = default
        self.mandatory = mandatory
        self.multiple = multiple

    def create_element(self, e_id, d_size, dataobj):
        """Creates a new element using this specification."""

        return self.type.from_buffer(e_id, d_size, dataobj)


class MasterElement(Element):
    # Child elements, in format {ID: ElementSpec(...)}
    _child_specs = {}

    def __init__(self, _id):
        self._children = []

        super(MasterElement, self).__init__(_id, None)

    def _write_children(self, buf):
        # Since children insert or delete bytes as needed, no need to
        # resize file within MasterElement.write
        for child in self._children:
            # If the child was unrecognised, it can't have been
            # modified. Therefore, just skip this portion of the file.
            if isinstance(child, tuple):
                skip_size = child[1]
                buf.seek(skip_size, 1)
            else:
                child.write(buf)

    # Override _get_byte_difference to ignore changes in child length, which
    # are already dealt with when writing children
    def _get_byte_difference(self):
        return (Element._vint_length(self.id) +
                Element._vint_length(self.data_size) - self.bytes_read)

    def _check_mandatory_children(self):
        # Check that all mandatory elements are set, otherwise raise Exception
        mandatory_ids = [
            k for k, v in self._child_specs.items() if v.mandatory
        ]

        for child in self._children:
            if isinstance(child, Element):
                if child.id in mandatory_ids:
                    mandatory_ids.remove(child.id)

        if mandatory_ids:
            missing = ", ".join("0x{:02x}".format(m) for m in mandatory_ids)
            raise Exception("The following mandatory elements are "
                            "missing: {}".format(missing))

    def _set_attributes(self):
        # Set attributes
        for child in self._children:
            if not isinstance(child, Element):
                continue

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

    def _read(self, size, buf):
        bytes_read = 0
        while bytes_read < size:
            try:
                e_id = Element._read_id(buf)
            except EOFError:
                raise EBMLParseError('Not enough elements in EBML Master.')

            d_size = Element._read_size(buf)
            bytes_read += (Element._vint_length(e_id) +
                           Element._vint_length(d_size) + d_size)

            spec = self._child_specs.get(e_id, None)
            if spec is None:
                # Append tuple indicating element was unrecognised, then
                # move on to the next element.
                self._children.append((e_id, d_size))
                buf.seek(d_size, 1)
                continue

            if not spec.multiple:
                # Check that there are no elements with the same ID
                if any(child.id == spec.id for child in self._children):
                    raise Exception("Attempt to set multiple values for "
                                    "non-multi element")

            new_element = spec.create_element(e_id, d_size, buf)
            self._children.append(new_element)

        self._check_mandatory_children()
        self._set_attributes()

    @classmethod
    def from_buffer(cls, _id, size, buf):
        result = cls(_id)

        result._read(size, buf)
        return result

    def _write_data(self, buf):
        # Since children insert or delete bytes as needed, no need to
        # resize file within MasterElement.write
        for child in self._children:
            # If the child was unrecognised, it can't have been
            # modified. Therefore, just skip this portion of the file.
            if isinstance(child, tuple):
                skip_size = child[1]
                buf.seek(skip_size, 1)
            else:
                child.write(buf)

    @property
    def data_size(self):
        return sum(child.bytes_to_write() for child in self._children)


class EBMLHeader(MasterElement):
    _child_specs = {
        0x4286: ElementSpec(0x4286, 'ebml_version', UnsignedElement),
        0x42F7: ElementSpec(0x42F7, 'ebml_read_version', UnsignedElement),
        0x42F2: ElementSpec(0x42F2, 'ebml_max_id_length', UnsignedElement),
        0x42F3: ElementSpec(0x42F3, 'ebml_max_size_length', UnsignedElement),
        0x4282: ElementSpec(0x4282, 'doc_type', ASCIIElement),
        0x4287: ElementSpec(0x4287, 'doc_type_version', UnsignedElement),
        0x4285: ElementSpec(0x4285, 'doc_type_read_version', UnsignedElement),
    }


class Document(MasterElement):

    _child_specs = {
        0x1A45DFA3: ElementSpec(0x1A45DFA3, 'ebml', EBMLHeader, multiple=True),
    }

    def __init__(self, buf):
        super(Document, self).__init__(_id)

        buf.seek(0, 2)
        size = buf.tell()
        buf.seek(0)

        self._read(size, buf)

    def write(self, buf):
        # This function assumes the fileobj can be written to.
        # Move back to the start of the file.
        buf.seek(0)
        # Carry out a standard MasterElement write.
        self._write_data(buf)
