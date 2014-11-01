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

from ._compat import integer_types, long_, text_type
from ._util import cdata, delete_bytes, insert_bytes


class EBMLParseError(Exception):
    pass


class ElementHeader(object):
    def __init__(self, _id, size, num_read_bytes=0):
        self._id = _id
        self._size = size
        self._num_read_bytes = num_read_bytes

    @property
    def id(self):
        return self._id

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        if not isinstance(value, integer_types):
            raise ValueError("ElementHeader.size must be an integer "
                             "type.")

        self._size = value

    @classmethod
    def read(cls, buf):
        _id, _id_bytes = cls._read_id(buf)
        _size, _size_bytes = cls._read_size(buf)

        return cls(_id, _size, _id_bytes + _size_bytes)

    def write(self, buf):
        self._insert_or_delete_bytes(buf)
        self._write_id(buf)
        self._write_size(buf)

    @property
    def num_read_bytes(self):
        return self._num_read_bytes

    @property
    def num_write_bytes(self):
        return self._id_length() + self._size_length()

    def byte_difference(self):
        return self.num_write_bytes - self.num_read_bytes

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

    @classmethod
    def _get_vint_bytes(cls, buf, unset_ld):
        data = bytearray(buf.read(1))

        if not data:
            raise ValueError("Could not read first byte of {}".format(buf))

        length_descriptor = cls._determine_vint_length(data[0])

        if length_descriptor:
            data.extend(buf.read(length_descriptor))

        # Unset length descriptor byte, if requested
        if unset_ld:
            data[0] &= (0x80 >> length_descriptor) - 1

        return data

    @classmethod
    def _read_id(cls, buf):
        data = cls._get_vint_bytes(buf, unset_ld=False)

        if len(data) > 4:
            raise EBMLParseError("More than four bytes read for element ID.")

        read_length = len(data)

        # Pad to 4 bytes
        data[0:0] = b'\x00'*4
        data = data[-4:]

        return cdata.uint_be(bytes(data)), read_length

    def _write_id(self, buf):
        data = cdata.to_uint_be(self._id)
        buf.write(data.lstrip(b'\x00'))

    def _id_length(self):
        data = cdata.to_uint_be(self.id)
        return len(data.lstrip(b'\x00'))

    @classmethod
    def _read_size(cls, buf):
        data = cls._get_vint_bytes(buf, unset_ld=True)

        if len(data) > 8:
            raise EBMLParseError("More than eight bytes read for data size.")

        read_length = len(data)

        # Pad to 8 bytes
        data[0:0] = b'\x00'*8
        data = data[-8:]

        return cdata.ulonglong_be(bytes(data)), read_length

    def _write_size(self, buf):

        target_size = self._size_length()

        data = cdata.to_ulonglong_be(self._size)
        data = bytearray(data)
        # Data should be padded to the target_size - since this is at minimum
        # the size of the useful data, no need to worry about truncating
        data[0:0] = b'\x00' * target_size
        del data[:-target_size]

        length_descriptor = 0x80 >> (len(data) - 1)
        data[0] |= length_descriptor

        buf.write(data)

    def _size_length(self):
        data = cdata.to_ulonglong_be(self._size)
        data = bytearray(data.lstrip(b'\x00'))
        length_descriptor = 0x80 >> (len(data) - 1)

        if data[0] >= length_descriptor:
            data_length = len(data) + 1
        else:
            data_length = len(data)

        return max(data_length, self.num_read_bytes - self._id_length())

    def _insert_or_delete_bytes(self, buf):
        difference = self.byte_difference()

        # Insert into or delete byte from dataobj at the current
        # position to make room for content
        if difference > 0:
            insert_bytes(buf, difference, buf.tell())
        elif difference < 0:
            delete_bytes(buf, -difference, buf.tell())

        self._num_read_bytes = self.num_write_bytes


class Element(object):

    def __init__(self, header, value, num_read_bytes=0):
        self._header = header

        self._num_read_bytes = num_read_bytes

    @classmethod
    def read(cls, header, buf):
        raise NotImplementedError

    def write(self, buf):
        # Update Element size to reflect changes in content
        self._header.size = self.num_write_bytes
        self._header.write(buf)
        self._insert_or_delete_bytes(buf)
        self._write_data(buf)

    def _write_data(self, buf):
        raise NotImplementedError

    @property
    def id(self):
        return self._header.id

    @property
    def size(self):
        return self._header.size

    @property
    def num_read_bytes(self):
        return self._num_read_bytes

    @property
    def num_write_bytes(self):
        raise NotImplementedError

    def byte_difference(self):
        return self.num_write_bytes - self._num_read_bytes

    def _insert_or_delete_bytes(self, buf):
        difference = self.byte_difference()

        # Insert into or delete byte from dataobj at the current
        # position to make room for content
        if difference > 0:
            insert_bytes(buf, difference, buf.tell())
        elif difference < 0:
            delete_bytes(buf, -difference, buf.tell())

        self._num_read_bytes = self.num_write_bytes


