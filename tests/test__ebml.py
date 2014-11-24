
import io

from mutagen._ebml import (ASCIIElement, BinaryElement, Document, EBMLHeader,
                           ElementHeader, MasterElement, UnsignedElement,
                           UTF8Element)
from tests import add, TestCase


class TElementHeader(TestCase):

    def test_read_id(self):
        one = io.BytesIO(b'\xBF')
        two = io.BytesIO(b'\x42\x85')
        three = io.BytesIO(b'\x3C\xB9\x23')
        four = io.BytesIO(b'\x1A\x45\xDF\xA3')

        self.assertEqual(ElementHeader._read_id(one), (0xBF, 1))
        self.assertEqual(ElementHeader._read_id(two), (0x4285, 2))
        self.assertEqual(ElementHeader._read_id(three), (0x3CB923, 3))
        self.assertEqual(ElementHeader._read_id(four), (0x1A45DFA3, 4))

    def test_write_id(self):
        test_values = [
            ((0xBF, 1), b'\xBF'),
            ((0x4285, 1), b'\x42\x85'),
            ((0x3CB923, 1), b'\x3C\xB9\x23'),
            ((0x1A45DFA3, 1), b'\x1A\x45\xDF\xA3'),
        ]

        for _in, _out in test_values:
            header = ElementHeader(*_in)
            buf = io.BytesIO()
            header._write_id(buf)
            self.assertEqual(buf.getvalue(), _out)

    def test_id_roundtrip(self):
        buf = io.BytesIO(b'\x1A\x45\xDF\xA3')
        _id = ElementHeader._read_id(buf)[0]

        buf = io.BytesIO()
        header = ElementHeader(_id, 1)
        header._write_id(buf)

        self.assertEqual(buf.getvalue(), b'\x1A\x45\xDF\xA3')

    def test_size_read(self):
        test_values = [
            (b'\x81', (0x1, 1)),
            (b'\x41\xA3', (0x1A3, 2)),
            (b'\x25\xB3\xC2', (0x5B3C2, 3)),
            (b'\x16\xAE\x7D\x3F', (0x6AE7D3F, 4)),
            (b'\x08\xF4\x5E\xCD\x0A', (0xF45ECD0A, 5)),
            (b'\x04\xAB\x84\xCB\x69\xFD', (0xAB84CB69FD, 6)),
            (b'\x02\xDF\x38\xBA\xE4\x75\xAD', (0xDF38BAE475AD, 7)),
            (b'\x01\xE4\x51\xF3\x3E\xB8\xA5\x6D', (0xE451F33EB8A56D, 8)),
        ]

        for _in, _out in test_values:
            buf = io.BytesIO(_in)
            self.assertEqual(ElementHeader._read_size(buf), _out)

    def test_size_write(self):
        test_values = [
            ((0x82, 0x1), b'\x81'),
            ((0x82, 0x1A3), b'\x41\xA3'),
            ((0x82, 0x5B3C2), b'\x25\xB3\xC2'),
            ((0x82, 0x6AE7D3F), b'\x16\xAE\x7D\x3F'),
            ((0x82, 0xF45ECD0A), b'\x08\xF4\x5E\xCD\x0A'),
            ((0x82, 0xAB84CB69FD), b'\x04\xAB\x84\xCB\x69\xFD'),
            ((0x82, 0xDF38BAE475AD), b'\x02\xDF\x38\xBA\xE4\x75\xAD'),
            ((0x82, 0xE451F33EB8A56D), b'\x01\xE4\x51\xF3\x3E\xB8\xA5\x6D')
        ]

        for _in, _out in test_values:
            header = ElementHeader(*_in)
            buf = io.BytesIO()
            header._write_size(buf)
            self.assertEqual(buf.getvalue(), _out)

    def test_size_roundtrip(self):
            buf = io.BytesIO(b'\x16\xAE\x7D\x3F')
            size = ElementHeader._read_size(buf)[0]

            buf = io.BytesIO()
            header = ElementHeader(0x1A45DFA3, size)
            header._write_size(buf)

            self.assertEqual(buf.getvalue(), b'\x16\xAE\x7D\x3F')

add(TElementHeader)


