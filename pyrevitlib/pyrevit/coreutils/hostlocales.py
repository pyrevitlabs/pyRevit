# -*- coding: utf-8 -*-
"""Provide conversion services between python.locale and host languages"""
from pyrevit import HOST_APP
from pyrevit.api import ApplicationServices


HOST_LOCALES = {
    ApplicationServices.LanguageType.English_USA: ["english", "en_us"],
    ApplicationServices.LanguageType.German: ["german", "de_de"],
    ApplicationServices.LanguageType.Spanish: ["spanish", "es_es"],
    ApplicationServices.LanguageType.French: ["french", "fr_fr"],
    ApplicationServices.LanguageType.Italian: ["italian", "it_it"],
    ApplicationServices.LanguageType.Dutch: ["dutch", "nl_be", "nl_nl"],
    ApplicationServices.LanguageType.Chinese_Simplified:
        ["chinese", "chinese_s"],
    ApplicationServices.LanguageType.Chinese_Traditional:
        ["chinese", "chinese_t"],
    ApplicationServices.LanguageType.Japanese: ["japanese", "ja"],
    ApplicationServices.LanguageType.Korean: ["korean", "ko"],
    ApplicationServices.LanguageType.Russian: ["russian", "ru"],
    ApplicationServices.LanguageType.Czech: ["czech", "cs"],
    ApplicationServices.LanguageType.Polish: ["polish", "pl"],
    ApplicationServices.LanguageType.Hungarian: ["hungarian", "hu"],
    ApplicationServices.LanguageType.Brazilian_Portuguese:
        ["portuguese_brazil", "brazilian", "portuguese", "pt_br", "pt_pt"],
}

# add extra langauges
if HOST_APP.is_newer_than(2018, or_equal=True):
    HOST_LOCALES[ApplicationServices.LanguageType.English_GB] = ["en_gb"]


def get_locale_string(string_dict):
    """Returns the correct string from given dict based on host language

    Args:
        string_dict (dict[str:str]): dict of strings in various locales

    Returns:
        str: string in correct locale

    Example:
        >>> data = {"en_us":"Hello", "chinese_s":"你好"}
        >>> from pyrevit.coreutils import hostlocales
        >>> # assuming running Revit is Chinese
        >>> hostlocales.get_locale_string(data)
        ... "你好"
    """
    locale_codes = HOST_LOCALES[HOST_APP.language]
    for locale_code in locale_codes:
        if locale_code in string_dict:
            return string_dict[locale_code]
