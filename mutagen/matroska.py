# -*- coding: utf-8 -*-
#
# Copyright 2014 Ben Ockmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Parser for tags within a Matroska container.

Allows editing of the metadata stored in the SimpleTag EBML elements of the
Matroska EBML document.

Based on:
    http://www.matroska.org/technical/specs/index.html

"""

import mutagen
import io
from mutagen._util import insert_bytes, delete_bytes, DictProxy, cdata
from mutagen._compat import long_

from mutagen.ebml import Document, MasterElement, EBMLHeader, UTF8String, String, UnsignedInteger, Binary

class SimpleTag(MasterElement):
    _mandatory_elements = {
        0x45A3: ('tag_name', UTF8String, False),
    }

    _optional_elements = {
        0x447A: ('tag_language', String, False),
        0x4484: ('tag_default', UnsignedInteger, False),
        0x4487: ('tag_string', UTF8String, False),
        0x4485: ('tag_binary', Binary, False),
    }

class Targets(MasterElement):
    _optional_elements = {
        0x68CA: ('target_type_value', UnsignedInteger, False),
        0x63CA: ('target_type', String, False),
        0x63C5: ('tag_track_uid', UnsignedInteger, False),
        0x63C9: ('tag_edition_uid', UnsignedInteger, False),
        0x63C4: ('tag_chapter_uid', UnsignedInteger, False),
        0x63C6: ('tag_attachment_uid', UnsignedInteger, False),
    }


class Tag(MasterElement):
    _mandatory_elements = {
        0x63C0: ('targets', Targets, False),
        0x67C8: ('simple_tag', SimpleTag, True),
    }


class Tags(MasterElement):
    _mandatory_elements = {
        0x7373: ("tag", Tag, True),
    }


class Segment(MasterElement):
    _ignored_elements = {
        0x114D9B74: "seek_head",
        0x1549A966: "info",
        0x1F43B675: "cluster",
        0x1654AE6B: "tracks",
        0x1C53BB6B: "cues",
        0x1941A469: "attachments",
        0x1043A770: "chapters",
    }

    _optional_elements = {
        0x1254C367: ("tags", Tags, True),
    }

class MatroskaDocument(Document):
    _mandatory_elements = {
        0x1A45DFA3: ("ebml", EBMLHeader, True),
        0x18538067: ("segment", Segment, True),
    }

