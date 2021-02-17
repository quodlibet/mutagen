
import os

from tests.test_tools import _TTools


class TMutagenPony(_TTools):

    TOOL_NAME = u"mutagen-pony"

    def test_basic(self):
        base = os.path.join('tests', 'data')
        res, out = self.call(base)
        self.failIf(res)
        self.failUnless("Report for %s" % base in out)
