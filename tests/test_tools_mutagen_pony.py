import os

from tests import add
from tests.test_tools import _TTools


class TMutagenPony(_TTools):

    TOOL_NAME = "mutagen-pony"

    def test_basic(self):
        base = os.path.join('tests', 'data')
        res, out = self.call(base)
        self.failIf(res)
        self.failUnless("Report for tests/data" in out)

add(TMutagenPony)
