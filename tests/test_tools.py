# -*- coding: utf-8 -*-

import os
import sys
import imp

import mutagen
from mutagen._compat import StringIO, text_type, PY2
from mutagen._toolsutil import fsnative, is_fsnative

from tests import TestCase


def get_var(tool_name, entry="main"):
    tool_path = os.path.join(
        mutagen.__path__[0], "..", "tools", fsnative(tool_name))
    dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        mod = imp.load_source(tool_name, tool_path)
    finally:
        sys.dont_write_bytecode = dont_write_bytecode
    return getattr(mod, entry)


class _TTools(TestCase):
    TOOL_NAME = None

    def setUp(self):
        self.assertTrue(isinstance(self.TOOL_NAME, text_type))
        self._main = get_var(self.TOOL_NAME)

    def get_var(self, name):
        return get_var(self.TOOL_NAME, name)

    def call2(self, *args):
        for arg in args:
            self.assertTrue(is_fsnative(arg))
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            out = StringIO()
            err = StringIO()
            sys.stdout = out
            sys.stderr = err
            try:
                ret = self._main([fsnative(self.TOOL_NAME)] + list(args))
            except SystemExit as e:
                ret = e.code
            ret = ret or 0
            out_val = out.getvalue()
            err_val = err.getvalue()
            if os.name == "nt" and PY2:
                encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
                out_val = text_type(out_val, encoding)
                err_val = text_type(err_val, encoding)
            return (ret, out_val, err_val)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def call(self, *args):
        return self.call2(*args)[:2]

    def tearDown(self):
        del self._main
