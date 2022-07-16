
import re
import os
import sys
import shutil
import contextlib
from io import StringIO
from tempfile import mkstemp
from unittest import TestCase as BaseTestCase

try:
    import pytest
except ImportError:
    raise SystemExit("pytest missing: sudo apt-get install python-pytest")


DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data")
assert isinstance(DATA_DIR, str)


_fs_enc = sys.getfilesystemencoding()
if "öäü".encode(_fs_enc, "replace").decode(_fs_enc) != u"öäü":
    raise RuntimeError("This test suite needs a unicode locale encoding. "
                       "Try setting LANG=C.UTF-8")


def get_temp_copy(path):
    """Returns a copy of the file with the same extension"""

    ext = os.path.splitext(path)[-1]
    fd, filename = mkstemp(suffix=ext)
    os.close(fd)
    shutil.copy(path, filename)
    return filename


def get_temp_empty(ext=""):
    """Returns an empty file with the extension"""

    fd, filename = mkstemp(suffix=ext)
    os.close(fd)
    return filename


@contextlib.contextmanager
def capture_output():
    """
    with capture_output() as (stdout, stderr):
        some_action()
    print stdout.getvalue(), stderr.getvalue()
    """

    err = StringIO()
    out = StringIO()
    old_err = sys.stderr
    old_out = sys.stdout
    sys.stderr = err
    sys.stdout = out

    try:
        yield (out, err)
    finally:
        sys.stderr = old_err
        sys.stdout = old_out


class TestCase(BaseTestCase):

    def failUnlessRaisesRegexp(self, exc, re_, fun, *args, **kwargs):
        def wrapped(*args, **kwargs):
            try:
                fun(*args, **kwargs)
            except Exception as e:
                self.failUnless(re.search(re_, str(e)))
                raise
        self.failUnlessRaises(exc, wrapped, *args, **kwargs)

    # silence deprec warnings about useless renames
    failUnless = BaseTestCase.assertTrue
    failIf = BaseTestCase.assertFalse
    failUnlessEqual = BaseTestCase.assertEqual
    failUnlessRaises = BaseTestCase.assertRaises
    failUnlessAlmostEqual = BaseTestCase.assertAlmostEqual
    failIfEqual = BaseTestCase.assertNotEqual
    failIfAlmostEqual = BaseTestCase.assertNotAlmostEqual
    assertEquals = BaseTestCase.assertEqual
    assertNotEquals = BaseTestCase.assertNotEqual
    assert_ = BaseTestCase.assertTrue

    def assertReallyEqual(self, a, b):
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertTrue(a == b)
        self.assertTrue(b == a)
        self.assertFalse(a != b)
        self.assertFalse(b != a)

    def assertReallyNotEqual(self, a, b):
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertFalse(a == b)
        self.assertFalse(b == a)
        self.assertTrue(a != b)
        self.assertTrue(b != a)


def unit(run=[], exitfirst=False):
    args = []

    if run:
        args.append("-k")
        args.append(" or ".join(run))

    if exitfirst:
        args.append("-x")

    args.append("tests")

    return pytest.main(args=args)
