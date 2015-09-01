# -*- coding: utf-8 -*-
# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write ASF (Window Media Audio) files."""

__all__ = ["ASF", "Open"]

import struct
from mutagen import FileType, Metadata, StreamInfo
from mutagen._util import resize_bytes, DictMixin
from mutagen._compat import string_types, xrange, long_, PY3

from ._util import error, ASFError, ASFHeaderError
from ._objects import BaseObject, HeaderObject, \
    MetadataLibraryObject, MetadataObject, ExtendedContentDescriptionObject, \
    HeaderExtensionObject, ContentDescriptionObject
from ._attrs import ASFGUIDAttribute, ASFWordAttribute, ASFQWordAttribute, \
    ASFDWordAttribute, ASFBoolAttribute, ASFByteArrayAttribute, \
    ASFUnicodeAttribute, ASFBaseAttribute, ASFValue


# pyflakes
error, ASFError, ASFHeaderError, ASFValue


class ASFInfo(StreamInfo):
    """ASF stream information.

    :ivar float length: Length in seconds
    :ivar int sample_rate: Sample rate in Hz
    :ivar int bitrate: Bitrate in bps
    :ivar int channels: Number of channels
    :ivar text codec_type: Name of the codec type of the first audio stream or
        an empty string if unknown. Example: "Windows Media Audio 9 Standard"
    :ivar text codec_name: Name and maybe version of the codec used. Example:
        "Windows Media Audio 9.1"
    :ivar text codec_description: Further information on the codec used.
        Example: "64 kbps, 48 kHz, stereo 2-pass CBR"
    """

    def __init__(self):
        self.length = 0.0
        self.sample_rate = 0
        self.bitrate = 0
        self.channels = 0
        self.codec_type = u""
        self.codec_name = u""
        self.codec_description = u""

    def pprint(self):
        """Returns a stream information text summary

        :rtype: text
        """

        s = u"ASF (%s) %d bps, %s Hz, %d channels, %.2f seconds" % (
            self.codec_type or self.codec_name or u"???", self.bitrate,
            self.sample_rate, self.channels, self.length)
        return s


