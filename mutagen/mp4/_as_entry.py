# -*- coding: utf-8 -*-
# Copyright (C) 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from mutagen._util import cdata
from mutagen._compat import cBytesIO, xrange
from ._util import parse_full_atom
from ._atom import Atom, AtomError


def _parse_desc_length(data, offset):
    """Returns the decoded value and the new offset in data after the value.
    Can raise ValueError in case the value is too long or data too short.
    """

    value = 0
    for i in xrange(4):
        try:
            b, offset = cdata.uint8_from(data, offset)
        except cdata.error as e:
            raise ValueError(e)
        value = (value << 7) | (b & 0x7f)
        if not b >> 7:
            break
    else:
        raise ValueError("invalid descriptor length")

    return value, offset


class AudioSampleEntry(object):
    """Parses an AudioSampleEntry atom.

    Private API.

    Attrs:
        channels (int): number of channels
        sample_size (int): sample size in bits
        sample_rate (int): sample rate in Hz
        bitrate (int): bits per second (0 means unknown)
        codec (string): audio codec, either 'mp4a' or 'alac'

    Can raise ValueError.
    """

    channels = 0
    sample_size = 0
    sample_rate = 0
    bitrate = 0
    codec = None

    def __init__(self, atom, fileobj):
        if atom.name in (b"mp4a", b"alac"):
            self.codec = atom.name.decode()
        else:
            raise ValueError("Unsupported coding name %s" % atom.name)

        ok, data = atom.read(fileobj)
        if not ok or len(data) < 28:
            raise ValueError("too short %s atom" % atom.name)

        # SampleEntry
        off = 6  # reserved
        off += 2  # data_ref_index

        # AudioSampleEntry
        off += 8  # reserved
        self.channels, off = cdata.uint16_be_from(data, off)
        self.sample_size, off = cdata.uint16_be_from(data, off)
        off += 2  # pre_defined
        off += 2  # reserved
        sample_rate, off = cdata.uint32_be_from(data, off)
        # defined as Q16.16, but the fraction part seems unused..
        # self.sample_rate = sample_rate * 2 ** (-16)
        self.sample_rate = sample_rate >> 16
        assert off == 28

        fileobj = cBytesIO(data[off:])

        try:
            extra = Atom(fileobj)
        except AtomError as e:
            raise ValueError(e)

        # esds only in mp4a atoms
        if atom.name == b"mp4a" and extra.name == b"esds":
            self._parse_esds(extra, fileobj)
        elif atom.name == b"alac" and extra.name == b"alac":
            self._parse_alac(extra, fileobj)

    def _parse_alac(self, atom, fileobj):
        # https://alac.macosforge.org/trac/browser/trunk/
        #    ALACMagicCookieDescription.txt

        assert atom.name == b"alac"

        ok, data = atom.read(fileobj)
        if not ok:
            raise ValueError("truncated %s atom" % atom.name)

        version, flags, data = parse_full_atom(data)
        if version != 0:
            # unsupported version, ignore
            return

        # for some files the AudioSampleEntry values default to 44100/2chan
        # and the real info is in the alac cookie, so prefer it
        try:
            self.channels, off = cdata.uint8_from(data, 9)
            off += 6  # skip some stuff
            self.bitrate, off = cdata.uint32_be_from(data, off)
            self.sample_rate, off = cdata.uint32_be_from(data, off)
        except cdata.error as e:
            raise ValueError(e)

    def _parse_esds(self, esds, fileobj):
        assert esds.name == b"esds"

        ok, data = esds.read(fileobj)
        if not ok:
            raise ValueError("truncated %s atom" % esds.name)

        version, flags, data = parse_full_atom(data)
        if version != 0:
            # unsupported version, ignore
            return

        try:
            tag, off = cdata.uint8_from(data, 0)
            ES_DescrTag = 0x03
            if tag != ES_DescrTag:
                raise ValueError("unexpected descriptor: %d" % tag)

            base_size, off = _parse_desc_length(data, off)
            es_id, off = cdata.uint16_be_from(data, off)
            es_flags, off = cdata.uint8_from(data, off)
            streamDependenceFlag = cdata.test_bit(es_flags, 7)
            URL_Flag = cdata.test_bit(es_flags, 6)
            OCRstreamFlag = cdata.test_bit(es_flags, 5)
            # streamPriority = es_flags & 0x1f
            if streamDependenceFlag:
                off += 2  # dependsOn_ES_ID
            if URL_Flag:
                url_len, off = cdata.uint8_from(data, off)
                off += url_len  # URLstring
            if OCRstreamFlag:
                off += 2  # OCR_ES_Id
            DecoderConfigDescrTag = 4
            tag, off = cdata.uint8_from(data, off)
            if tag != DecoderConfigDescrTag:
                raise ValueError("unexpected DecoderConfigDescrTag %d" % tag)

            dec_conf_size, off = _parse_desc_length(data, off)
            off += 9  # skip some stuff
            # average bitrate
            self.bitrate, off = cdata.uint32_be_from(data, off)
        except cdata.error as e:
            raise ValueError(e)
