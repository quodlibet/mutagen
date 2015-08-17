ID3v2
=====

.. automodule:: mutagen.id3


ID3 Frames
----------

.. toctree::
    :titlesonly:

    id3_frames


.. autoclass:: mutagen.id3.PictureType
    :members:
    :member-order: bysource


.. autoclass:: mutagen.id3.Encoding
    :members:
    :member-order: bysource

ID3
---

.. autoclass:: mutagen.id3.ID3()
    :show-inheritance:
    :members:
    :exclude-members: loaded_frame

.. autoclass:: mutagen.id3.ID3FileType(filename, ID3=None)
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

.. autoclass:: mutagen.mp3.MP3(filename, ID3=None)
    :show-inheritance:
    :members:

.. autoclass:: mutagen.mp3.MPEGInfo()
    :members:

.. autoclass:: mutagen.mp3.BitrateMode()
    :members:

.. autoclass:: mutagen.mp3.EasyMP3(filename, ID3=None)
    :show-inheritance:
    :members:
    :exclude-members: ID3


TrueAudio
---------

.. automodule:: mutagen.trueaudio

.. autoclass:: mutagen.trueaudio.TrueAudio(filename, ID3=None)
    :show-inheritance:
    :members:

.. autoclass:: mutagen.trueaudio.TrueAudioInfo()
    :members:

.. autoclass:: mutagen.trueaudio.EasyTrueAudio(filename, ID3=None)
    :show-inheritance:
    :members:
    :exclude-members: ID3

AIFF
----

.. automodule:: mutagen.aiff

.. autoclass:: mutagen.aiff.AIFF(filename)
    :show-inheritance:
    :members:

.. autoclass:: mutagen.aiff.AIFFInfo()
    :members:
