# -*- coding: utf-8 -*-
"""Provide conversion services between python.locale and host languages."""
# https://www.science.co.il/language/Locale-codes.php
import os
import xml.etree.ElementTree as ET

from pyrevit import HOST_APP
from pyrevit.api import ApplicationServices
from pyrevit.userconfig import user_config


DEFAULT_LANG_DIR = 'LTR'


class AppLocale(object):
    """Type representing a language option."""
    def __init__(self,
                 lang_type,
                 locale_codes,
                 lang_name=None,
                 lang_dir=DEFAULT_LANG_DIR):
        if isinstance(lang_type, ApplicationServices.LanguageType):
            self.lang_type = lang_type
        elif isinstance(lang_type, str):
            self.lang_type = lang_type
        self.lang_name = lang_name
        self.lang_dir = lang_dir
        self.locale_codes = locale_codes
        if self.locale_codes:
            self.locale_code = self.locale_codes[0]

    def __str__(self):
        if self.lang_name:
            return '%s / %s (%s)' % (
                self.lang_name, str(self.lang_type), self.locale_code)
        else:
            return '%s (%s)' % (str(self.lang_type), self.locale_code)

    def __repr__(self):
        return str(self)


DEFAULT_LOCALE = AppLocale(
    lang_type=ApplicationServices.LanguageType.English_USA,
    lang_name="English USA",
    locale_codes=["en_us", "english"])

