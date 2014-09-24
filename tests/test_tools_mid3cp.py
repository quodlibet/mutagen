# -*- coding: utf-8 -*-

# Copyright 2014 Ben Ockmore

# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""Tests for mid3cp tool. Since the tool is quite simple, most of the
functionality is covered by the mutagen package tests - these simply test
usage.
"""

import os
from tempfile import mkstemp
import shutil
from mutagen.id3 import ID3, ParseID3v1

from tests import add
from tests.test_tools import _TTools


class TMid3cp(_TTools):

    TOOL_NAME = "mid3cp"

    def setUp(self):
        super(TMid3cp, self).setUp()
        original = os.path.join('tests', 'data', 'silence-44-s.mp3')
        fd, self.filename = mkstemp(suffix='.mp3')
        os.close(fd)
        shutil.copy(original, self.filename)

    def tearDown(self):
        super(TMid3cp, self).tearDown()
        os.unlink(self.filename)

    def test_noop(self):
        res, out, err = self.call2()
        self.assertNotEqual(res, 0)
        self.failUnless("Usage:" in err)

    def test_src_equal_dst(self):
        res, out, err = self.call2(self.filename, self.filename)
        self.assertNotEqual(res, 0)
        self.failUnless("the same" in err)
        self.failUnless("Usage:" in err)

    def test_copy(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        res = self.call(self.filename, blank_file)[0]
        self.failIf(res)

        original_id3 = ID3(self.filename)
        copied_id3 = ID3(blank_file)

        self.failUnlessEqual(original_id3, copied_id3)

        for key in original_id3:
            # Go through every tag in the original file, and check that it's
            # present and correct in the copy
            self.failUnless(key in copied_id3)
            self.failUnlessEqual(copied_id3[key], original_id3[key])

        os.unlink(blank_file)

    def test_include_id3v1(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        self.call('-1', self.filename, blank_file)

        fileobj = open(blank_file, 'rb')
        fileobj.seek(-128, 2)
        frames = ParseID3v1(fileobj.read(128))

        # If ID3v1 frames are present, assume they've been written correctly by
        # mutagen, so no need to check them
        self.failUnless(frames)

    def test_exclude_single_tag(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        self.call('-x TLEN', self.filename, blank_file)

        original_id3 = ID3(self.filename)
        copied_id3 = ID3(blank_file)

        self.failUnless('TLEN' in original_id3)
        self.failIf('TLEN' in copied_id3)

    def test_exclude_multiple_tag(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        self.call('-x TLEN', '-x TCON', '-x TALB', self.filename, blank_file)

        original_id3 = ID3(self.filename)
        copied_id3 = ID3(blank_file)

        self.failUnless('TLEN' in original_id3)
        self.failUnless('TCON' in original_id3)
        self.failUnless('TALB' in original_id3)
        self.failIf('TLEN' in copied_id3)
        self.failIf('TCON' in copied_id3)
        self.failIf('TALB' in copied_id3)

    def test_no_src_header(self):
        fd, blank_file1 = mkstemp(suffix='.mp3')
        os.close(fd)

        fd, blank_file2 = mkstemp(suffix='.mp3')
        os.close(fd)

        err = self.call2(blank_file1, blank_file2)[2]
        self.failUnless("No ID3 header found" in err)

    def test_verbose(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        err = self.call2(self.filename, "--verbose", blank_file)[2]
        self.failUnless('mp3 contains:' in err)
        self.failUnless('Successfully saved' in err)

    def test_quiet(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        out = self.call(self.filename, blank_file)[1]
        self.failIf(out)

    def test_exit_status(self):
        fd, blank_file = mkstemp(suffix='.mp3')
        os.close(fd)

        status, out, err = self.call2(self.filename)
        self.assertTrue(status)

        status, out, err = self.call2(self.filename, self.filename)
        self.assertTrue(status)

        status, out, err = self.call2(blank_file, self.filename)
        self.assertTrue(status)

        status, out, err = self.call2("", self.filename)
        self.assertTrue(status)

        status, out, err = self.call2(self.filename, blank_file)
        self.assertFalse(status)

add(TMid3cp)
