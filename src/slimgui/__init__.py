"""
See https://nurpax.github.io/slimgui/ for documentation.
"""

from importlib.metadata import version

from . import anim as anim
from . import imgui as imgui

__version__ = version(__package__ or "slimgui")
