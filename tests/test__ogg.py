from StringIO import StringIO
from tests import TestCase, add
from mutagen._ogg import OggPage

class TOggPage(TestCase):
    def setUp(self):
        self.fileobj = file("tests/data/empty.ogg")
        self.page = OggPage(self.fileobj)

    def test_flags(self):
        self.failUnless(self.page.first)
        self.failIf(self.page.continued)
        self.failIf(self.page.last)

    def test_flags_next_page(self):
        page = OggPage(self.fileobj)
        self.failIf(page.first)
        self.failIf(page.continued)
        self.failIf(page.last)

    def test_length(self):
        # Always true for Ogg files
        self.failUnlessEqual(self.page.size, 58)

    def test_first_metadata_page_is_separate(self):
        self.failIf(OggPage(self.fileobj).continued)

    def test_roundtrip(self):
        self.failUnlessEqual(self.page, OggPage(StringIO(self.page.write())))

    def test_at_least_one_audio_page(self):
        page = OggPage(self.fileobj)
        while not page.last:
            page = OggPage(self.fileobj)
        self.failUnless(page.last)
add(TOggPage)