class ASFTags(list, DictMixin, Metadata):
    """Dictionary containing ASF attributes."""

    def pprint(self):
        return "\n".join("%s=%s" % (k, v) for k, v in self)

    def __getitem__(self, key):
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__getitem__(self, key)

        values = [value for (k, value) in self if k == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    def __delitem__(self, key):
        """Delete all values associated with the key."""

        # PY3 only
        if isinstance(key, slice):
            return list.__delitem__(self, key)

        to_delete = [x for x in self if x[0] == key]
        if not to_delete:
            raise KeyError(key)
        else:
            for k in to_delete:
                self.remove(k)

    def __contains__(self, key):
        """Return true if the key has any values."""
        for k, value in self:
            if k == key:
                return True
        else:
            return False

    def __setitem__(self, key, values):
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__setitem__(self, key, values)

        if not isinstance(values, list):
            values = [values]

        to_append = []
        for value in values:
            if not isinstance(value, ASFBaseAttribute):
                if isinstance(value, string_types):
                    value = ASFUnicodeAttribute(value)
                elif PY3 and isinstance(value, bytes):
                    value = ASFByteArrayAttribute(value)
                elif isinstance(value, bool):
                    value = ASFBoolAttribute(value)
                elif isinstance(value, int):
                    value = ASFDWordAttribute(value)
                elif isinstance(value, long_):
                    value = ASFQWordAttribute(value)
                else:
                    raise TypeError("Invalid type %r" % type(value))
            to_append.append((key, value))

        try:
            del(self[key])
        except KeyError:
            pass

        self.extend(to_append)

    def keys(self):
        """Return all keys in the comment."""
        return self and set(next(iter(zip(*self))))

    def as_dict(self):
        """Return a copy of the comment data in a real dict."""
        d = {}
        for key, value in self:
            d.setdefault(key, []).append(value)
        return d


UNICODE = ASFUnicodeAttribute.TYPE
BYTEARRAY = ASFByteArrayAttribute.TYPE
BOOL = ASFBoolAttribute.TYPE
DWORD = ASFDWordAttribute.TYPE
QWORD = ASFQWordAttribute.TYPE
WORD = ASFWordAttribute.TYPE
GUID = ASFGUIDAttribute.TYPE


class ASF(FileType):
    """An ASF file, probably containing WMA or WMV."""

    _mimes = ["audio/x-ms-wma", "audio/x-ms-wmv", "video/x-ms-asf",
              "audio/x-wma", "video/x-wmv"]

    def load(self, filename):
        self.filename = filename
        with open(filename, "rb") as fileobj:
            self.size = 0
            self.size1 = 0
            self.size2 = 0
            self.offset1 = 0
            self.offset2 = 0
            self.num_objects = 0
            self.info = ASFInfo()
            self.tags = ASFTags()
            self.__read_file(fileobj)

    def save(self):
        # Move attributes to the right objects
        self.to_content_description = {}
        self.to_extended_content_description = {}
        self.to_metadata = {}
        self.to_metadata_library = []
        for name, value in self.tags:
            library_only = (value.data_size() > 0xFFFF or value.TYPE == GUID)
            can_cont_desc = value.TYPE == UNICODE

            if library_only or value.language is not None:
                self.to_metadata_library.append((name, value))
            elif value.stream is not None:
                if name not in self.to_metadata:
                    self.to_metadata[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            elif name in ContentDescriptionObject.NAMES:
                if name not in self.to_content_description and can_cont_desc:
                    self.to_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            else:
                if name not in self.to_extended_content_description:
                    self.to_extended_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))

        # Add missing objects
        if not self.content_description_obj:
            self.content_description_obj = \
                ContentDescriptionObject()
            self.objects.append(self.content_description_obj)
        if not self.extended_content_description_obj:
            self.extended_content_description_obj = \
                ExtendedContentDescriptionObject()
            self.objects.append(self.extended_content_description_obj)
        if not self.header_extension_obj:
            self.header_extension_obj = \
                HeaderExtensionObject()
            self.objects.append(self.header_extension_obj)
        if not self.metadata_obj:
            self.metadata_obj = \
                MetadataObject()
            self.header_extension_obj.objects.append(self.metadata_obj)
        if not self.metadata_library_obj:
            self.metadata_library_obj = \
                MetadataLibraryObject()
            self.header_extension_obj.objects.append(self.metadata_library_obj)

        # Render the header
        data = b"".join([obj.render(self) for obj in self.objects])
        data = (HeaderObject.GUID +
                struct.pack("<QL", len(data) + 30, len(self.objects)) +
                b"\x01\x02" + data)

        with open(self.filename, "rb+") as fileobj:
            size = len(data)
            resize_bytes(fileobj, self.size, size, 0)
            fileobj.seek(0)
            fileobj.write(data)

        self.size = size
        self.num_objects = len(self.objects)

    def __read_file(self, fileobj):
        header = fileobj.read(30)
        if len(header) != 30 or header[:16] != HeaderObject.GUID:
            raise ASFHeaderError("Not an ASF file.")

        self.extended_content_description_obj = None
        self.content_description_obj = None
        self.header_extension_obj = None
        self.metadata_obj = None
        self.metadata_library_obj = None

        self.size, self.num_objects = struct.unpack("<QL", header[16:28])
        self.objects = []
        self._tags = {}
        for i in xrange(self.num_objects):
            self.__read_object(fileobj)

        for guid in [ContentDescriptionObject.GUID,
                ExtendedContentDescriptionObject.GUID, MetadataObject.GUID,
                MetadataLibraryObject.GUID]:
            self.tags.extend(self._tags.pop(guid, []))
        assert not self._tags

    def __read_object(self, fileobj):
        guid, size = struct.unpack("<16sQ", fileobj.read(24))
        obj = BaseObject._get_object(guid)
        data = fileobj.read(size - 24)
        obj.parse(self, data, fileobj, size)
        self.objects.append(obj)

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(HeaderObject.GUID) * 2

Open = ASF
