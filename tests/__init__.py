from __future__ import division, print_function

import re
import glob
import os
import sys
import unittest

from unittest import TestCase as BaseTestCase
suites = []
add = suites.append

from mutagen._compat import cmp


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
        self.assertEqual(0, cmp(a, b))
        self.assertEqual(0, cmp(b, a))

    def assertReallyNotEqual(self, a, b):
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertFalse(a == b)
        self.assertFalse(b == a)
        self.assertTrue(a != b)
        self.assertTrue(b != a)
        self.assertNotEqual(0, cmp(a, b))
        self.assertNotEqual(0, cmp(b, a))


def import_tests():
    for name in glob.glob(
            os.path.join(os.path.dirname(__file__), "test_*.py")):
        # skip m4a in py3k
        if sys.version_info[0] != 2 and "test_m4a" in name:
            continue
        module = "tests." + os.path.basename(name)
        __import__(module[:-3], {}, {}, [])


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

    runner = Runner()
    failures = 0
    for test in suites:
        failures += runner.run(test)

    return len(suites), failures


def unit(run=[], exitfirst=False):
    import_tests()

    runner = Runner()
    failures = 0
    count = 0
    tests = [t for t in suites if not run or t.__name__ in run]

    for test in tests:
        if failures and exitfirst:
            break

        failures += runner.run(test)

    count += len(tests)

    return count, failures
