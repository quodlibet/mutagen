from io import BytesIO

from mutagen import File, Metadata
from mutagen import MutagenError
from mutagen.asf import ASF
from mutagen.apev2 import APEv2File, APEv2
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3FileType, EasyID3
from mutagen.id3 import ID3FileType, ID3
from mutagen.mp3 import MP3
from mutagen.mp3 import EasyMP3
from mutagen.oggflac import OggFLAC
from mutagen.oggspeex import OggSpeex
from mutagen.oggtheora import OggTheora
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.trueaudio import EasyTrueAudio
from mutagen.trueaudio import TrueAudio
from mutagen.wavpack import WavPack
from mutagen.easymp4 import EasyMP4
from mutagen.mp4 import MP4
from mutagen.musepack import Musepack
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.optimfrog import OptimFROG
from mutagen.aiff import AIFF
from mutagen.aac import AAC
from mutagen.ac3 import AC3
from mutagen.smf import SMF
from mutagen.tak import TAK
from mutagen.dsf import DSF
from mutagen.wave import WAVE
from mutagen.dsdiff import DSDIFF


OPENERS = [
    MP3, TrueAudio, OggTheora, OggSpeex, OggVorbis, OggFLAC,
    FLAC, AIFF, APEv2File, MP4, ID3FileType, WavPack,
    Musepack, MonkeysAudio, OptimFROG, ASF, OggOpus, AC3,
    TAK, DSF, EasyMP3, EasyID3FileType, EasyTrueAudio, EasyMP4,
    File, SMF, AAC, EasyID3, ID3, APEv2, WAVE, DSDIFF]

# If you only want to test one:
# OPENERS = [AAC]


def run(opener, f):
    try:
        res = opener(f)
    except MutagenError:
        return

    # File is special and returns None if loading fails
    if opener is File and res is None:
        return

    # These can still fail because we might need to parse more data
    # to rewrite the file

    f.seek(0)
    try:
        res.save(f)
    except MutagenError:
        return

    f.seek(0)
    res = opener(f)

    f.seek(0)
    try:
        res.delete(f)
    except MutagenError:
        return

    # These can also save to empty files
    if isinstance(res, Metadata):
        f = BytesIO()
        res.save(f)
        f.seek(0)
        opener(f)
        f.seek(0)
        res.delete(f)


def run_all(data):
    f = BytesIO(data)
    [run(opener, f) for opener in OPENERS]


def group_crashes(result_path):
    """Re-checks all errors, and groups them by stack trace
    and error type.
    """

    crash_paths = []
    pattern = os.path.join(result_path, '**', 'crashes', '*')
    for path in glob.glob(pattern):
        if os.path.splitext(path)[-1] == ".txt":
            continue
        crash_paths.append(path)

    if not crash_paths:
        print("No crashes found")
        return

    def norm_exc():
        lines = traceback.format_exc().splitlines()
        if ":" in lines[-1]:
            lines[-1], message = lines[-1].split(":", 1)
        else:
            message = ""
        return "\n".join(lines), message.strip()

    traces = {}
    messages = {}
    for path in crash_paths:
        with open(path, "rb") as h:
            data = h.read()
        try:
            run_all(data)
        except Exception:
            trace, message = norm_exc()
            messages.setdefault(trace, set()).add(message)
            traces.setdefault(trace, []).append(path)

    for trace, paths in traces.items():
        print('-' * 80)
        print("\n".join(paths))
        print()
        print(textwrap.indent(trace, '    '))
        print(messages[trace])

    print("%d crashes with %d traces" % (len(crash_paths), len(traces)))


if __name__ == '__main__':
    import sys
    import glob
    import os
    import traceback
    import textwrap
    group_crashes(sys.argv[1])
