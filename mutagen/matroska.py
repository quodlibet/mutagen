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

from mutagen import Metadata, FileType
import io
from mutagen._util import insert_bytes, delete_bytes, DictProxy, cdata
from mutagen._compat import long_, text_type

from mutagen._ebml import Document, MasterElement, EBMLHeader, UTF8Element, ASCIIElement, UnsignedElement, BinaryElement, ElementSpec


class SimpleTag(MasterElement):
    _child_specs = {
        0x45A3: ElementSpec(0x45A3, 'tag_name', UTF8Element),
        0x447A: ElementSpec(0x447A, 'tag_language', ASCIIElement, mandatory=False),
        0x4484: ElementSpec(0x4484, 'tag_default', UnsignedElement, mandatory=False),
        0x4487: ElementSpec(0x4487, 'tag_string', UTF8Element, mandatory=False),
        0x4485: ElementSpec(0x4485, 'tag_binary', BinaryElement, mandatory=False)
    }

    TAG_NAME = 0x45A3
    TAG_STRING = 0x4487
    TAG_BINARY = 0x4485


class Targets(MasterElement):
    _child_specs = {
        0x68CA: ElementSpec(0x68CA, 'target_type_value', UnsignedElement, mandatory=False, default=50),
        0x63CA: ElementSpec(0x63CA, 'target_type', ASCIIElement, mandatory=False),
        0x63C5: ElementSpec(0x63C5, 'tag_track_uid', UnsignedElement, mandatory=False, default=0),
        0x63C9: ElementSpec(0x63C9, 'tag_edition_uid', UnsignedElement, mandatory=False, default=0),
        0x63C4: ElementSpec(0x63C4, 'tag_chapter_uid', UnsignedElement, mandatory=False, default=0),
        0x63C6: ElementSpec(0x63C6, 'tag_attachment_uid', UnsignedElement, mandatory=False, default=0)
    }

    TARGET_TYPE_VALUE = 0x68CA


class Tag(MasterElement):
    _child_specs = {
        0x63C0: ElementSpec(0x63C0, 'targets', Targets),
        0x67C8: ElementSpec(0x67C8, 'simple_tag', SimpleTag, multiple=True),
    }

    TARGETS = 0x63C0
    SIMPLE_TAG = 0x67C8


class Tags(MasterElement):
    _child_specs = {
        0x7373: ElementSpec(0x7373, "tag", Tag, multiple=True),
    }

    TAG = 0x7373


class Segment(MasterElement):
    _child_specs = {
        0x1254C367: ElementSpec(0x1254C367, "tags", Tags, mandatory=False, multiple=True)
    }

    TAGS = 0x1254C367


class MatroskaDocument(Document):
    _child_specs = {
        0x1A45DFA3: ElementSpec(0x1A45DFA3, "ebml", EBMLHeader, multiple=True),
        0x18538067: ElementSpec(0x18538067, "segment", Segment, multiple=True),
    }

    SEGMENT = 0x18538067


class MatroskaTags(DictProxy, Metadata):
    """ Tags object for accessing Matroska metadata. Metadata is stored on a
    per-target basis. Each target is accessible as a key of the tags object,
    and the corresponding value is a dictionary of tags. For example:

        my_tags = Matroska(fileobj)
        my_tags[50]['artist'] = 'Bob'

    In this initial version, only track-level and album-level tags are
    accessible. Higher-level tags are left intact.
    """

    def load(self, fileobj):
        self.doc = MatroskaDocument(fileobj)

        segments = self.doc.find_children(self.doc.SEGMENT)
        if not segments:
            print "No segments found in file - this is very bad."

        tags_list = segments[0].find_children(Segment.TAGS)

        for tags in tags_list:
            for tag in tags.find_children(Tags.TAG):
                target = tag.find_children(Tag.TARGETS)[0]

                target_type = target.find_children(Targets.TARGET_TYPE_VALUE)

                # Look for a non-zero UID
                uid_ids = [0x63C5, 0x63C9, 0x63C4, 0x63C6]
                nonzero_uids = [x for x in target.children
                                if (x.id in uid_ids) and (x != 0)]

                if (target_type == 50) or (not nonzero_uids):
                    tag_destination = self
                elif target_type == 30:
                    tag_destination = self[nonzero_uids[0]] = {}

                for simple_tag in tag.find_children(Tag.SIMPLE_TAG):
                    key = simple_tag.find_children(SimpleTag.TAG_NAME)[0]

                    str_value = simple_tag.find_children(SimpleTag.TAG_STRING)
                    bin_value = simple_tag.find_children(SimpleTag.TAG_STRING)

                    if str_value:
                        tag_destination[key] = text_type(str_value[0])
                    elif bin_value:
                        tag_destination[key] = bytes(bin_value[0])

    def save(self, filename):
        pass
        #self.doc.segment[0].tags[0].tag[0].simple_tag.clear()


class Matroska(FileType):
    def load(self, filename):
        self.filename = filename
        fileobj = open(filename, "rb")

        self.tags = MatroskaTags(fileobj)
