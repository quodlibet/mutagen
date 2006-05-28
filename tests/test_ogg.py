import os
import random
import shutil

from StringIO import StringIO
from tests import TestCase, add
from mutagen.ogg import OggPage
from tempfile import mkstemp

class TOggPage(TestCase):
    def setUp(self):
        self.fileobj = file(os.path.join("tests", "data", "empty.ogg"), "rb")
        self.page = OggPage(self.fileobj)

        pages = [OggPage(), OggPage(), OggPage()]
        pages[0].packets = ["foo"]
        pages[1].packets = ["bar"]
        pages[2].packets = ["baz"]
        for i in range(len(pages)):
            pages[i].sequence = i
        for page in pages:
            page.serial = 1
        self.pages = pages

    def test_flags(self):
        self.failUnless(self.page.first)
        self.failIf(self.page.continued)
        self.failIf(self.page.last)
        self.failUnless(self.page.complete)

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
        self.failUnlessEqual(len(self.page.write()), 58)

    def test_first_metadata_page_is_separate(self):
        self.failIf(OggPage(self.fileobj).continued)

    def test_single_page_roundtrip(self):
        self.failUnlessEqual(
            self.page, OggPage(StringIO(self.page.write())))

    def test_at_least_one_audio_page(self):
        page = OggPage(self.fileobj)
        while not page.last:
            page = OggPage(self.fileobj)
        self.failUnless(page.last)

    def test_crappy_fragmentation(self):
        packets = ["1" * 511, "2" * 511, "3" * 511]
        pages = OggPage.from_packets(packets, default_size=510, wiggle_room=0)
        self.failUnless(len(pages) > 3)
        self.failUnlessEqual(OggPage.to_packets(pages), packets)

    def test_wiggle_room(self):
        packets = ["1" * 511, "2" * 511, "3" * 511]
        pages = OggPage.from_packets(packets, default_size=510, wiggle_room=100)
        self.failUnlessEqual(len(pages), 3)
        self.failUnlessEqual(OggPage.to_packets(pages), packets)

    def test_one_packet_per_wiggle(self):
        packets = ["1" * 511, "2" * 511, "3" * 511]
        pages = OggPage.from_packets(
            packets, default_size=1000, wiggle_room=1000000)
        self.failUnlessEqual(len(pages), 2)
        self.failUnlessEqual(OggPage.to_packets(pages), packets)

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

        fileobj.seek(0)
        OggPage.renumber(fileobj, 1, 20)
        fileobj.seek(0)
        pages = [OggPage(fileobj) for i in range(3)]
        self.failUnlessEqual([page.sequence for page in pages], [20, 21, 22])

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

    def test_renumber_reread(self):
        try:
            fd, filename = mkstemp(suffix=".ogg")
            os.close(fd)
            shutil.copy(os.path.join("tests", "data", "multipagecomment.ogg"),
                        filename)
            fileobj = file(filename, "rb+")
            OggPage.renumber(fileobj, 1002429366L, 20)
            fileobj.close()
            fileobj = file(filename, "rb+")
            OggPage.renumber(fileobj, 1002429366L, 0)
            fileobj.close()
        finally:
            try: os.unlink(filename)
            except OSError: pass

    def test_to_packets(self):
        self.failUnlessEqual(
            ["foo", "bar", "baz"], OggPage.to_packets(self.pages))
        self.pages[0].complete = False
        self.pages[1].continued = True
        self.failUnlessEqual(
            ["foobar", "baz"], OggPage.to_packets(self.pages))

    def test_to_packets_mixed_stream(self):
        self.pages[0].serial = 3
        self.failUnlessRaises(ValueError, OggPage.to_packets, self.pages)

    def test_to_packets_missing_sequence(self):
        self.pages[0].sequence = 3
        self.failUnlessRaises(ValueError, OggPage.to_packets, self.pages)

    def test_to_packets_strict(self):
        for page in self.pages:
            page.complete = False
        self.failUnlessRaises(
            ValueError, OggPage.to_packets, self.pages, strict=True)

    def test_from_packets_short_enough(self):
        packets = ["1" * 200, "2" * 200, "3" * 200]
        pages = OggPage.from_packets(packets)
        self.failUnlessEqual(OggPage.to_packets(pages), packets)

    def test_from_packets_long(self):
        packets = ["1" * 100000, "2" * 100000, "3" * 100000]
        pages = OggPage.from_packets(packets)
        self.failIf(pages[0].complete)
        self.failUnless(pages[1].continued)
        self.failUnlessEqual(OggPage.to_packets(pages), packets)

    def test_random_data_roundtrip(self):
        try: random_file = file("/dev/urandom", "rb")
        except (IOError, OSError):
            print "WARNING: Random data round trip test disabled."
            return
        for i in range(10):
            num_packets = random.randrange(2, 100)
            lengths = [random.randrange(10, 10000)
                       for i in range(num_packets)]
            packets = map(random_file.read, lengths)
            self.failUnlessEqual(
                packets, OggPage.to_packets(OggPage.from_packets(packets)))

    def test_packet_exactly_255(self):
        page = OggPage()
        page.packets = ["1" * 255]
        page.complete = False
        page2 = OggPage()
        page2.packets = [""]
        page2.sequence = 1
        page2.continued = True
        self.failUnlessEqual(
            ["1" * 255], OggPage.to_packets([page, page2]))

    def test_page_max_size_alone_too_big(self):
        page = OggPage()
        page.packets = ["1" * 255 * 255]
        page.complete = True
        self.failUnlessRaises(ValueError, page.write)

    def test_page_max_size(self):
        page = OggPage()
        page.packets = ["1" * 255 * 255]
        page.complete = False
        page2 = OggPage()
        page2.packets = [""]
        page2.sequence = 1
        page2.continued = True
        self.failUnlessEqual(
            ["1" * 255 * 255], OggPage.to_packets([page, page2]))

    def test_complete_zero_length(self):
        packets = [""] * 20
        page = OggPage.from_packets(packets)[0]
        new_page = OggPage(StringIO(page.write()))
        self.failUnlessEqual(new_page, page)
        self.failUnlessEqual(OggPage.to_packets([new_page]), packets)

    def test_too_many_packets(self):
        packets = ["1"] * 3000
        pages = OggPage.from_packets(packets)
        map(OggPage.write, pages)

    def test_read_max_size(self):
        page = OggPage()
        page.packets = ["1" * 255 * 255]
        page.complete = False
        page2 = OggPage()
        page2.packets = ["", "foo"]
        page2.sequence = 1
        page2.continued = True
        data = page.write() + page2.write()
        fileobj = StringIO(data)
        self.failUnlessEqual(OggPage(fileobj), page)
        self.failUnlessEqual(OggPage(fileobj), page2)
        self.failUnlessRaises(EOFError, OggPage, fileobj)

    def tearDown(self):
        self.fileobj.close()
add(TOggPage)
