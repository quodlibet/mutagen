"""RF64 reading and tag editing through the public WAVE API."""

import io
import os
import struct
import tempfile
from unittest import skipUnless

import mutagen
from mutagen._iff import error
from mutagen.id3 import TIT2
from mutagen.wave import WAVE
from tests import TestCase


def chunk(name, data, extended=False):
    size = 0xffffffff if extended else len(data)
    return (struct.pack('<4sI', name, size) + data
            + b'\x00' * (len(data) % 2))


def rf64(extra=b'', entries=(), normal_sizes=False):
    audio = bytes(range(256)) * 8
    fmt = chunk(b'fmt ', struct.pack('<HHIIHH', 1, 1, 8000, 16000, 2, 16))
    body = fmt + extra + chunk(b'data', audio, not normal_sizes)
    table = b''.join(struct.pack('<4sQ', name, size) for name, size in entries)
    size = 4 + 36 + len(table) + len(body)
    ds64 = chunk(b'ds64', struct.pack('<QQQI', size, len(audio),
                                    len(audio) // 2, len(entries)) + table)
    header_size = size if normal_sizes else 0xffffffff
    return io.BytesIO(struct.pack('<4sI4s', b'RF64', header_size, b'WAVE')
                      + ds64 + body)


class TRF64(TestCase):
    def test_identification(self):
        source = rf64()
        wave = mutagen.File(source)
        self.assertIsInstance(wave, WAVE)
        self.assertEqual(wave.info.channels, 1)
        self.assertEqual(wave.info.bits_per_sample, 16)
        self.assertEqual(wave.info.sample_rate, 8000)
        self.assertEqual(wave.info.length, 1024 / 8000)
        self.assertIsNone(wave.tags)
        self.assertEqual(WAVE.score('', source, source.getvalue()[:12]), 2)

    def test_tag_lifecycle(self):
        for normal_sizes in (False, True):
            with self.subTest(normal_sizes=normal_sizes):
                source = rf64(normal_sizes=normal_sizes)
                original = source.getvalue()
                wave = WAVE(source)
                wave.add_tags()
                for title in ('First', 'Longer title ' * 500, 'Short'):
                    wave['TIT2'] = TIT2(encoding=3, text=title)
                    wave.save(source, padding=lambda info: 0)
                    wave = WAVE(source)
                    self.assertEqual(wave['TIT2'].text, [title])
                    current = source.getvalue()
                    self.assertEqual(struct.unpack_from('<Q', current, 20)[0],
                                     len(current) - 8)
                    self.assertEqual(current[28:len(original)], original[28:])
                    self.assertEqual(wave.info.length, 1024 / 8000)
                    header_size = struct.unpack_from('<I', current, 4)[0]
                    self.assertEqual(header_size, len(current) - 8
                                     if normal_sizes else 0xffffffff)
                wave.delete(source)
                self.assertIsNone(WAVE(source).tags)
                self.assertEqual(source.getvalue(), original)

    def test_extended_chunks_and_duplicate_ids(self):
        extra = chunk(b'JUNK', b'odd', True) + chunk(b'JUNK', b'longer', True)
        source = rf64(extra, ((b'JUNK', 3), (b'JUNK', 6)))
        self.assertEqual(WAVE(source).info.length, 1024 / 8000)
        wave = WAVE(source)
        wave.add_tags()
        wave['TIT2'] = TIT2(encoding=3, text='After extended chunks')
        wave.save(source)
        self.assertEqual(WAVE(source)['TIT2'].text, ['After extended chunks'])

    def test_tags_before_audio(self):
        source = rf64()
        wave = WAVE(source)
        wave.add_tags()
        wave['TIT2'] = TIT2(encoding=3, text='Before audio')
        wave.save(source, padding=lambda info: 0)
        data = source.getvalue()
        audio_end = 80 + 2048
        source = io.BytesIO(data[:72] + data[audio_end:]
                            + data[72:audio_end])
        for title in ('Larger title ' * 300, 'Small'):
            wave = WAVE(source)
            wave['TIT2'] = TIT2(encoding=3, text=title)
            wave.save(source, padding=lambda info: 0)
            self.assertEqual(WAVE(source)['TIT2'].text, [title])
            self.assertTrue(source.getvalue().endswith(bytes(range(256)) * 8))
        wave.delete(source)
        self.assertEqual(source.getvalue(), rf64().getvalue())

    def test_extended_list(self):
        extra = chunk(b'LIST', b'INFO' + chunk(b'INAM', b'Title'), True)
        source = rf64(extra, ((b'LIST', len(extra) - 8),))
        self.assertEqual(WAVE(source).info.length, 1024 / 8000)
        from mutagen._riff import RiffFile
        source.seek(0)
        container = RiffFile(source)
        self.assertEqual(container['LIST'].subchunks()[0].read(), b'Title')

    def test_extended_id3_size(self):
        from mutagen.id3 import ID3
        tags = ID3()
        tags.add(TIT2(encoding=3, text='Extended ID3 chunk'))
        data = io.BytesIO()
        tags.save(data, padding=lambda info: 0)
        payload = data.getvalue()
        source = rf64(chunk(b'id3 ', payload, True),
                      ((b'id3 ', len(payload)),))
        wave = WAVE(source)
        self.assertEqual(wave['TIT2'].text, ['Extended ID3 chunk'])
        wave['TIT2'] = TIT2(encoding=3, text='Larger ' * 200)
        wave.save(source, padding=lambda info: 0)
        self.assertEqual(WAVE(source)['TIT2'].text, ['Larger ' * 200])
        wave.delete(source)
        self.assertIsNone(WAVE(source).tags)
        self.assertEqual(WAVE(source).info.length, 1024 / 8000)

    def test_normal_sizes_take_precedence(self):
        source = rf64(normal_sizes=True)
        source.seek(20)
        source.write(struct.pack('<QQ', 9999999999, 9999999999))
        self.assertEqual(WAVE(source).info.length, 1024 / 8000)

    def test_invalid_ds64(self):
        original = rf64().getvalue()
        for data in (original[:12], original[:35],
                     original[:12] + b'JUNK' + original[16:],
                     original[:16] + struct.pack('<I', 27) + original[20:],
                     original[:44] + struct.pack('<I', 1) + original[48:]):
            with self.subTest(data=data[:48]):
                self.assertRaises(error, WAVE, io.BytesIO(data))

    def test_missing_extended_size(self):
        source = rf64(chunk(b'JUNK', b'1234', True))
        self.assertRaises(error, WAVE, source)

    @skipUnless(os.name == 'posix', 'Requires sparse file support')
    def test_large_sparse_file(self):
        # Exercise an actual >32-bit seek without allocating 4 GiB of PCM data.
        data_size = 2**32 + 16
        source = rf64()
        prefix = source.getvalue()[:80]
        with tempfile.TemporaryFile() as target:
            target.write(prefix)
            target.seek(20)
            target.write(struct.pack('<QQQ', 72 + data_size, data_size,
                                     data_size // 2))
            target.seek(80 + data_size - 1)
            target.write(b'\x00')
            wave = WAVE(target)
            self.assertEqual(wave.info.length, data_size / 2 / 8000)
            wave.add_tags()
            wave['TIT2'] = TIT2(encoding=3, text='Beyond 4 GiB')
            wave.save(target, padding=lambda info: 0)
            self.assertEqual(WAVE(target)['TIT2'].text, ['Beyond 4 GiB'])
            target.seek(0, 2)
            size = target.tell()
            target.seek(20)
            self.assertEqual(struct.unpack('<Q', target.read(8))[0], size - 8)
            wave.delete(target)
            target.seek(0, 2)
            self.assertEqual(target.tell(), 80 + data_size)
