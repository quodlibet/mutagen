# -*- coding: utf-8 -*-

from __future__ import division, print_function

import re
import glob
import os
import sys
import unittest

from unittest import TestCase as BaseTestCase

from mutagen._compat import PY3
from mutagen._toolsutil import fsencoding, is_fsnative


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
if os.name == "nt" and not PY3:
    DATA_DIR = DATA_DIR.decode("ascii")
assert is_fsnative(DATA_DIR)


if os.name != "nt":
    try:
        u"öäü".encode(fsencoding())
    except ValueError:
        raise RuntimeError("This test suite needs a unicode locale encoding. "
                           "Try setting LANG=C.UTF-8")


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

    def assertReallyEqual(self, a, b):
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertTrue(a == b)
        self.assertTrue(b == a)
        self.assertFalse(a != b)
        self.assertFalse(b != a)
        if not PY3:
            self.assertEqual(0, cmp(a, b))
            self.assertEqual(0, cmp(b, a))

    def assertReallyNotEqual(self, a, b):
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertFalse(a == b)
        self.assertFalse(b == a)
        self.assertTrue(a != b)
        self.assertTrue(b != a)
        if not PY3:
            self.assertNotEqual(0, cmp(a, b))
            self.assertNotEqual(0, cmp(b, a))


def import_tests():
    tests = []

    for name in glob.glob(
            os.path.join(os.path.dirname(__file__), "test_*.py")):
        module_name = "tests." + os.path.basename(name)
        mod = __import__(module_name[:-3], {}, {}, [])
        mod = getattr(mod, os.path.basename(name)[:-3])

        tests.extend(get_tests_from_mod(mod))

    return list(set(tests))


def get_tests_from_mod(mod):
    tests = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, BaseTestCase) and \
                obj is not TestCase:
            tests.append(obj)
    return tests


class Result(unittest.TestResult):

    separator1 = '=' * 70
    separator2 = '-' * 70

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        sys.stdout.write('.')

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        sys.stdout.write('E')

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        sys.stdout.write('F')

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = "%3d" % succ
        count = 50 - self.testsRun
        sys.stdout.write((" " * count) + v + "\n")
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            sys.stdout.write(self.separator1 + "\n")
            sys.stdout.write("%s: %s\n" % (flavour, str(test)))
            sys.stdout.write(self.separator2 + "\n")
            sys.stdout.write("%s\n" % err)


class Runner(object):
    def run(self, test):
        suite = unittest.makeSuite(test)
        pref = '%s (%d): ' % (test.__name__, len(suite._tests))
        print (pref + " " * (25 - len(pref)), end="")
        result = Result()
        suite(result)
        result.printErrors()
        return bool(result.failures + result.errors)


def check():
    from tests.quality import test_pep8
    from tests.quality import test_pyflakes

    tests = get_tests_from_mod(test_pep8)
    tests += get_tests_from_mod(test_pyflakes)

    runner = Runner()
    failures = 0
    for test in sorted(tests, key=lambda c: c.__name__):
        failures += runner.run(test)

    return len(tests), failures


def unit(run=[], exitfirst=False):
    tests = import_tests()

    runner = Runner()
    failures = 0
    filtered = [t for t in tests if not run or t.__name__ in run]

    for test in sorted(filtered, key=lambda c: c.__name__):
        if failures and exitfirst:
            break

        failures += runner.run(test)

    return len(filtered), failures
