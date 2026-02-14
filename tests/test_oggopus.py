
import os
from io import BytesIO

from mutagen.oggopus import OggOpus, OggOpusInfo, delete, error
from mutagen.ogg import OggPage
from tests import TestCase, DATA_DIR, get_temp_copy
from tests.test_ogg import TOggFileTypeMixin


class TOggOpus(TestCase, TOggFileTypeMixin):
    Kind = OggOpus

    def setUp(self):
        self.filename = get_temp_copy(os.path.join(DATA_DIR, "example.opus"))
        self.audio = self.Kind(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

    def test_length(self):
        self.failUnlessAlmostEqual(self.audio.info.length, 11.35, 2)

    def test_misc(self):
        self.failUnlessEqual(self.audio.info.channels, 1)
        self.failUnless(self.audio.tags.vendor.startswith("libopus"))

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(self.Kind(self.filename).tags)

    def test_mime(self):
        self.failUnless("audio/ogg" in self.audio.mime)
        self.failUnless("audio/ogg; codecs=opus" in self.audio.mime)

    def test_invalid_not_first(self):
        with open(self.filename, "rb") as h:
            page = OggPage(h)
        page.first = False
        self.failUnlessRaises(error, OggOpusInfo, BytesIO(page.write()))

    def test_unsupported_version(self):
        with open(self.filename, "rb") as h:
            page = OggPage(h)
        data = bytearray(page.packets[0])

        data[8] = 0x03
        page.packets[0] = bytes(data)
        OggOpusInfo(BytesIO(page.write()))

        data[8] = 0x10
        page.packets[0] = bytes(data)
        self.failUnlessRaises(error, OggOpusInfo, BytesIO(page.write()))

    def test_preserve_non_padding(self):
        self.audio["FOO"] = ["BAR"]
        self.audio.save()

        extra_data = b"\xde\xad\xbe\xef"

        with open(self.filename, "r+b") as fobj:
            OggPage(fobj)  # header
            page = OggPage(fobj)
            data = OggPage.to_packets([page])[0]
            data = data.rstrip(b"\x00") + b"\x01" + extra_data
            new_pages = OggPage.from_packets([data], page.sequence)
            OggPage.replace(fobj, [page], new_pages)

        OggOpus(self.filename).save()

        with open(self.filename, "rb") as fobj:
            OggPage(fobj)  # header
            page = OggPage(fobj)
            data = OggPage.to_packets([page])[0]
            self.assertTrue(data.endswith(b"\x01" + extra_data))

        self.assertEqual(OggOpus(self.filename).tags._padding, 0)

    def test_init_padding(self):
        self.assertEqual(self.audio.tags._padding, 196)

    def test_pprint(self):
        assert self.audio.info.pprint() == "Ogg Opus, 11.35 seconds, 45243 bps"

    def test_bitrate(self):
        assert self.audio.info.bitrate == 45243

    def test_bitrate_stable_after_tag_change(self):
        bitrate_before = self.audio.info.bitrate
        assert bitrate_before != 0

        self.audio["ARTIST"] = ["Test Artist"]
        self.audio["ALBUM"] = ["Test Album"]
        self.audio["TITLE"] = ["Test Title"]
        self.audio.save(padding=lambda x: 0)

        audio_after = self.Kind(self.filename)
        bitrate_after = audio_after.info.bitrate
        assert bitrate_before == bitrate_after

    def test_bitrate_stable_with_large_metadata(self):
        bitrate_initial = self.audio.info.bitrate
        assert bitrate_initial != 0

        large_comment = "x" * 50000
        self.audio["COMMENT"] = [large_comment]
        self.audio["DESCRIPTION"] = [large_comment]
        self.audio["CUSTOM"] = [large_comment]
        self.audio.save(padding=lambda x: 0)

        audio_large = self.Kind(self.filename)
        bitrate_after_large = audio_large.info.bitrate
        assert bitrate_initial == bitrate_after_large

        audio_large["COMMENT"] = ["small"]
        del audio_large["DESCRIPTION"]
        del audio_large["CUSTOM"]
        audio_large.save(padding=lambda x: 0)

        audio_small = self.Kind(self.filename)
        bitrate_after_small = audio_small.info.bitrate
        assert bitrate_initial == bitrate_after_small
