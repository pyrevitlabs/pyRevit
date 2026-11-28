# -*- coding: utf-8 -*-
"""Localized strings of the Attribute Editor, read from the bundle's XAML resources."""

import glob
import os
import xml.etree.ElementTree as ET

from pyrevit.coreutils import applocales

_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
_RESOURCES = os.path.join(_BUNDLE_DIR, "resources.xaml")
_ENGLISH = os.path.join(_BUNDLE_DIR, "resources.ResourceDictionary.en_us.xaml")
_XAML_NAMESPACE = "http://schemas.microsoft.com/winfx/2006/xaml"
_SYS_NAMESPACE = "clr-namespace:System;assembly=mscorlib"

_cache = {}


def _read_dictionary(path):
    root = ET.parse(path).getroot()
    return dict(
        (element.get("{%s}Key" % _XAML_NAMESPACE), element.text)
        for element in root.iter("{%s}String" % _SYS_NAMESPACE)
    )


def _locale_dictionary_path(code):
    base = os.path.splitext(_RESOURCES)[0]
    return "{}.ResourceDictionary.{}.xaml".format(base, code)


def _strings():
    if "strings" not in _cache:
        strings = _read_dictionary(_ENGLISH)
        locale = applocales.get_current_applocale()
        if locale is not None and locale is not applocales.DEFAULT_LOCALE:
            for code in locale.locale_codes:
                path = _locale_dictionary_path(code)
                if os.path.isfile(path):
                    strings.update(_read_dictionary(path))
                    break
        _cache["strings"] = strings
    return _cache["strings"]


def t(key):
    """Return the string for ``key`` in the user's locale, English as fallback."""
    return _strings().get(key, key)


def page_strings():
    """Return every ``ui_`` string for the page, as a dict keyed by resource key."""
    return dict(
        (key, text) for key, text in _strings().items() if key.startswith("ui_")
    )


def _all_locale_texts(key):
    texts = []
    for path in glob.glob(_locale_dictionary_path("*")):
        text = _read_dictionary(path).get(key)
        if text:
            texts.append(text)
    return texts


def translations(key):
    """Return the text of ``key`` in every shipped locale, lower-cased.

    Used to read answers such as Yes and No in the language of whoever copied
    the table, which can differ from the language pyRevit runs in.
    """
    cache_key = ("translations", key)
    if cache_key not in _cache:
        _cache[cache_key] = frozenset(
            text.strip().lower() for text in _all_locale_texts(key)
        )
    return _cache[cache_key]


def token_set(key):
    """Return the ``;``-separated words of ``key`` in every shipped locale, lower-cased."""
    cache_key = ("tokens", key)
    if cache_key not in _cache:
        found = set()
        for text in _all_locale_texts(key):
            found.update(word.strip().lower() for word in text.split(";"))
        found.discard("")
        _cache[cache_key] = frozenset(found)
    return _cache[cache_key]
