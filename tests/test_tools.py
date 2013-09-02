import os
import sys
import StringIO

from tests import TestCase


def get_main(tool_name, entry="main"):
    tool_path = os.path.join("tools", tool_name)
    env = {}
    execfile(tool_path, env)
    return env[entry]


class _TTools(TestCase):
    TOOL_NAME = None

    def setUp(self):
        self._main = get_main(self.TOOL_NAME)

    def call(self, *args):
        for arg in args:
            assert isinstance(arg, str)
        old_stdout = sys.stdout
        try:
            out = StringIO.StringIO()
            sys.stdout = out
            try:
                ret = self._main([self.TOOL_NAME] + list(args))
            except SystemExit, e:
                ret = e.code
            ret = ret or 0
            return (ret,  out.getvalue())
        finally:
            sys.stdout = old_stdout

    def tearDown(self):
        del self._main
