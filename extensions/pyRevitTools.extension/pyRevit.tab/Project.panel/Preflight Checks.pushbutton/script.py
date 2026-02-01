"""Run perflight checks on current model"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
import xml.etree.ElementTree as ET
from pyrevit import preflight
from pyrevit import forms
from pyrevit import script
from pyrevit import revit
from pyrevit.userconfig import user_config
from pyrevit.coreutils import applocales

logger = script.get_logger()
output = script.get_output()


def load_resource_string(resource_file, key):
    """Load a string from a XAML resource dictionary file.
    
    Args:
        resource_file (str): Path to resource dictionary XAML file
        key (str): Resource key to retrieve
        
    Returns:
        (str): Resource string value or None if not found
    """
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
    except:
        pass
    return None


def get_translated_ui_string(key):
    """Get translated UI string from resource dictionaries.
    
    Args:
        key (str): Resource key
        
    Returns:
        (str): Translated string or English fallback
    """
    template_xaml = script.get_bundle_file("PreflightCheckTemplate.xaml")
    template_resfile = template_xaml.replace(
        ".xaml", ".ResourceDictionary.{}.xaml".format(user_config.user_locale)
    )
    template_resfile_en = template_xaml.replace(
        ".xaml", ".ResourceDictionary.en_us.xaml"
    )
    
    # Try localized version first
    if os.path.isfile(template_resfile):
        result = load_resource_string(template_resfile, key)
        if result:
            return result
    
    # Fallback to English
    if os.path.isfile(template_resfile_en):
        result = load_resource_string(template_resfile_en, key)
        if result:
            return result
    
    # Final fallback
    return key


class PreflightSelectFromList(forms.SelectFromList):
    """Custom SelectFromList that merges PreflightCheckTemplate resource dictionaries."""
    
    def _setup(self, **kwargs):
        # Merge PreflightCheckTemplate resource dictionaries
        template_xaml = script.get_bundle_file("PreflightCheckTemplate.xaml")
        template_resfile = template_xaml.replace(
            ".xaml", ".ResourceDictionary.{}.xaml".format(user_config.user_locale)
        )
        template_resfile_en = template_xaml.replace(
            ".xaml", ".ResourceDictionary.en_us.xaml"
        )
        
        if os.path.isfile(template_resfile):
            self.merge_resource_dict(template_resfile)
        elif os.path.isfile(template_resfile_en):
            self.merge_resource_dict(template_resfile_en)
        
        # Call parent _setup
        super(PreflightSelectFromList, self)._setup(**kwargs)


def ask_for_preflight_checks():
    """Ask user for preflight tests and run one by one"""
    # Get translated strings
    title = get_translated_ui_string("SelectPreflightCheckTitle")
    button_name = get_translated_ui_string("RunCheckButton")
    
    template_xaml = script.get_bundle_file("PreflightCheckTemplate.xaml")
    
    # ask user for test case
    selected_check = PreflightSelectFromList.show(
        preflight.get_all_preflight_checks(),
        title=title,
        button_name=button_name,
        multiselect=False,
        info_panel=True,
        checked_only=True,
        height=400,
        width=950,
        item_template=forms.utils.load_ctrl_template(template_xaml),
    )

    if selected_check:
        logger.debug("Running: {}".format(selected_check))
        preflight.run_preflight_check(
            selected_check, doc=revit.doc, output=output
        )


if __name__ == "__main__":
    ask_for_preflight_checks()
