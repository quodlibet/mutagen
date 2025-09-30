import os
import struct
from io import BytesIO

EBML_HEADER = 0x1A45DFA3
SEGMENT = 0x18538067
SEEK_HEAD = 0x114D9B74
INFO = 0x1549A966
TAGS = 0x1254C367
SEEK = 0x4DBB
SEEK_ID = 0x53AB
SEEK_POSITION = 0x53AC
TITLE = 0x7BA9
TAG = 0x7373
SIMPLE_TAG = 0x67C8
TAG_NAME = 0x45A3
TAG_STRING = 0x4487
TAG_BINARY = 0x4485


def _read_vint_raw(stream):
    first_byte_data = stream.read(1)
    if not first_byte_data:
        raise IOError("Reached end of stream while reading VINT")
    first_byte = first_byte_data[0]

    width = 0
    for i in range(8):
        if (first_byte >> (7 - i)) & 1:
            width = i + 1
            break
    else:
        raise ValueError("Invalid VINT start byte")

    data = bytes([first_byte]) + stream.read(width - 1)
    if len(data) < width:
        raise IOError("Reached end of stream while reading VINT data")

    value = int.from_bytes(data, 'big')
    return value, width


def _read_vint_value(stream):
    first_byte_data = stream.read(1)
    if not first_byte_data:
        raise IOError("Reached end of stream while reading VINT")
    first_byte = first_byte_data[0]

    width = 0
    for i in range(8):
        if (first_byte >> (7 - i)) & 1:
            width = i + 1
            break
    else:
        raise ValueError("Invalid VINT start byte")

    data = bytes([first_byte]) + stream.read(width - 1)
    if len(data) < width:
        raise IOError("Reached end of stream while reading VINT data")

    value = data[0] & ((1 << (8 - width)) - 1)
    for i in range(1, width):
        value = (value << 8) | data[i]

    return value, width


def _write_vint_size(value):
    if value < (2**7) - 1:
        return (value | 0x80).to_bytes(1, 'big')
    elif value < (2**14) - 1:
        return (value | 0x4000).to_bytes(2, 'big')
    elif value < (2**21) - 1:
        return (value | 0x200000).to_bytes(3, 'big')
    elif value < (2**28) - 1:
        return (value | 0x10000000).to_bytes(4, 'big')
    elif value < (2**35) - 1:
        return (value | 0x0800000000).to_bytes(5, 'big')
    elif value < (2**42) - 1:
        return (value | 0x040000000000).to_bytes(6, 'big')
    elif value < (2**49) - 1:
        return (value | 0x02000000000000).to_bytes(7, 'big')
    elif value < (2**56) - 1:
        return (value | 0x0100000000000000).to_bytes(8, 'big')
    else:
        raise ValueError("VINT size too large")


def _write_element(element_id, data):
    id_bytes = element_id.to_bytes(4, 'big')
    if element_id < 0x1000000:
        id_bytes = id_bytes[1:]
    if element_id < 0x10000:
        id_bytes = id_bytes[1:]
    if element_id < 0x100:
        id_bytes = id_bytes[1:]
    return id_bytes + _write_vint_size(len(data)) + data


def _iter_elements(stream, end_pos=None):
    while end_pos is None or stream.tell() < end_pos:
        current_pos = stream.tell()
        try:
            element_id, id_len = _read_vint_raw(stream)
            size, size_len = _read_vint_value(stream)
        except (IOError, ValueError):
            break

        data_pos = stream.tell()
        if end_pos is not None and data_pos + size > end_pos:
            break

        yield element_id, stream.read(size)
        stream.seek(current_pos + id_len + size_len + size)


