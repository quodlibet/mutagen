# -*- coding: utf-8 -*-

import os
import sys

dir_ = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, dir_)
sys.path.insert(0, os.path.abspath(os.path.join(dir_, "..")))

needs_sphinx = "1.3"

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'ext',
]
intersphinx_mapping = {
    'python': ('https://docs.python.org/2.7', None),
    'python3': ('https://docs.python.org/3.5', None),
}
source_suffix = '.rst'
master_doc = 'index'
project = 'mutagen'
copyright = u'2016, Joe Wreschnig, Michael Urman, Lukáš Lalinský, ' \
            u'Christoph Reiter, Ben Ockmore & others'
html_title = project
exclude_patterns = ['_build']
bug_url_template = "https://github.com/quodlibet/mutagen/issues/%s"
pr_url_template = "https://github.com/quodlibet/mutagen/pull/%s"
bbpr_url_template = "https://bitbucket.org/lazka/mutagen/pull-requests/%s"

autodoc_member_order = "bysource"
default_role = "obj"

html_theme = "sphinx_rtd_theme"
html_favicon = "images/favicon.ico"
html_theme_options = {
    "display_version": False,
}
