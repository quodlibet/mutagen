
import os

from tests.test_tools import _TTools


class TMutagenPony(_TTools):

    TOOL_NAME = "mutagen-pony"

    def test_basic(self):
        base = os.path.join('tests', 'data')
        res, out = self.call(base)
        self.assertFalse(res)
        self.assertTrue(f"Report for {base}" in out)
