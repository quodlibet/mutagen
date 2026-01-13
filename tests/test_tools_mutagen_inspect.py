
import glob
import os

from tests.test_tools import _TTools


class TMutagenInspect(_TTools):

    TOOL_NAME = "mutagen-inspect"

    def test_basic(self):
        base = os.path.join('tests', 'data')
        self.paths = glob.glob(os.path.join(base, "empty*"))
        self.paths += glob.glob(os.path.join(base, "silence-*"))

        for path in self.paths:
            res, out = self.call(path)
            self.assertFalse(res)
            self.assertTrue(out.strip())
            self.assertFalse("Unknown file type" in out)
            self.assertFalse("Errno" in out)
