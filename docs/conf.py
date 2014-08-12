# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, os.path.abspath('../'))
import mutagen


extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'ext']
intersphinx_mapping = {'python': ('http://docs.python.org/2.7', None)}
source_suffix = '.rst'
master_doc = 'index'
project = 'mutagen'
copyright = u'2013, Joe Wreschnig, Michael Urman, Lukáš Lalinský, ' \
            u'Christoph Reiter & others'
version = mutagen.version_string
release = mutagen.version_string
exclude_patterns = ['_build']
bug_url_template = "http://bitbucket.org/lazka/mutagen/issue/%s"
