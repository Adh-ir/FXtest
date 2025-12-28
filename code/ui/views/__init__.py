# Views module for the FX-Test application
# Import view renderers for easy access

from .finder import render_finder
from .auditor import render_auditor

__all__ = ['render_finder', 'render_auditor']
