WAVE
----

WAVE supports RIFF and RF64 containers, including reading and writing ID3v2
tags in existing RF64 files. RF64 stores extended chunk sizes in its ``ds64``
chunk, allowing audio data larger than 4 GiB.

.. automodule:: mutagen.wave

.. autoclass:: mutagen.wave.WAVE(filename)
    :show-inheritance:
    :members:

.. autoclass:: mutagen.wave.WaveStreamInfo()
    :members:
