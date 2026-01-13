# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Standard MIDI File (SMF)"""

import struct
from io import BytesIO
from typing import cast, final, override

from mutagen import MutagenError, StreamInfo
from mutagen._file import FileType
from mutagen._filething import FileThing
from mutagen._util import endswith, loadfile


class SMFError(MutagenError):
    pass


def _var_int(data: bytearray, offset: int = 0) -> tuple[int, int]:
    val = 0
    while 1:
        try:
            x = data[offset]
        except IndexError:
            raise SMFError("Not enough data") from IndexError
        offset += 1
        val = (val << 7) + (x & 0x7F)
        if not (x & 0x80):
            return val, offset
    raise AssertionError("unreachable")

def _read_track(chunkb: bytes):
    """Returns a list of midi events and tempo change events"""

    TEMPO = 0
    MIDI = 1

    # Deviations: The running status should be reset on non midi events, but
    # some files contain meta events in between.
    # TODO: Offset and time signature are not considered.

    tempos: list[tuple[int, int, int]] = []
    events: list[tuple[int, int, int]] = []

    chunk = bytearray(chunkb)
    deltasum = 0
    status = 0
    off = 0
    while off < len(chunk):
        delta, off = _var_int(chunk, off)
        deltasum += delta
        event_type = chunk[off]
        off += 1
        if event_type == 0xFF:
            meta_type = chunk[off]
            off += 1
            num, off = _var_int(chunk, off)
            # TODO: support offset/time signature
            if meta_type == 0x51:
                data = chunk[off:off + num]
                if len(data) != 3:
                    raise SMFError
                tempo = cast(int, struct.unpack(">I", b"\x00" + bytes(data))[0])
                tempos.append((deltasum, TEMPO, tempo))
            off += num
        elif event_type in (0xF0, 0xF7):
            val, off = _var_int(chunk, off)
            off += val
        else:
            if event_type < 0x80:
                # if < 0x80 take the type from the previous midi event
                off += 1
                event_type = status
            elif event_type < 0xF0:
                off += 2
                status = event_type
            else:
                raise SMFError("invalid event")

            if event_type >> 4 in (0xD, 0xC):
                off -= 1

            events.append((deltasum, MIDI, delta))

    return events, tempos


def _read_midi_length(fileobj: BytesIO) -> float:
    """Returns the duration in seconds. Can raise all kind of errors..."""

    TEMPO = 0
    MIDI = 1  # noqa: F841  # pyright: ignore[reportUnusedVariable]

    def read_chunk(fileobj: BytesIO) -> tuple[bytes, bytes]:
        info = fileobj.read(8)
        if len(info) != 8:
            raise SMFError("truncated")
        chunklen = cast(int, struct.unpack(">I", info[4:])[0])
        data = fileobj.read(chunklen)
        if len(data) != chunklen:
            raise SMFError("truncated")
        return info[:4], data

    identifier, chunk = read_chunk(fileobj)
    if identifier != b"MThd":
        raise SMFError("Not a MIDI file")

    if len(chunk) != 6:
        raise SMFError("truncated")

    format_, ntracks, tickdiv = cast(tuple[int, int, int], struct.unpack(">HHH", chunk))
    if format_ > 1:
        raise SMFError(f"Not supported format {format_}")

    if tickdiv >> 15:
        # fps = (-(tickdiv >> 8)) & 0xFF
        # subres = tickdiv & 0xFF
        # never saw one of those
        raise SMFError("Not supported timing interval")

    # get a list of events and tempo changes for each track
    tracks: list[list[tuple[int, int, int]]] = []
    first_tempos = None
    for _tracknum in range(ntracks):
        identifier, chunk = read_chunk(fileobj)
        if identifier != b"MTrk":
            continue
        events, tempos = _read_track(chunk)

        # In case of format == 1, copy the first tempo list to all tracks
        first_tempos = first_tempos or tempos
        if format_ == 1:
            tempos = list(first_tempos)
        events += tempos
        events.sort()
        tracks.append(events)

    # calculate the duration of each track
    durations: list[float] = []
    for events in tracks:
        tempo = 500000
        parts: list[tuple[int, int]] = []
        deltasum = 0
        for (_dummy, type_, data) in events:
            if type_ == TEMPO:
                parts.append((deltasum, tempo))
                tempo = data
                deltasum = 0
            else:
                deltasum += data
        parts.append((deltasum, tempo))

        duration = 0.0
        for (deltasum, tempo) in parts:
            quarter, tpq = deltasum / float(tickdiv), tempo
            duration += (quarter * tpq)
        duration /= 10 ** 6

        durations.append(duration)

    # return the longest one
    return max(durations)

@final
class SMFInfo(StreamInfo):
    """SMFInfo()

    Attributes:
        length (`float`): Length in seconds

    """

    length: float

    def __init__(self, fileobj: BytesIO):
        """Raises SMFError"""

        self.length = _read_midi_length(fileobj)

    @override
    def pprint(self):
        return f"SMF, {self.length:.2f} seconds"

@final
class SMF(FileType):
    """SMF(filething)

    Standard MIDI File (SMF)

    Attributes:
        info (`SMFInfo`)
        tags: `None`
    """

    _mimes: list[str] = ["audio/midi", "audio/x-midi"]

    info: SMFInfo
    tags = None

    @loadfile()
    def load(self, filething: FileThing):
        try:
            self.info = SMFInfo(filething.fileobj)
        except OSError as e:
            raise SMFError(e) from e

    @override
    def add_tags(self):
        raise SMFError("doesn't support tags")

    @staticmethod
    @override
    def score(filename: str, fileobj: BytesIO, header: bytes):
        filename = filename.lower()
        return header.startswith(b"MThd") and (
            endswith(filename, ".mid") or endswith(filename, ".midi"))


Open = SMF
error = SMFError

__all__ = ["SMF"]
