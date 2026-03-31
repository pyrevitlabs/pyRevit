# -*- coding: UTF-8 -*-
from pyrevit import script, forms
from pyrevit.userconfig import user_config
from ws4links_script import main
from ws4links_translations import TRANSLATIONS_CONFIG


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


my_config = script.get_config()

set_type_ws = my_config.get_option("set_type_ws", False)
set_all = my_config.get_option("set_all", False)
custom_prefix_for_rvt = my_config.get_option("custom_prefix_for_rvt", False)
custom_prefix_for_dwg = my_config.get_option("custom_prefix_for_dwg", False)

translations = TRANSLATIONS_CONFIG.get(
    user_config.user_locale,
    TRANSLATIONS_CONFIG["en_us"]
)  # type: dict[str, str | list]

opts = [
    MyOption(translations["Options.SetTypeWorkset.Text"], set_type_ws),
    MyOption(translations["Options.SetAll.Text"], set_all),
    MyOption(translations["Options.CustomPrefixRvt.Text"], custom_prefix_for_rvt),
    MyOption(translations["Options.CustomPrefixDwg.Text"], custom_prefix_for_dwg),
]

results = forms.SelectFromList.show(
    opts,
    multiselect=True,
    title=translations["Options.WindowTitle"],
    button_name=translations["Options.Select.Button"],
    return_all=True,
    width=330,
    height=300,
)

if results:
    selected_items = {item.item: item.state for item in results}

    my_config.set_option(
        "set_type_ws",
        selected_items.get(translations["Options.SetTypeWorkset.Text"], False)
    )
    my_config.set_option(
        "set_all",
        selected_items.get(translations["Options.SetAll.Text"], False)
    )
    my_config.set_option(
        "custom_prefix_for_rvt",
        selected_items.get(translations["Options.CustomPrefixRvt.Text"], False)
    )
    my_config.set_option(
        "custom_prefix_for_dwg",
        selected_items.get(translations["Options.CustomPrefixDwg.Text"], False)
    )

    if selected_items.get(translations["Options.CustomPrefixRvt.Text"], False):
        custom_prefix_value = my_config.get_option("custom_prefix_rvt_value", "ZL_RVT_")
        custom_prefix_value = forms.ask_for_string(
            default=custom_prefix_value,
            prompt=translations["PrefixRvt.Prompt"]
        )
        my_config.set_option("custom_prefix_rvt_value", custom_prefix_value)

    if selected_items.get(translations["Options.CustomPrefixDwg.Text"], False):
        custom_prefix_value = my_config.get_option("custom_prefix_dwg_value", "ZL_DWG_")
        custom_prefix_value = forms.ask_for_string(
            default=custom_prefix_value,
            prompt=translations["PrefixDwg.Prompt"]
        )
        my_config.set_option("custom_prefix_dwg_value", custom_prefix_value)

    script.save_config()
    main()
