Mutagen Tutorial
----------------

There are two different ways to load files in Mutagen, but both provide
similar interfaces. The first is the :class:`Metadata <mutagen.Metadata>`
API, which deals only in metadata tags. The second is the :class:`FileType
<mutagen.FileType>` API, which is a superset of the :class:`mutagen
<mutagen.Metadata>` API, and contains information about the audio data
itself.

Both Metadata and FileType objects present a dict-like interface to
edit tags. FileType objects also have an 'info' attribute that gives
information about the song length, as well as per-format
information. In addition, both support the load(filename),
save(filename), and delete(filename) instance methods; if no filename
is given to save or delete, the last loaded filename is used.

This tutorial is only an outline of Mutagen's API. For the full
details, you should read the docstrings (pydoc mutagen) or source
code.

Easy Examples
^^^^^^^^^^^^^

The following code loads a file, sets its title, prints all tag data,
then saves the file, first on a FLAC file, then on a Musepack
file. The code is almost identical.

::

      from mutagen.flac import FLAC
      audio = FLAC("example.flac")
      audio["title"] = "An example"
      audio.pprint()
      audio.save()

::

      from mutagen.apev2 import APEv2
      audio = APEv2("example.mpc")
      audio["title"] = "An example"
      audio.pprint()
      audio.save()

The following example gets the length and bitrate of an MP3 file::

    from mutagen.mp3 import MP3
    audio = MP3("example.mp3")
    print audio.info.length, audio.info.bitrate

The following deletes an ID3 tag from an MP3 file::

    from mutagen.id3 import ID3
    audio = ID3("example.mp3")
    audio.delete()

Hard Examples: ID3
^^^^^^^^^^^^^^^^^^

Unlike Vorbis, FLAC, and APEv2 comments, ID3 data is highly
structured. Because of this, the interface for ID3 tags is very
different from the APEv2 or Vorbis/FLAC interface. For example, to set
the title of an ID3 tag, you need to do the following::

    from mutagen.id3 import ID3, TIT2
    audio = ID3("example.mp3")
    audio.add(TIT2(encoding=3, text=u"An example"))
    audio.save()

If you use the ID3 module, you should familiarize yourself with how
ID3v2 tags are stored, by reading the the details of the ID3v2
standard at http://www.id3.org/develop.html.


ID3 Versions
^^^^^^^^^^^^

.. py:currentmodule:: mutagen.id3

Mutagen's ID3 API is primary targeted at id3v2.4, so by default any id3 tags
will be upgraded to 2.4 and saving a file will make it 2.4 as well. Saving as
2.3 is possible but needs some extra steps.

By default mutagen will:

* Load the file
* Upgrade any ID3v2.2 frames to their ID3v2.3/4 counterparts
  (``TT2`` to ``TIT2`` for example)
* Upgrade 2.3 only frames to their 2.4 counterparts or throw them away in
  case there exists no sane upgrade path.

In code it comes down to this::

    from mutagen.id3 import ID3

    audio = ID3("example.mp3")
    audio.save()

The :attr:`ID3.version` attribute contains the id3 version the loaded file
had.

For more control the following functions are important:

* :func:`ID3` which loads the tags and if ``translate=True``
  (default) calls either :meth:`ID3.update_to_v24` or
  :meth:`ID3.update_to_v23` depending on the ``v2_version``
  argument (defaults to ``4``)

* :meth:`ID3.update_to_v24` which upgrades v2.2/3 frames to v2.4

* :meth:`ID3.update_to_v23` which downgrades v2.4 and upgrades v2.2 frames to v2.3

* :meth:`ID3.save` which will save as v2.3 if ``v2_version=3`` (defaults to
  ``4``) and also allows specifying a separator for joining multiple text
  values into one (defaults to ``v23_sep='/'``).

To load any ID3 tag and save it as v2.3 do the following::

    from mutagen.id3 import ID3

    audio = ID3("example.mp3", v2_version=3)
    audio.save(v2_version=3)

You may notice that if you load a v2.4 file this way, the text frames will
still have multiple values or are defined to be saved using UTF-8, both of
which isn't valid in v2.3. But the resulting file will still be valid because
the following will happen in :meth:`ID3.save`:

* Frames that use UTF-8 as text encoding will be saved as UTF-16 instead.
* Multiple values in text frames will be joined with ``v23_sep`` as passed to
  :meth:`ID3.save`.


Nonstandard ID3v2.3 Tricks
~~~~~~~~~~~~~~~~~~~~~~~~~~

Saving v2.4 frames in v2.3 tags
    While not standard conform, you can exclude certain v2.4 frames from being
    thrown out by :meth:`ID3.update_to_v23` by removing them temporarily::

        audio = ID3("example.mp3", translate=False)
        keep_these = audio.getall("TSOP")
        audio.update_to_v23()
        audio.setall("TSOP", keep_these)
        audio.save(v2_version=3)

Saving Multiple Text Values in v2.3 Tags
    The v2.3 standard states that after a text termination "all the following
    information should be ignored and not be displayed". So, saving multiple
    values separated by the text terminator should allow v2.3 only readers to
    read the first value while providing a way to read all values back.

    But editing these files will probably throw out all the other values and
    some implementations might get confused about the extra non-NULL data, so
    this isn't recommended.

    To use the terminator as value separator pass ``v23_sep=None`` to
    :meth:`ID3.save`.

    ::

        audio = ID3("example.mp3", v2_version=3)
        audio.save(v2_version=3, v23_sep=None)

    Mutagen itself disregards the v2.3 spec in this case and will read them
    back as multiple values.