APP_LOCALES = [
    DEFAULT_LOCALE,
    AppLocale(
        lang_type=ApplicationServices.LanguageType.German,
        lang_name="Deutsch",
        locale_codes=["de_de", "german"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Spanish,
        lang_name="español",
        locale_codes=["es_es", "spanish"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.French,
        lang_name="français",
        locale_codes=["fr_fr", "french"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Italian,
        lang_name="italiano",
        locale_codes=["it_it", "italian"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Dutch,
        lang_name="Nederlands",
        locale_codes=["nl_nl", "nl_be", "dutch"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Chinese_Simplified,
        lang_name="简体中文",
        locale_codes=["chinese_s", "chinese"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Chinese_Traditional,
        lang_name="繁體中文",
        locale_codes=["chinese_t", "chinese"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Japanese,
        lang_name="日本語",
        locale_codes=["ja", "japanese"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Korean,
        lang_name="한국어",
        locale_codes=["ko", "korean"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Russian,
        lang_name="Русский",
        locale_codes=["ru", "russian"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Czech,
        lang_name="Čeština",
        locale_codes=["cs", "czech"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Polish,
        lang_name="Polski",
        locale_codes=["pl", "polish"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Hungarian,
        lang_name="Magyar",
        locale_codes=["hu", "hungarian"],
    ),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Brazilian_Portuguese,
        lang_name="Português do Brasil",
        locale_codes=["pt_br", "portuguese_brazil", "brazilian", "portuguese", "pt_pt"],
    ),
]

# add version specific languages
if HOST_APP.is_newer_than(2018, or_equal=True):
    APP_LOCALES.append(
        AppLocale(
            lang_type=ApplicationServices.LanguageType.English_GB,
            lang_name="English Great Britain",
            locale_codes=["en_gb"])
        )

# add custom languages provided by this module
APP_LOCALES.append(
    AppLocale(
        lang_type="Bulgarian",
        lang_name="Български",
        locale_codes=["bg", "bulgarian"])
    )
APP_LOCALES.append(
    AppLocale(
        lang_type="Farsi",
        locale_codes=["fa", "farsi", "persian"],
        lang_name="فارسی",
        lang_dir='RTL'
    ))
APP_LOCALES.append(
    AppLocale(
        lang_type="Arabic",
        locale_codes=["ar", "arabic"],
        lang_name="العربیه",
        lang_dir='RTL'
    ))
APP_LOCALES.append(
    AppLocale(
        lang_type="Ukrainian",
        locale_codes=["uk", "ukrainian"],
        lang_name="Українська"
    ))


def get_applocale_by_local_code(locale_code):
    """Return application locale by locale code.

    Args:
        locale_code (str): locale code

    Returns:
        (AppLocale): application locale
    """
    for applocale in APP_LOCALES:
        if locale_code in applocale.locale_codes:
            return applocale


def get_applocale_by_lang_type(lang_type):
    """Return application locale by language type.

    Args:
        lang_type (ApplicationServices.LanguageType | str): language type

    Returns:
        (AppLocale): application locale
    """
    for applocale in APP_LOCALES:
        if lang_type == applocale.lang_type:
            return applocale


def get_applocale_by_lang_name(lang_name):
    """Return application locale by language name.

    Args:
        lang_name (str): language name

    Returns:
        (AppLocale): application locale
    """
    for applocale in APP_LOCALES:
        if lang_name in {applocale.lang_name, str(applocale.lang_type)}:
            return applocale


def get_current_applocale():
    """Return the current locale.

    This is the user locale, if set, or the host application locale otherwise.

    Returns:
        (AppLocale): current locale
    """
    if user_config.user_locale:
        return get_applocale_by_local_code(user_config.user_locale)
    return get_applocale_by_lang_type(HOST_APP.language)


def get_host_applocale():
    """Return host application locale.

    Returns:
        (AppLocale): host application locale
    """
    return get_applocale_by_lang_type(HOST_APP.language)


def get_locale_string(string_dict):
    """Returns the correct string from given dict based on host language.

    Args:
        string_dict (dict[str, str]): dict of strings in various locales

    Returns:
        (str): string in correct locale

    Examples:
        ```python
        data = {"en_us":"Hello", "chinese_s":"你好"}
        from pyrevit.coreutils import applocales
        # assuming running Revit is Chinese
        applocales.get_locale_string(data)
        ```
        "你好"
    """
    applocale = get_applocale_by_local_code(user_config.user_locale)
    if applocale:
        local_codes = applocale.locale_codes + DEFAULT_LOCALE.locale_codes
    else:
        local_codes = DEFAULT_LOCALE.locale_codes
    for locale_code in local_codes:
        if locale_code in string_dict:
            return string_dict[locale_code]


def get_locale_string_from_xaml(xaml_base_path, key):
    """Get a localized string from a XAML resource dictionary file.

    Derives the resource dictionary path from ``xaml_base_path`` by replacing
    the ``.xaml`` extension with ``.ResourceDictionary.{locale}.xaml``.
    Tries all locale codes of the current locale, then falls back to the
    default (English) locale. Returns ``key`` unchanged when no match is found.

    Args:
        xaml_base_path (str): Path to the base XAML file, e.g. from
            ``script.get_bundle_file("MyForm.xaml")``.
        key (str): Resource key to look up.

    Returns:
        (str): Localized string, or ``key`` as the final fallback.

    Examples:
        ```python
        from pyrevit import script
        from pyrevit.coreutils import applocales
        xaml = script.get_bundle_file("MyForm.xaml")
        title = applocales.get_locale_string_from_xaml(xaml, "WindowTitle")
        ```
    """

    def _read_key(filepath):
        try:
            root = ET.parse(filepath).getroot()
            x_ns = "http://schemas.microsoft.com/winfx/2006/xaml"
            sys_ns = "clr-namespace:System;assembly=mscorlib"
            for elem in root.iter("{%s}String" % sys_ns):
                if elem.get("{%s}Key" % x_ns) == key:
                    return elem.text
        except Exception:
            pass
        return None

    base = os.path.splitext(xaml_base_path)[0]
    locale = get_current_applocale() or DEFAULT_LOCALE

    for code in locale.locale_codes:
        path = "{}.ResourceDictionary.{}.xaml".format(base, code)
        if os.path.isfile(path):
            result = _read_key(path)
            if result is not None:
                return result
            break  # right locale file found but key missing — fall to English

    if locale is not DEFAULT_LOCALE:
        for code in DEFAULT_LOCALE.locale_codes:
            path = "{}.ResourceDictionary.{}.xaml".format(base, code)
            if os.path.isfile(path):
                result = _read_key(path)
                if result is not None:
                    return result
                break

    return key
