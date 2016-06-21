===
ID3
===

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
standard at http://id3.org/id3v2.4.0-structure.


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
    print(EasyID3.valid_keys.keys())

By default, mutagen.mp3.MP3 uses the real ID3 class. You can make it
use EasyID3 as follows::

    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    audio = MP3("example.mp3", ID3=EasyID3)
    audio.pprint()


Compatibility / Bugs
^^^^^^^^^^^^^^^^^^^^

* Mutagen writes ID3v2.4 tags which id3lib cannot read. If you enable
  ID3v1 tag saving (pass v1=2 to ID3.save), id3lib will read those.

* iTunes has a bug in its handling of very large ID3 tags (such as tags
  that contain an attached picture). Mutagen can read tags from iTunes, but
  iTunes may not be able to read tags written by Quod Libet.

* Mutagen has had several bugs in correct sync-safe parsing and writing
  of data length flags in ID3 tags. This will only affect files with very
  large or compressed ID3 frames (e.g. APIC). As of 1.10 we believe them all
  to be fixed.

* Mutagen 1.18 moved EasyID3FileType to mutagen.easyid3, rather than
  mutagen.id3, which was used in 1.17. Keeping in mutagen.id3 caused circular
  import problems.

* Mutagen 1.19 made it possible for POPM to have no 'count'
  attribute. Previously, files that generated POPM frames of this type would
  fail to load at all.

* When given date frames less than four characters long (which are
  already outside the ID3v2 specification), Mutagen 1.20 and earlier would
  write invalid ID3v1 tags that were too short. Mutagen 1.21 will parse these
  and fix them if it finds them while saving.
