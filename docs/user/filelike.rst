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


For loading, the file-like object has to implement the following interface:

::

    class IOInterface(object):
        """This is the interface mutagen expects from custom file-like
        objects
        """

        def tell(self):
            """Returns he current offset as int. Always >= 0.

            Raises IOError in case fetching the position is for some reason
            not possible.
            """

            raise NotImplementedError

        def read(self, size=-1):
            """Returns 'size' amount of bytes or less if there is no more data.
            If no size is given all data is returned. size can be >= 0.

            Raises IOError in case reading failed while data was available.
            """

            raise NotImplementedError

        def seek(self, offset, whence=0):
            """Move to a new offset either relative or absolute. whence=0 is
            absolute, whence=1 is relative, whence=2 is relative to the end.

            Any relative or absolute seek operation which would result in a
            negative position is undefined and that case can be ignored
            in the implementation.

            Any seek operation which moves the position after the stream
            should succeed. tell() should report that position and read()
            should return an empty bytes object.

            Raise IOError in case the seek operation asn't possible.
            """

            raise NotImplementedError
