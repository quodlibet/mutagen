# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('../'))
import mutagen


extensions = ['sphinx.ext.autodoc']
source_suffix = '.rst'
master_doc = 'index'
project = 'mutagen'
copyright = u'2013, Joe Wreschnig, Michael Urman, Lukáš Lalinský, Christoph Reiter & others'
version = mutagen.version_string
release = mutagen.version_string
exclude_patterns = ['_build']
