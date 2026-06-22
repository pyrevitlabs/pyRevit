# -*- coding: UTF-8 -*-
"""Run preflight checks on current model"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
from pyrevit import preflight
from pyrevit import forms
from pyrevit import script
from pyrevit import revit
from pyrevit.userconfig import user_config
from pyrevit.coreutils import applocales

logger = script.get_logger()
output = script.get_output()


class PreflightSelectFromList(forms.SelectFromList):
    """Custom SelectFromList that merges PreflightCheckTemplate resource dictionaries."""

    def _setup(self, **kwargs):
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

        super(PreflightSelectFromList, self)._setup(**kwargs)


def ask_for_preflight_checks():
    """Ask user for preflight tests and run one by one"""
    template_xaml = script.get_bundle_file("PreflightCheckTemplate.xaml")
    title = applocales.get_locale_string_from_xaml(
        template_xaml, "SelectPreflightCheckTitle"
    )
    button_name = applocales.get_locale_string_from_xaml(template_xaml, "RunCheckButton")

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
