#! /usr/bin/env python
#
# mutagen aims to be an all purpose media tagging library
# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id$
#

version = (0, 0, -1)

"""
mutagen aims to be an all purpose tagging library.

    import mutagen.[format]
    metadata = mutagen.[format].Open(filename)

metadata is now acts like a dictionary of tags in the file. tags are
generally a list of string-like values, but may have additional methods
available depending on tag or format. They may also be entirely different
objects for certain keys, again depending on format.
"""

class Metadata(dict):
    """Abstract dict-like object that each format inherits for managing
    metadata."""

    def __init__(self, filename=None, fileobj=None):
        """Initializes a tag structure. If fileobj is specified it is the
        source and must include a "read" method or an AttributeError will be
        raised. Otherwise if filename is specified it must exist and be
        readable or normal exceptions will be thrown. Finally for various kinds
        of bad data, a subclass of ValueError may be thrown."""
        raise NotImplementedError

    def save(self, filename=None):
        """Save metadata to previously referenced or newly specified file"""
        raise NotImplementedError

    def delete(self):
        """Remove tags from the open file"""
        raise NotImplementedError
