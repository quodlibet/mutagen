========
 mid3cp
========

-------------
copy ID3 tags
-------------

:Manual section: 1


SYNOPSIS
========

**mid3cp** [*options*] *source* *dest*


DESCRIPTION
===========

**mid3cp** copies the ID3 tags from a source file to a destination file.

It is designed to provide similar functionality to id3lib's id3cp tool, and can
optionally write ID3v1 tags. It can also exclude specific tags from being
copied.


OPTIONS
=======

--verbose, -v
    Be verbose: state all operations performed, and list tags in source file.

--write-v1
    Write ID3v1 tags to the destination file, derived from the ID3v2 tags.

--exclude-tag, -x
    Exclude a specific tag from being copied. Can be specified multiple times.



AUTHOR
======

Marcus Sundman.

Based on id3cp (part of id3lib) by Dirk Mahoney and Scott Thomas Haug.