Easy ID3
^^^^^^^^

Since reading standards is hard, Mutagen also provides a simpler ID3
interface.

::

    from mutagen.easyid3 import EasyID3
    audio = EasyID3("example.mp3")
    audio["title"] = u"An example"
    audio.save()

Because of the simpler interface, only a few keys can be edited by
EasyID3; to see them, use::

    from mutagen.easyid3 import EasyID3
    print EasyID3.valid_keys.keys()

By default, mutagen.mp3.MP3 uses the real ID3 class. You can make it
use EasyID3 as follows::

    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    audio = MP3("example.mp3", ID3=EasyID3)
    audio.pprint()

Unicode
^^^^^^^

Mutagen has full Unicode support for all formats. When you assign text
strings, we strongly recommend using Python unicode objects rather
than str objects. If you use str objects, Mutagen will assume they are
in UTF-8.

(This does not apply to strings that must be interpreted as bytes, for
example filenames. Those should be passed as str objectss, and will
remain str objects within Mutagen.)

Multiple Values
^^^^^^^^^^^^^^^

Most tag formats support multiple values for each key, so when you
access then (e.g. ``audio["title"]``) you will get a list of strings
rather than a single one (``[u"An example"]`` rather than ``u"An example"``).
Similarly, you can assign a list of strings rather than a single one.


VorbisComment
^^^^^^^^^^^^^

VorbisComment is the tagging format used in Ogg and FLAC container formats. In
mutagen this corresponds to the tags in all subclasses of
:class:`mutagen.ogg.OggFileType` and the :class:`mutagen.flac.FLAC` class.

Embedded Images
~~~~~~~~~~~~~~~

The most common way to include images in VorbisComment is to store a base64
encoded FLAC Picture block with the key ``metadata_block_picture`` [0]. See
the following code example on how to read and write images this way::

    # READING / SAVING
    import base64
    from mutagen.oggvorbis import OggVorbis
    from mutagen.flac import Picture, error as FLACError

    file_ = OggVorbis("somefile.ogg")

    for b64_data in file_.get("metadata_block_picture", []):
        try:
            data = base64.b64decode(b64_data)
        except (TypeError, ValueError):
            continue

        try:
            picture = Picture(data)
        except FLACError:
            continue

        extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
        }
        ext = extensions.get(picture.mime, "jpg")

        with open("image.%s" % ext, "wb") as h:
            h.write(picture.data)

::

    # WRITING
    import base64
    from mutagen.oggvorbis import OggVorbis
    from mutagen.flac import Picture

    file_ = OggVorbis("somefile.ogg")

    with open("image.jpeg", "rb") as h:
        data = h.read()

    picture = Picture()
    picture.data = data
    picture.type = 17
    picture.desc = u"A bright coloured fish"
    picture.mime = u"image/jpeg"
    picture.width = 100
    picture.height = 100
    picture.depth = 24

    picture_data = picture.write()
    encoded_data = base64.b64encode(picture_data)
    vcomment_value = encoded_data.decode("ascii")

    file_["metadata_block_picture"] = [vcomment_value]
    file_.save()


Some programs also write base64 encoded image data directly into the
``coverart`` field and sometimes a corresponding mime type into the
``coverartmime`` field::

    # READING
    import base64
    import itertools
    from mutagen.oggvorbis import OggVorbis

    file_ = OggVorbis("somefile.ogg")

    values = file_.get("coverart", [])
    mimes = file_.get("coverartmime", [])
    for value, mime in itertools.izip_longest(values, mimes, fillvalue=u""):
        try:
            image_data = base64.b64decode(value.encode("ascii"))
        except (TypeError, ValueError):
            continue

        print(mime)
        print(image_data)


FLAC supports images directly, see :class:`mutagen.flac.Picture`,
:attr:`mutagen.flac.FLAC.pictures`, :meth:`mutagen.flac.FLAC.add_picture` and
:meth:`mutagen.flac.FLAC.clear_pictures`.


[0] https://wiki.xiph.org/VorbisComment#Cover_art


Padding
~~~~~~~

Many formats mutagen supports include a notion of metadata padding, empty
space in the file following the metadata. In case the size of the metadata
increases, this empty space can be claimed and written into. The alternative
would be to resize the whole file, which means everything after the metadata
needs to be rewritten. This can be a time consuming operation if the file is
large.

For formats where mutagen supports using such a padding it will use the
existing padding for extending metadata, add additional padding if the added
data exceeds the size of the existing padding and reduce the padding size if
it makes up more than a significant part of the file size.

It also provides additional API to control the padding usage. Some
`mutagen.FileType` and `mutagen.Metadata` subclasses provide a ``save()``
method which can be passed a padding callback. This callback gets called with
a `mutagen.PaddingInfo` instance and should return the amount of padding to
write to the file.

::

    from mutagen.mp3 import MP3

    def no_padding(info):
        # this will remove all padding
        return 0

    def default_implementation(info):
        # this is the default implementation, which can be extended
        return info.get_default_padding()

    def no_new_padding(info):
        # this will use existing padding but never add new one
        return max(info.padding, 0)

    f = MP3("somefile.mp3")
    f.save(padding=no_padding)
    f.save(padding=default_implementation)
    f.save(padding=no_new_padding)
