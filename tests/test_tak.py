# -*- coding: utf-8 -*-

import os

from mutagen.tak import TAK, TAKHeaderError
from tests import TestCase, DATA_DIR


class TTAK(TestCase):

    def setUp(self):
        self.tak_no_tags = TAK(os.path.join(DATA_DIR, "test.tak"))
        self.tak_tags = TAK(os.path.join(DATA_DIR, "test-tags.tak"))

    def test_not_my_file(self):
        self.failUnlessRaises(
            TAKHeaderError, TAK,
            os.path.join(DATA_DIR, "empty.ogg"))
        self.failUnlessRaises(
            TAKHeaderError, TAK,
            os.path.join(DATA_DIR, "click.mpc"))

    def test_mime(self):
        self.failUnless("audio/x-tak" in self.tak_no_tags.mime)

    def test_pprint(self):
        self.failUnless(self.tak_no_tags.pprint())
        self.failUnless(self.tak_tags.pprint())
