from StringIO import StringIO
from tests import TestCase, add
from mutagen._ogg import OggPage

class TOggPage(TestCase):
    def setUp(self):
        self.fileobj = file("tests/data/empty.ogg", "rb")
        self.page = OggPage(self.fileobj)

        pages = [OggPage(), OggPage(), OggPage()]
        pages[0].data = ["foo"]
        pages[1].data = ["bar"]
        pages[2].data = ["baz"]
        for i in range(len(pages)):
            pages[i].sequence = i
        for page in pages:
            page.serial = 1
        self.pages = pages

    def test_flags(self):
        self.failUnless(self.page.first)
        self.failIf(self.page.continued)
        self.failIf(self.page.last)
        self.failUnless(self.page.finished)

        for first in [True, False]:
            self.page.first = first
            for last in [True, False]:
                self.page.last = last
                for continued in [True, False]:
                    self.page.continued = continued
                    self.failUnlessEqual(self.page.first, first)
                    self.failUnlessEqual(self.page.last, last)
                    self.failUnlessEqual(self.page.continued, continued)

    def test_flags_next_page(self):
        page = OggPage(self.fileobj)
        self.failIf(page.first)
        self.failIf(page.continued)
        self.failIf(page.last)

    def test_length(self):
        # Always true for Ogg Vorbis files
        self.failUnlessEqual(self.page.size, 58)

    def test_first_metadata_page_is_separate(self):
        self.failIf(OggPage(self.fileobj).continued)

    def test_roundtrip(self):
        self.failUnlessEqual(
            self.page, OggPage(StringIO(self.page.write())))

    def test_at_least_one_audio_page(self):
        page = OggPage(self.fileobj)
        while not page.last:
            page = OggPage(self.fileobj)
        self.failUnless(page.last)

    def test_renumber(self):
        self.failUnlessEqual(
            [page.sequence for page in self.pages], [0, 1, 2])
        fileobj = StringIO()
        for page in self.pages:
            fileobj.write(page.write())
        fileobj.seek(0)
        OggPage.renumber(fileobj, 1, 10)
        fileobj.seek(0)
        pages = [OggPage(fileobj) for i in range(3)]
        self.failUnlessEqual([page.sequence for page in pages], [10, 11, 12])

    def test_renumber_extradata(self):
        fileobj = StringIO()
        for page in self.pages:
            fileobj.write(page.write())
        fileobj.write("left over data")
        fileobj.seek(0)
        orig_data = fileobj.read()
        fileobj.seek(0)
        # Trying to rewrite should raise an error...
        self.failUnlessRaises(Exception, OggPage.renumber, fileobj, 1, 10)
        fileobj.seek(0)
        # But the already written data should remain valid,
        pages = [OggPage(fileobj) for i in range(3)]
        self.failUnlessEqual([page.sequence for page in pages], [10, 11, 12])
        # And the garbage that caused the error should be okay too.
        self.failUnlessEqual(fileobj.read(), "left over data")

    def test_from_pages(self):
        self.failUnlessEqual(
            ["foo", "bar", "baz"], OggPage.from_pages(self.pages))
        self.pages[0].finished = False
        self.failUnlessEqual(
            ["foobar", "baz"], OggPage.from_pages(self.pages))

    def test_from_pages_mixed_stream(self):
        self.pages[0].serial = 3
        self.failUnlessRaises(ValueError, OggPage.from_pages, self.pages)

    def test_from_pages_missing_sequence(self):
        self.pages[0].sequence = 3
        self.failUnlessRaises(ValueError, OggPage.from_pages, self.pages)

    def test_from_pages_strict(self):
        for page in self.pages:
            page.finished = False
        self.failUnlessRaises(
            ValueError, OggPage.from_pages, self.pages, strict=True)

    def test_from_packets_short_enough(self):
        packets = ["1" * 200, "2" * 200, "3" * 200]
        pages = OggPage.from_packets(packets)
        self.failUnlessEqual(len(pages), 3)
        for page in pages:
            # Each page should have one packet
            self.failUnlessEqual(len(page.data), 1)
            self.failUnlessEqual(len(page.data[0]), 200)
            self.failUnless(page.finished)
        self.failUnlessEqual(OggPage.from_pages(pages), packets)

    def test_from_packets_long(self):
        packets = ["1" * 100000, "2" * 100000, "3" * 100000]
        pages = OggPage.from_packets(packets)
        self.failUnless(len(pages) > 3)
        self.failIf(pages[0].finished)
        self.failUnless(pages[1].continued)
        self.failUnlessEqual(OggPage.from_pages(pages), packets,
                             "inaccurate page/packet roundtrip")

    def tearDown(self):
        self.fileobj.close()
add(TOggPage)
