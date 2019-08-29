# -*- coding: utf-8 -*-
"""Provide conversion services between python.locale and host languages"""
from pyrevit import HOST_APP
from pyrevit.api import ApplicationServices
from pyrevit.userconfig import user_config


class AppLocale(object):
    """Type representing a language option."""
    def __init__(self, lang_type, locale_codes):
        if isinstance(lang_type, ApplicationServices.LanguageType):
            self.lang_type = lang_type
        elif isinstance(lang_type, str):
            self.lang_type = lang_type
        self.locale_codes = locale_codes
        if self.locale_codes:
            self.locale_code = self.locale_codes[0]

    def __str__(self):
        return str(self.lang_type)

    def __repr__(self):
        return str(self)

    def ToString(self):
        return str(self)


DEFAULT_LOCALE = AppLocale(
    lang_type=ApplicationServices.LanguageType.English_USA,
    locale_codes=["en_us", "english"])

APP_LOCALES = [
    DEFAULT_LOCALE,

    AppLocale(
        lang_type=ApplicationServices.LanguageType.German,
        locale_codes=["de_de", "german"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Spanish,
        locale_codes=["es_es", "spanish"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.French,
        locale_codes=["fr_fr", "french"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Italian,
        locale_codes=["it_it", "italian"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Dutch,
        locale_codes=["nl_nl", "nl_be", "dutch"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Chinese_Simplified,
        locale_codes=["chinese_s", "chinese"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Chinese_Traditional,
        locale_codes=["chinese_t", "chinese"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Japanese,
        locale_codes=["ja", "japanese"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Korean,
        locale_codes=["ko", "korean"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Russian,
        locale_codes=["ru", "russian"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Czech,
        locale_codes=["cs", "czech"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Polish,
        locale_codes=["pl", "polish"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Hungarian,
        locale_codes=["hu", "hungarian"]),
    AppLocale(
        lang_type=ApplicationServices.LanguageType.Brazilian_Portuguese,
        locale_codes=["pt_br", "portuguese_brazil", "brazilian",
                      "portuguese", "pt_pt"]),
]

# add version specific languages
if HOST_APP.is_newer_than(2018, or_equal=True):
    APP_LOCALES.append(
        AppLocale(
            lang_type=ApplicationServices.LanguageType.English_GB,
            locale_codes=["en_gb"])
        )

# add custom languages provided by this module
APP_LOCALES.append(
    AppLocale(
        lang_type="Bulgarian",
        locale_codes=["it_it", "italian"])
    )
APP_LOCALES.append(
    AppLocale(
        lang_type="Farsi",
        locale_codes=["it_it", "italian"])
    )


def get_applocale_by_local_code(locale_code):
    for applocale in APP_LOCALES:
        if locale_code in applocale.locale_codes:
            return applocale


def get_applocale_by_lang_type(lang_type):
    for applocale in APP_LOCALES:
        if lang_type == applocale.lang_type:
            return applocale


def get_current_applocale():
    if user_config.user_locale:
        return get_applocale_by_local_code(user_config.user_locale)
    return get_applocale_by_lang_type(HOST_APP.language)


def get_locale_string(string_dict):
    """Returns the correct string from given dict based on host language

    Args:
        string_dict (dict[str:str]): dict of strings in various locales

    Returns:
        str: string in correct locale

    Example:
        >>> data = {"en_us":"Hello", "chinese_s":"你好"}
        >>> from pyrevit.coreutils import applocales
        >>> # assuming running Revit is Chinese
        >>> applocales.get_locale_string(data)
        ... "你好"
    """
    applocale = get_applocale_by_local_code(user_config.user_locale)
    if applocale:
        local_codes = applocale.locale_codes + DEFAULT_LOCALE.locale_codes
    else:
        local_codes = DEFAULT_LOCALE.locale_codes
    for locale_code in local_codes:
        if locale_code in string_dict:
            return string_dict[locale_code]
