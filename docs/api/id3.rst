ID3v2
=====

.. automodule:: mutagen.id3


ID3 Frames
----------

.. toctree::
    :titlesonly:

    id3_frames


ID3
---

.. autoclass:: mutagen.id3.ID3
    :show-inheritance:
    :members:

.. autoclass:: mutagen.id3.ID3FileType
    :members:
    :exclude-members: ID3


EasyID3
-------

.. automodule:: mutagen.easyid3

.. autoclass:: mutagen.easyid3.EasyID3
    :show-inheritance:
    :members:

.. autoclass:: mutagen.easyid3.EasyID3FileType
    :show-inheritance:
    :members:
    :exclude-members: ID3


MP3
---

.. automodule:: mutagen.mp3

.. autoclass:: mutagen.mp3.MP3
    :show-inheritance:
    :members:

.. autoclass:: mutagen.mp3.MPEGInfo
    :members:

.. autoclass:: mutagen.mp3.EasyMP3
    :show-inheritance:
    :members:
    :exclude-members: ID3


TrueAudio
---------

.. automodule:: mutagen.trueaudio

.. autoclass:: mutagen.trueaudio.TrueAudio
    :show-inheritance:
    :members:

.. autoclass:: mutagen.trueaudio.TrueAudioInfo
    :members:

.. autoclass:: mutagen.trueaudio.EasyTrueAudio
    :show-inheritance:
    :members:
    :exclude-members: ID3