class MKVTags(dict):
    def __setitem__(self, key, value):
        if not isinstance(value, list):
            value = [value]
        super().__setitem__(key.upper(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.upper())

    def add_tag(self, key, value):
        key = key.upper()
        if key in self:
            super().__getitem__(key).append(value)
        else:
            # Creates the initial list
            super().__setitem__(key, [value])


class MKVFile:
    def __init__(self, filename):
        self.filename = filename
        self.tags = MKVTags()
        self._load()

    def _load(self):
        with open(self.filename, 'rb') as f:
            header_id_bytes = f.read(4)
            if not header_id_bytes or int.from_bytes(header_id_bytes, 'big') != EBML_HEADER:
                return

            try:
                header_size, _ = _read_vint_value(f)
                f.seek(header_size, 1)
            except (IOError, ValueError):
                return

            try:
                segment_pos = f.tell()
                segment_id_val, id_len = _read_vint_raw(f)
                segment_size, size_len = _read_vint_value(f)
                if segment_id_val != SEGMENT:
                    return
                segment_data_pos = f.tell()
            except (IOError, ValueError):
                return

            tags_pos, info_pos = None, None
            f.seek(segment_data_pos)
            for eid, edata in _iter_elements(f, end_pos=segment_data_pos + 4096):
                if eid == SEEK_HEAD:
                    for seek_id, seek_data in _iter_elements(BytesIO(edata)):
                        if seek_id == SEEK:
                            s_id, s_pos = None, None
                            for sub_id, sub_data in _iter_elements(BytesIO(seek_data)):
                                if sub_id == SEEK_ID: s_id = int.from_bytes(sub_data, 'big')
                                elif sub_id == SEEK_POSITION: s_pos = int.from_bytes(sub_data, 'big')
                            if s_id == TAGS: tags_pos = segment_data_pos + s_pos
                            elif s_id == INFO: info_pos = segment_data_pos + s_pos
                    break

            if info_pos is not None:
                f.seek(info_pos)
                try:
                    info_id, info_data = next(_iter_elements(f))
                    if info_id == INFO: self._parse_info(info_data)
                    else: info_pos = None
                except (StopIteration, IOError, ValueError): info_pos = None

            tags_data = None
            if tags_pos is not None:
                f.seek(tags_pos)
                try:
                    tags_id, tags_data_read = next(_iter_elements(f))
                    if tags_id == TAGS: tags_data = tags_data_read
                except (StopIteration, IOError, ValueError): pass
            if tags_data is None or info_pos is None:
                f.seek(segment_data_pos)
                scan_end_pos = min(segment_data_pos + segment_size, segment_data_pos + 10 * 1024 * 1024)
                for eid, edata in _iter_elements(f, scan_end_pos):
                    if eid == TAGS and tags_data is None: tags_data = edata
                    elif eid == INFO and info_pos is None:
                         self._parse_info(edata)
                         info_pos = True
                    if tags_data is not None and info_pos is not None: break

            if tags_data:
                self._parse_tags_element(tags_data)

    def _parse_info(self, info_data):
        for eid, edata in _iter_elements(BytesIO(info_data)):
            if eid == TITLE:
                self.tags.add_tag('TITLE', edata.decode('utf-8', 'replace'))
                break

    def _parse_tags_element(self, tags_data):
        for eid, edata in _iter_elements(BytesIO(tags_data)):
            if eid == TAG:
                self._parse_tag(edata)

    def _parse_tag(self, tag_data):
        for eid, edata in _iter_elements(BytesIO(tag_data)):
            if eid == SIMPLE_TAG:
                self._parse_simple_tag_recursive(edata)

    def _parse_simple_tag_recursive(self, simple_tag_data):
        tag_name, tag_value = None, None
        nested_tags_data = []

        for eid, edata in _iter_elements(BytesIO(simple_tag_data)):
            if eid == TAG_NAME: tag_name = edata.decode('utf-8', 'replace')
            elif eid == TAG_STRING: tag_value = edata.decode('utf-8', 'replace')
            elif eid == TAG_BINARY: tag_value = edata
            elif eid == SIMPLE_TAG: nested_tags_data.append(edata)

        if tag_name and tag_value is not None:
            self.tags.add_tag(tag_name, tag_value)

        for nested_data in nested_tags_data:
            self._parse_simple_tag_recursive(nested_data)

    def add_tags(self):
        if not self.tags:
            self.tags = MKVTags()

    def delete(self, filename=None):
        if filename is None:
            filename = self.filename
        self.tags.clear()
        self.save(filename, delete_tags=True)

    def _render_tags(self):
        tags_payload = b""
        if self.tags:
            for key, values in sorted(self.tags.items()):
                for v in values:
                    simple_tag_payload = b""
                    simple_tag_payload += _write_element(TAG_NAME, key.encode('utf-8'))
                    if isinstance(v, str):
                        simple_tag_payload += _write_element(TAG_STRING, v.encode('utf-8'))
                    elif isinstance(v, bytes):
                        simple_tag_payload += _write_element(TAG_BINARY, v)
                    else:
                        continue
                    tags_payload += _write_element(TAG, _write_element(SIMPLE_TAG, simple_tag_payload))
        return _write_element(TAGS, tags_payload) if tags_payload else b""

    def save(self, filename=None, delete_tags=False):
        if filename is None:
            filename = self.filename
        
        temp_filename = filename + ".tmp"

        with open(self.filename, 'rb') as f_in, open(temp_filename, 'wb') as f_out:
            f_in.seek(0)
            ebml_header_end = 0
            try:
                eid, id_len = _read_vint_raw(f_in)
                if eid != EBML_HEADER: raise ValueError("No EBML Header")
                size, size_len = _read_vint_value(f_in)
                ebml_header_end = f_in.tell() + size
                f_in.seek(0)
                f_out.write(f_in.read(ebml_header_end))
            except (IOError, ValueError) as e:
                raise IOError(f"Cannot read MKV file structure: {e}")
            f_in.seek(ebml_header_end)
            segment_data_start_pos = 0
            try:
                eid, id_len = _read_vint_raw(f_in)
                if eid != SEGMENT: raise ValueError("No Segment found after EBML Header")
                f_out.write(eid.to_bytes(4, 'big'))
                f_out.write(b'\x01\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
                _, size_len = _read_vint_value(f_in)
                segment_data_start_pos = f_in.tell()
            except (IOError, ValueError):
                raise IOError("Could not find or parse Segment element")
            new_tags_element = b""
            if self.tags and not delete_tags:
                new_tags_element = self._render_tags()

            tags_element_start_pos = -1
            tags_element_len = 0
            insert_pos = -1

            f_in.seek(segment_data_start_pos)
            try:
                current_pos = f_in.tell()
                eid, id_len = _read_vint_raw(f_in)
                size, size_len = _read_vint_value(f_in)
                insert_pos = current_pos + id_len + size_len + size

                f_in.seek(segment_data_start_pos)
                while True:
                    element_start = f_in.tell()
                    try:
                        eid, id_len = _read_vint_raw(f_in)
                        size, size_len = _read_vint_value(f_in)
                    except (IOError, ValueError): break

                    if eid == TAGS:
                        tags_element_start_pos = element_start
                        tags_element_len = id_len + size_len + size
                        break
                    f_in.seek(element_start + id_len + size_len + size)
            except (IOError, ValueError):
                 insert_pos = segment_data_start_pos
            f_in.seek(segment_data_start_pos)
            if tags_element_start_pos != -1:
                bytes_before = tags_element_start_pos - segment_data_start_pos
                f_out.write(f_in.read(bytes_before))
                f_out.write(new_tags_element)
                f_in.seek(tags_element_start_pos + tags_element_len)
                f_out.write(f_in.read())
            elif insert_pos != -1:
                bytes_before = insert_pos - segment_data_start_pos
                f_out.write(f_in.read(bytes_before))
                f_out.write(new_tags_element)
                f_out.write(f_in.read())
            else:
                 f_out.write(new_tags_element)
                 f_out.write(f_in.read())

        os.replace(temp_filename, filename)