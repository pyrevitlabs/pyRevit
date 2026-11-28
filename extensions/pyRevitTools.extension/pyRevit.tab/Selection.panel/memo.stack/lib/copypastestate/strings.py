# -*- coding: utf-8 -*-
"""Localized strings of the Copy State and Paste State buttons."""

import os.path as op

from pyrevit.coreutils import applocales

RESOURCES = op.join(op.dirname(__file__), "resources.xaml")


def text(key):
    """Return the localized string for ``key`` from ``resources.ResourceDictionary.<locale>.xaml``."""
    return applocales.get_locale_string_from_xaml(RESOURCES, key)
