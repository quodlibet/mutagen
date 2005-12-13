#!/usr/bin/python

import popen2, os, sys
from mutagen.id3 import ID3, RVA2

def process_files(files):
    r, w = popen2.popen2(["mp3gain", "-q", "-o", "-s", "s"] + files)
    lines = []
    for line in r:
        line = line.strip()
        lines.append(line)
    lines.pop(0)
    name, gain, db, amp, max, min = lines.pop().split("\t")
    peak = float(amp) / 32768.
    db = float(db.split()[0])
    albumrva2 = RVA2(desc="album", channel=1, gain=db, peak=peak)
    print repr(albumrva2)

    finals = []
    print "Album: %s" % albumrva2
    for line, filename in zip(lines, files):
        name, gain, db, amp, max, min = line.split("\t")
        peak = float(amp) / 32768.
        db = float(db.split()[0])
        rva2 = RVA2(desc="track", channel=1, gain=db, peak=peak)
        print "%s: %s" % (filename, rva2)
        tag = ID3(filename)
        tag.loaded_frame(albumrva2)
        tag.loaded_frame(rva2)
        tag.save()

if __name__ == "__main__":
    if os.system("mp3gain 2> /dev/null") != 256:
        raise SystemExit("mp3gain not found.")
    else: process_files(sys.argv[1:])
