
import mutagen
import io
from mutagen._util import insert_bytes, delete_bytes, DictProxy, cdata
from mutagen._compat import long_

from mutagen.ebml import Document, MasterElement, EBMLHeader, UTF8String, String, UnsignedInteger, Binary

class SimpleTag(MasterElement):
    _mandatory_elements = {
        0x45A3: ('tag_name', UTF8String, False),
    }

    _optional_elements = {
        0x447A: ('tag_language', String, False),
        0x4484: ('tag_default', UnsignedInteger, False),
        0x4487: ('tag_string', UTF8String, False),
        0x4485: ('tag_binary', Binary, False),
    }

class Targets(MasterElement):
    _optional_elements = {
        0x68CA: ('target_type_value', UnsignedInteger, False),
        0x63CA: ('target_type', String, False),
        0x63C5: ('tag_track_uid', UnsignedInteger, False),
        0x63C9: ('tag_edition_uid', UnsignedInteger, False),
        0x63C4: ('tag_chapter_uid', UnsignedInteger, False),
        0x63C6: ('tag_attachment_uid', UnsignedInteger, False),
    }


class Tag(MasterElement):
    _mandatory_elements = {
        0x63C0: ('targets', Targets, False),
        0x67C8: ('simple_tag', SimpleTag, True),
    }


class Tags(MasterElement):
    _mandatory_elements = {
        0x7373: ("tag", Tag, True),
    }


class Segment(MasterElement):
    _ignored_elements = {
        0x114D9B74: "seek_head",
        0x1549A966: "info",
        0x1F43B675: "cluster",
        0x1654AE6B: "tracks",
        0x1C53BB6B: "cues",
        0x1941A469: "attachments",
        0x1043A770: "chapters",
    }

    _optional_elements = {
        0x1254C367: ("tags", Tags, True),
    }

class MatroskaDocument(Document):
    _mandatory_elements = {
        0x1A45DFA3: ("ebml", EBMLHeader, True),
        0x18538067: ("segment", Segment, True),
    }

#http://www.matroska.org/technical/specs/index.html


__all__ = ['MKATag', 'MKAFileType', 'Open']

class MKATag(DictProxy, mutagen.Metadata):

    def __init__(self, *args, **kwargs):
        super(MKATag, self).__init__(*args, **kwargs)

Open = MKATag


class Element(object):
    def __init__(self, fileobj):
        self.id = ElementID(fileobj)
        self.data_size = DataSize(fileobj)
        self.raw_data = fileobj.read(self.data_size)

    def write(self):
        return self.id.write() + self.data_size.write() + self.raw_data

class UnsignedInteger(Element):
    def __init__(self, fileobj):
        super(UnsignedInteger, self).__init__(fileobj)

        # Pad the raw data to 8 octets
        data = (b'\x00'*8 + self.raw_data)[-8:]
        self.val = cdata.ulonglong_be(data)

class String(Element):
    def __init__(self, fileobj):
        super(String, self).__init__(fileobj)

        self.val = self.raw_data

class EBML(Element):
    def __init__(self, fileobj):
        super(EBML, self).__init__(fileobj)
        data_stream = io.BytesIO(self.raw_data)
        self.version = UnsignedInteger(data_stream)
        self.read_version = UnsignedInteger(data_stream)
        self.max_id_length = UnsignedInteger(data_stream)
        self.max_size_length = UnsignedInteger(data_stream)
        self.doc_type = String(data_stream)
        self.doc_type_version = UnsignedInteger(data_stream)
        self.doc_type_read_version = UnsignedInteger(data_stream)


class MKAFileType(mutagen.FileType):
    @staticmethod
    def score(filename, fileobj, header_data):
        return header_data.startswith(b'\x1a\x45\xdf\xa3')



    """def parse_tag(data):
        tag_name_id = data[0:2]
        if tag_name_id != b'\x45\xa3':
            return
        tag_name_length ="""


    def read_header(self, fileobj):
        data = fileobj.read(4)

        length = self._read_length(fileobj)[0]
        fileobj.read(length)


        section_id = fileobj.read(4)
        length = self._read_length(fileobj)[0]
        while section_id != b"\x18\x53\x80\x67":
            fileobj.read(length)
            section_id = fileobj.read(4)
            if not section_id:
                raise ValueError

            length = self._read_length(fileobj)[0]

        print("Segment found, with length: {}!".format(length))

        while 1:
            section_id = fileobj.read(4)
            if not section_id:
                raise ValueError

            print([hex(ord(x)) for x in section_id])
            length = self._read_length(fileobj)[0]
            if section_id == '\x12\x54\xc3\x67':
                print("Tags found! Length: {}".format(length))
                break

            fileobj.read(length)

        tags_length = length
        read = 0
        while read < tags_length:
            tag = fileobj.read(2)
            if tag != '\x73\x73':
                return

            tag_length, length_bytes_read = self._read_length(fileobj)

            l2_read = 0
            while l2_read < tag_length:
                level_3 = fileobj.read(2)
                if level_3 == b'\x63\xc0':
                    length, l2_len_bytes_read = self._read_length(fileobj)
                    fileobj.read(length)
                elif level_3 == b'\x67\xc8':
                    length, l2_len_bytes_read = self._read_length(fileobj)
                    fileobj.read(length)
                    print("SimpleTag ({})".format(length))
                l2_read += length + 2 + l2_len_bytes_read

            print("Tag ({})".format(tag_length + length_bytes_read + 2))
            read += tag_length + length_bytes_read + 2

    def load(self, filename, **kwargs):
        print filename
        fileobj = open(filename, "rb")
        self.read_header(fileobj)


