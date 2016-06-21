==============================
Loading from File-like Objects
==============================

.. currentmodule:: mutagen

The first argument passed to a :class:`FileType` or :class:`Metadata` can
either be a file name or a file-like object, such as `StringIO
<StringIO.StringIO>`  (`BytesIO <io.BytesIO>` in Python 3) and mutagen will
figure out what to do.

::

    MP3("myfile.mp3")
    MP3(myfileobj)


If for some reason the automatic type detection fails, it's possible to pass
them using a named argument which skips the type guessing.

::

    MP3(filename="myfile.mp3")
    MP3(fileobj=myfileobj)


For loading, the file-like objects has to support the methods ``read()``,
``seek()``, ``tell()`` and it has to return `bytes`.
