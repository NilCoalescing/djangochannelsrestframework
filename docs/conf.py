# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

__version__ = "1.2.0"

# Setup Django
from django.conf import settings

settings.configure()

import djangochannelsrestframework

# -- Project information -----------------------------------------------------

project = "djangochannelsrestframework"
copyright = "2025, Nil Coalescing Limited"
author = "Nil Coalescing Limited"


# -- General configuration ---------------------------------------------------

default_role = "obj"
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

autodoc_typehints = "description"
add_module_names = False

# The suffix of source filenames.
source_suffix = ".rst"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__


# Output file base name for HTML help builder.
htmlhelp_basename = "djangochannelsrestframework"