class UnsignedElement(long_, Element):

    def __new__(cls, header, value, num_read_bytes=0):
        return long_.__new__(UnsignedElement, value)

    @classmethod
    def read(cls, header, buf):
        data = buf.read(header.size)
        # Pad the raw data to 8 octets
        data = (b'\x00'*8 + data)[-8:]
        return cls(header, cdata.ulonglong_be(data), header.size)

    def _write_data(self, buf):
        data = cdata.to_ulonglong_be(self).strip(b'\x00')
        buf.write(data)

    @property
    def num_write_bytes(self):
        return len(cdata.to_ulonglong_be(self).strip(b'\x00'))


class ASCIIElement(text_type, Element):
    def __new__(cls, header, value, num_read_bytes=0):
        return text_type.__new__(ASCIIElement, value)

    @classmethod
    def read(cls, header, buf):
        data = buf.read(header.size)
        return cls(header, data.strip(b'\x00').decode('ascii'), header.size)

    def _write_data(self, buf):
        data = self.encode('ascii')
        buf.write(data)

    @property
    def num_write_bytes(self):
        return len(self.encode('ascii'))


class UTF8Element(text_type, Element):
    def __new__(cls, header, value, num_read_bytes=0):
        return text_type.__new__(UTF8Element, value)

    @classmethod
    def read(cls, header, buf):
        data = buf.read(header.size)
        return cls(header, data.strip(b'\x00').decode('utf8'), header.size)

    def _write_data(self, buf):
        data = self.encode('utf8')
        buf.write(data)

    @property
    def num_write_bytes(self):
        return len(self.encode('utf8'))


class BinaryElement(bytes, Element):
    def __new__(cls, header, value, num_read_bytes=0):
        return bytes.__new__(BinaryElement, value)

    @classmethod
    def read(cls, header, buf):
        return cls(header, buf.read(header.size), header.size)

    def _write_data(self, buf):
        buf.write(self)

    @property
    def num_write_bytes(self):
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

    def create_element(self, header, buf):
        """Creates a new element using this specification."""

        return self.type.read(header, buf)


class MasterElement(Element):
    # Child elements, in format {ID: ElementSpec(...)}
    _child_specs = {}

    def __init__(self, header, num_read_bytes=0):
        self._children = []

        super(MasterElement, self).__init__(header, None,
                                            num_read_bytes=num_read_bytes)

    @classmethod
    def read(cls, header, buf):
        result = cls(header, header.size)
        result._read_children(buf)

        return result

    def _write_data(self, buf):
        # Since children insert or delete bytes as needed, no need to
        # resize file within MasterElement.write
        for child in self._children:
            # If the child was unrecognised, it can't have been
            # modified. Therefore, just skip this portion of the file.
            if isinstance(child, ElementHeader):
                buf.seek(child.size, 1)
            else:
                child.write(buf)

    @property
    def num_write_bytes(self):
        result = 0
        for chld in self._children:
            if isinstance(chld, Element):
                result += (chld.num_write_bytes + chld._header.num_write_bytes)
            else:
                result += (chld.size + chld.num_write_bytes)

        return result

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

    def _read_children(self, buf):
        bytes_read = 0
        while bytes_read < self.size:
            try:
                header = ElementHeader.read(buf)
            except EOFError:
                raise EBMLParseError('Not enough elements in EBML Master.')

            bytes_read += header.num_read_bytes

            spec = self._child_specs.get(header.id, None)
            if spec is None:
                # Append ElementHeader, indicating element was unrecognised,
                # then move on to the next element.
                self._children.append(header)
                buf.seek(header.size, 1)
            else:
                if not spec.multiple:
                    # Check that there are no elements with the same ID
                    if any(child.id == spec.id for child in self._children):
                        raise Exception("Attempt to set multiple values for "
                                        "non-multi element")

                new_element = spec.create_element(header, buf)
                self._children.append(new_element)

            bytes_read += header.size

        self._check_mandatory_children()
        self._set_attributes()

    # Override byte_difference to ignore changes in child length, which are
    # already dealt with when writing children
    def byte_difference(self):
        return 0


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
