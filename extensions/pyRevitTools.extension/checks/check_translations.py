# -*- coding: UTF-8 -*-
"""Translation helper for preflight check files using XAML ResourceDictionary.

This module provides translation functions that load strings from
PreflightCheckTemplate ResourceDictionary XAML files.
"""
import os
import xml.etree.ElementTree as ET
from pyrevit.userconfig import user_config


def _find_resource_dictionary_path():
    """Find the path to PreflightCheckTemplate ResourceDictionary files.
    
    Returns:
        (str): Base path to ResourceDictionary files or None if not found
    """
    # Get the current file's directory (checks/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up to extension root, then navigate to Preflight Checks.pushbutton
    extension_root = os.path.dirname(current_dir)
    template_path = os.path.join(
        extension_root,
        "pyRevit.tab",
        "Project.panel",
        "Preflight Checks.pushbutton",
        "PreflightCheckTemplate.xaml"
    )
    
    if os.path.exists(template_path):
        return template_path
    return None


def _load_resource_string(resource_file, key):
    """Load a string from a XAML resource dictionary file.
    
    Args:
        resource_file (str): Path to resource dictionary XAML file
        key (str): Resource key to retrieve
        
    Returns:
        (str): Resource string value or None if not found
    """
    if not resource_file or not os.path.isfile(resource_file):
        return None
        
    try:
        tree = ET.parse(resource_file)
        root = tree.getroot()
        # XAML namespace
        ns = {"xaml": "http://schemas.microsoft.com/winfx/2006/xaml/presentation",
              "x": "http://schemas.microsoft.com/winfx/2006/xaml",
              "system": "clr-namespace:System;assembly=mscorlib"}
        # Find the string resource
        string_elem = root.find(".//system:String[@x:Key='{}']".format(key), ns)
        if string_elem is not None:
            return string_elem.text
    except Exception as e:
        print("Error loading resource string: {}".format(e))
        pass
    return None


def get_check_translation(key):
    """Get translated string from PreflightCheckTemplate ResourceDictionary.
    
    Args:
        key (str): Resource key to retrieve
        
    Returns:
        (str): Translated string in current locale, or key if not found
    """
    template_path = _find_resource_dictionary_path()
    if not template_path:
        return key
    
    # Try localized version first
    template_resfile = template_path.replace(
        ".xaml", ".ResourceDictionary.{}.xaml".format(user_config.user_locale)
    )
    if os.path.isfile(template_resfile):
        result = _load_resource_string(template_resfile, key)
        if result:
            return result
    
    # Fallback to English
    template_resfile_en = template_path.replace(
        ".xaml", ".ResourceDictionary.en_us.xaml"
    )
    if os.path.isfile(template_resfile_en):
        result = _load_resource_string(template_resfile_en, key)
        if result:
            return result
    
    # Final fallback to key name
    return key


class DocstringMeta(type):
    """Metaclass to make __doc__ and name dynamic based on translation key."""
    def __init__(cls, name, bases, dct):
        super(DocstringMeta, cls).__init__(name, bases, dct)
        # If class has _docstring_key, set __doc__ to translated value
        if '_docstring_key' in dct:
            translation_key = dct['_docstring_key']
            translated = get_check_translation(translation_key)
            # Only set if translation succeeded (not just returning the key)
            if translated != translation_key:
                cls.__doc__ = translated
            # Otherwise keep the original docstring from dct if it exists
        

        name_key = None
        
        if '_name_key' in dct:
            name_key = dct['_name_key']
        elif 'name' in dct and isinstance(dct['name'], property) and '_docstring_key' in dct:
            doc_key = dct['_docstring_key']
            if doc_key.startswith('CheckDescription_'):
                name_key = doc_key.replace('CheckDescription_', 'CheckName_', 1)
        
        if name_key:
            translated_name = get_check_translation(name_key)
            if translated_name != name_key:
                cls.name = translated_name
