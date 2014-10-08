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

from mutagen._ebml import Document, MasterElement, EBMLHeader, UTF8String, String, UnsignedInteger, Binary, ElementSpec

class SimpleTag(MasterElement):
    _child_specs = {
        0x45A3: ElementSpec(0x45A3, 'tag_name', UTF8String),
        0x447A: ElementSpec(0x447A, 'tag_language', String, mandatory=False),
        0x4484: ElementSpec(0x4484, 'tag_default', UnsignedInteger, mandatory=False),
        0x4487: ElementSpec(0x4487, 'tag_string', UTF8String, mandatory=False),
        0x4485: ElementSpec(0x4485, 'tag_binary', Binary, mandatory=False)
    }

class Targets(MasterElement):
    _child_specs = {
        0x68CA: ElementSpec(0x68CA, 'target_type_value', UnsignedInteger, mandatory=False),
        0x63CA: ElementSpec(0x63CA, 'target_type', String, mandatory=False),
        0x63C5: ElementSpec(0x63C5, 'tag_track_uid', UnsignedInteger, mandatory=False),
        0x63C9: ElementSpec(0x63C9, 'tag_edition_uid', UnsignedInteger, mandatory=False),
        0x63C4: ElementSpec(0x63C4, 'tag_chapter_uid', UnsignedInteger, mandatory=False),
        0x63C6: ElementSpec(0x63C6, 'tag_attachment_uid', UnsignedInteger, mandatory=False)
    }


class Tag(MasterElement):
    _child_specs = {
        0x63C0: ElementSpec(0x63C0, 'targets', Targets),
        0x67C8: ElementSpec(0x67C8, 'simple_tag', SimpleTag, multiple=True),
    }


class Tags(MasterElement):
    _child_specs = {
        0x7373: ElementSpec(0x7373, "tag", Tag, multiple=True),
    }


class Segment(MasterElement):
    _child_specs = {
        0x1254C367: ElementSpec(0x1254C367, "tags", Tags, mandatory=False, multiple=True)
    }


class MatroskaDocument(Document):
    _child_specs = {
        0x1A45DFA3: ElementSpec(0x1A45DFA3, "ebml", EBMLHeader, multiple=True),
        0x18538067: ElementSpec(0x18538067, "segment", Segment, multiple=True),
    }

class MatroskaTags(DictProxy, Metadata):
    
    def load(self, fileobj):
        self.doc = MatroskaDocument(fileobj)
        
        for tag in self.doc.segment[0].tags[0].tag[0].simple_tag:
            if hasattr(tag, 'tag_string'):
                self[tag.tag_name] = text_type(tag.tag_string)
            else:
                self[tag.tag_name] = bytes(tag.tag_binary)


    def save(self, filename):
        pass
        #self.doc.segment[0].tags[0].tag[0].simple_tag.clear()
                
class Matroska(FileType):
    def load(self, filename):
        self.filename = filename
        fileobj = open(filename, "rb")
        
        self.tags = MatroskaTags(fileobj)
