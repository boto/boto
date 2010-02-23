# -*- coding: utf-8 -*-

import sys, os

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'boto'
copyright = u'2009, Mitch Garnaat'
version = '1.9'
release = "HEAD" #'1.8d'
exclude_trees = []
pygments_style = 'sphinx'
html_theme = 'boto_theme'
html_theme_path = ["."]
html_title = "boto v%s (r%s)" % (version, release)
html_static_path = ['_static']
htmlhelp_basename = 'botodoc'
latex_documents = [
  ('index', 'boto.tex', u'boto Documentation',
   u'Mitch Garnaat', 'manual'),
]
intersphinx_mapping = {'http://docs.python.org/': None}

try:
    import subprocess, os
    release = os.environ['SVN_REVISION']
    # p = subprocess.Popen(["svn info ../boto | grep Revision | awk '{print $2}'"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # release = p.stdout.read().strip()
    # print p.stderr.read()
except:
    pass
