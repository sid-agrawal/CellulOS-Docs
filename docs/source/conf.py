# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'CellulOS'
copyright = '2024, Sid Agrawal'
author = 'Sid Agrawal, Linh Pham, Arya Stevinson'

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'myst_parser'
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# for implicit references
myst_heading_anchors = 2

# -- Options for HTML output

html_theme = 'sphinx_book_theme'

html_theme_options = {
    'navigation_depth': 2,
    'home_page_in_toc': True
}

html_logo = 'images/OSmosis_Logo_noBG_border.png'

# -- Options for EPUB output
epub_show_urls = 'footnote'
