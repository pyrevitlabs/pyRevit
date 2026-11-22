# -*- coding: utf-8 -*-
"""Localized strings of the Attribute Editor, read from the bundle's XAML resources."""

import os
import xml.etree.ElementTree as ET

from pyrevit.coreutils import applocales

_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
_RESOURCES = os.path.join(_BUNDLE_DIR, "resources.xaml")
_ENGLISH = os.path.join(_BUNDLE_DIR, "resources.ResourceDictionary.en_us.xaml")
_XAML_NAMESPACE = "http://schemas.microsoft.com/winfx/2006/xaml"
_SYS_NAMESPACE = "clr-namespace:System;assembly=mscorlib"

_cache = {}


def _english_keys():
    root = ET.parse(_ENGLISH).getroot()
    return [
        element.get("{%s}Key" % _XAML_NAMESPACE)
        for element in root.iter("{%s}String" % _SYS_NAMESPACE)
    ]


def t(key):
    """Return the string for ``key`` in the user's locale, English as fallback."""
    if key not in _cache:
        _cache[key] = applocales.get_locale_string_from_xaml(_RESOURCES, key)
    return _cache[key]


def page_strings():
    """Return every ``ui_`` string for the page, as a dict keyed by resource key."""
    return dict((key, t(key)) for key in _english_keys() if key.startswith("ui_"))
