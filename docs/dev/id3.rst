ID3
===

`ID3 Website <https://web.archive.org/web/20190103005542/http://id3.org/Home>`__

ID3v2.4.0:
    * `ID3v2.4.0 Main Structure <https://web.archive.org/web/20200805181446/https://id3.org/id3v2.4.0-structure>`__
    * `ID3v2.4.0 Native Frames <https://web.archive.org/web/20200806134515/https://id3.org/id3v2.4.0-frames>`__
    * `ID3v2.4.0 Changes <https://web.archive.org/web/20181102144806/http://www.id3.org/id3v2.4.0-changes>`__

ID3v2.3.0:
    * `ID3v2.3.0 Informal standard <https://web.archive.org/web/20180814201738/http://id3.org/d3v2.3.0>`__
    * `ID3v2 Programming Guidlines <https://web.archive.org/web/20180814205538/http://id3.org/id3guide>`__

ID3v2.2.0:
    * `ID3v2.2.0 Informal standard <https://web.archive.org/web/20181229090829/http://www.id3.org/id3v2-00>`__

Additional standards:
  * `ID3v2 Chapter Frame Addendum v1.0 <https://web.archive.org/web/20200809234704/https://id3.org/id3v2-chapters-1.0>`__
  * `ID3v2 Accessibility Addendum v1.0 <https://web.archive.org/web/20181119131208/http://id3.org/id3v2-accessibility-1.0>`__


Mutagen Implementation Details
------------------------------

* We don't interpret or write the "ID3v2 extended header". An existing extended
  header gets removed when saving the tags.

  * https://github.com/quodlibet/mutagen/pull/631#issuecomment-1742118078

* We don't support appended tags. They will neither be found nor updated.

  * https://github.com/quodlibet/mutagen/issues/78

* We always NULL-terminate multivalue text frames and ignore them when parsing

  * https://github.com/quodlibet/mutagen/issues/379#issuecomment-486852503
