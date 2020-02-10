==============================
Working with File-like Objects
==============================

.. currentmodule:: mutagen

The first argument passed to a :class:`FileType` or :class:`Metadata` can
either be a file name or a file-like object, such as `BytesIO <io.BytesIO>`
and mutagen will figure out what to do.

::

    MP3("myfile.mp3")
    MP3(myfileobj)


If for some reason the automatic type detection fails, it's possible to pass
them using a named argument which skips the type guessing.

::

    MP3(filename="myfile.mp3")
    MP3(fileobj=myfileobj)


Mutagen expects the file offset to be at 0 for all file objects passed to it.

The file-like object has to implement the following interface (It's a limited
subset of real buffered file objects and StringIO/BytesIO)

.. literalinclude:: examples/fileobj-iface.py


Gio Example Implementation
--------------------------

The following implements a file-like object using `PyGObject
<https://wiki.gnome.org/PyGObject>`__ and `Gio
<https://developer.gnome.org/gio/stable/ch01.html>`__. It depends on the
`giofile <https://github.com/lazka/giofile>`__ Python library.


.. code:: python

    import mutagen
    import giofile
    from gi.repository import Gio

    gio_file = Gio.File.new_for_uri(
        "http://people.xiph.org/~giles/2012/opus/ehren-paper_lights-96.opus")

    cancellable = Gio.Cancellable.new()
    with giofile.open(gio_file, "rb", cancellable=cancellable) as gfile:
        print(mutagen.File(gfile).pprint())

.. code:: sh

    $ python example.py
    Ogg Opus, 228.11 seconds (audio/ogg)
    ENCODER=opusenc from opus-tools 0.1.5
    artist=Ehren Starks
    title=Paper Lights
    album=Lines Build Walls
    date=2005-09-05
    copyright=Copyright 2005 Ehren Starks
    license=http://creativecommons.org/licenses/by-nc-sa/1.0/
    organization=magnatune.com
