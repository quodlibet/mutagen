# -*- coding: utf-8 -*-

import os

from mutagen._toolsutil import get_win32_unicode_argv, split_escape
from mutagen._compat import text_type

from tests import TestCase


class Tget_win32_unicode_argv(TestCase):

    def test_main(self):
        argv = get_win32_unicode_argv()
        if os.name == "nt" and argv:
            self.assertTrue(isinstance(argv[0], text_type))


class Tsplit_escape(TestCase):
    def test_split_escape(self):
        inout = [
            (("", ":"), [""]),
            ((":", ":"), ["", ""]),
            ((":", ":", 0), [":"]),
            ((":b:c:", ":", 0), [":b:c:"]),
            ((":b:c:", ":", 1), ["", "b:c:"]),
            ((":b:c:", ":", 2), ["", "b", "c:"]),
            ((":b:c:", ":", 3), ["", "b", "c", ""]),
            (("a\\:b:c", ":"), ["a:b", "c"]),
            (("a\\\\:b:c", ":"), ["a\\", "b", "c"]),
            (("a\\\\\\:b:c\\:", ":"), ["a\\:b", "c:"]),
            (("\\", ":"), [""]),
            (("\\\\", ":"), ["\\"]),
            (("\\\\a\\b", ":"), ["\\a\\b"]),
        ]

        for inargs, out in inout:
            self.assertEqual(split_escape(*inargs), out)

    def test_types(self):
        parts = split_escape(b"\xff:\xff", b":")
        self.assertEqual(parts, [b"\xff", b"\xff"])
        self.assertTrue(isinstance(parts[0], bytes))

        parts = split_escape(b"", b":")
        self.assertEqual(parts, [b""])
        self.assertTrue(isinstance(parts[0], bytes))

        parts = split_escape(u"a:b", u":")
        self.assertEqual(parts, [u"a", u"b"])
        self.assertTrue(all(isinstance(p, text_type) for p in parts))

        parts = split_escape(u"", u":")
        self.assertEqual(parts, [u""])
        self.assertTrue(all(isinstance(p, text_type) for p in parts))

        parts = split_escape(u":", u":")
        self.assertEqual(parts, [u"", u""])
        self.assertTrue(all(isinstance(p, text_type) for p in parts))