class TEBMLElement(TestCase):

    def test_unsigned_element(self):
        header = ElementHeader(0x1A45DFA3, 1)
        ele = UnsignedElement(header, 100)

        self.assertEqual(ele.num_read_bytes, 0)
        self.assertEqual(ele.num_write_bytes, 1)

        buf = io.BytesIO()
        ele.write(buf)

        buf.seek(0)

        header = ElementHeader.read(buf)
        ele = UnsignedElement.read(header, buf)

        self.assertEqual(ele, 100)
        self.assertEqual(buf.getvalue(), b'\x1a\x45\xdf\xa3\x81\x64')

    def test_ascii(self):
        header = ElementHeader(0x1A45DFA3, 4)
        ele = ASCIIElement(header, u'abcd')

        self.assertEqual(ele.num_read_bytes, 0)
        self.assertEqual(ele.num_write_bytes, 4)

        buf = io.BytesIO()
        ele.write(buf)

        buf.seek(0)

        header = ElementHeader.read(buf)
        ele = ASCIIElement.read(header, buf)

        self.assertEqual(ele, u'abcd')
        self.assertEqual(buf.getvalue(), b'\x1a\x45\xdf\xa3\x84abcd')

    def test_utf8(self):
        header = ElementHeader(0x1A45DFA3, 8)
        ele = UTF8Element(header, u'Test\u2019s')

        self.assertEqual(ele.num_read_bytes, 0)
        self.assertEqual(ele.num_write_bytes, 8)

        buf = io.BytesIO()
        ele.write(buf)

        buf.seek(0)

        header = ElementHeader.read(buf)
        ele = UTF8Element.read(header, buf)

        self.assertEqual(ele, u'Test\u2019s')
        self.assertEqual(buf.getvalue(),
                         b'\x1a\x45\xdf\xa3\x88Test\xe2\x80\x99s')

    def test_binary(self):
        header = ElementHeader(0x1A45DFA3, 4)
        ele = BinaryElement(header, b'\x00\x11\x22\x33')

        self.assertEqual(ele.num_read_bytes, 0)
        self.assertEqual(ele.num_write_bytes, 4)

        buf = io.BytesIO()
        ele.write(buf)

        buf.seek(0)

        header = ElementHeader.read(buf)
        ele = BinaryElement.read(header, buf)

        self.assertEqual(ele, b'\x00\x11\x22\x33')
        self.assertEqual(buf.getvalue(),
                         b'\x1a\x45\xdf\xa3\x84\x00\x11\x22\x33')

    def test_master(self):
        header = ElementHeader(0x1A45DFA3, 0)
        ele = MasterElement(header)
        ele.children = [
            BinaryElement(ElementHeader(0x1A45DFA3, 4), b'\x00\x11\x22\x33'),
            UTF8Element(ElementHeader(0x1A45DFA3, 8), u'Test\u2019s'),
            ASCIIElement(ElementHeader(0x1A45DFA3, 4), u'abcd'),
            UnsignedElement(ElementHeader(0x1A45DFA3, 1), 100),
        ]

        self.assertEqual(ele.num_read_bytes, 0)
        self.assertEqual(ele.num_write_bytes, 37)
        self.assertEqual(ele.byte_difference(), 0)

        buf = io.BytesIO()
        ele.write(buf)

        self.assertEqual(buf.tell(), 42)
        self.assertEqual(len(buf.getvalue()), 42)

        buf.seek(0)

        self.assertEqual(
            buf.getvalue(),
            b'\x1a\x45\xdf\xa3\xa5\x1a\x45\xdf\xa3\x84\x00\x11\x22\x33\x1a\x45'
            b'\xdf\xa3\x88Test\xe2\x80\x99s\x1a\x45\xdf\xa3\x84abcd\x1a\x45'
            b'\xdf\xa3\x81\x64'
        )

    def test_ebml_header(self):
        data = (b'\x1A\x45\xDF\xA3\x01\x00\x00\x00\x00\x00\x00\x23\x42\x86\x81'
                b'\x01\x42\xF7\x81\x01\x42\xF2\x81\x04\x42\xF3\x81\x08\x42\x82'
                b'\x88\x6D\x61\x74\x72\x6F\x73\x6B\x61\x42\x87\x81\x02\x42\x85'
                b'\x81\x02')
        buf = io.BytesIO(data)

        header = ElementHeader.read(buf)
        ele = EBMLHeader.read(header, buf)

        self.assertEquals(ele._header.num_write_bytes, 12)
        self.assertEquals(ele._header.num_read_bytes, 12)
        self.assertEquals(ele._header.byte_difference(), 0)
        self.assertEquals(ele.num_read_bytes, 35)
        self.assertEquals(ele.num_write_bytes, 35)

        buf = io.BytesIO()
        ele.write(buf)

        self.assertEquals(ele._header.num_write_bytes, 12)
        self.assertEquals(buf.getvalue(), data)

    def test_document(self):
        data = (b'\x1A\x45\xDF\xA3\x01\x00\x00\x00\x00\x00\x00\x23\x42\x86\x81'
                b'\x01\x42\xF7\x81\x01\x42\xF2\x81\x04\x42\xF3\x81\x08\x42\x82'
                b'\x88\x6D\x61\x74\x72\x6F\x73\x6B\x61\x42\x87\x81\x02\x42\x85'
                b'\x81\x02')
        buf = io.BytesIO(data)
        doc = Document(buf)

        self.assertTrue(doc.find_children(0x1A45DFA3))

        buf = io.BytesIO()
        doc.write(buf)

        self.assertEquals(buf.getvalue(), data)


add(TEBMLElement)
