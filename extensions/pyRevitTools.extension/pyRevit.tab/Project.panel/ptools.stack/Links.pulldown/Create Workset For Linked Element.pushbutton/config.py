# -*- coding: UTF-8 -*-
import io
import json
import os
from pyrevit import script, forms
from pyrevit.userconfig import user_config
from script import main


def get_translations(script_folder, script_type, locale):
    # type: (str, str, str) -> dict[str, str | list]
    """
    Get translation for a specific script type from a JSON file.

    Examples:
    ```python
    get_translations(script.get_script_path(), "script", "en_us")
    ```

    Args:
        script_folder (str): The folder containing the JSON file.
        script_type (str): The type of script for which translations are loaded.
            - "script"
            - "config"
        locale (str): The locale for which translations are loaded ("en_us" etc.).

    Returns:
        dict[str, str | list]: A dictionary containing the translation.
    """
    json_path = os.path.join(script_folder, 'translations.json')
    with io.open(json_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
    script_translations = translations.get(script_type, {})
    return script_translations.get(locale, script_translations.get("en_us", {}))


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


my_config = script.get_config()

set_type_ws = my_config.get_option("set_type_ws", False)
set_all = my_config.get_option("set_all", False)
custom_prefix_for_rvt = my_config.get_option("custom_prefix_for_rvt", False)
custom_prefix_for_dwg = my_config.get_option("custom_prefix_for_dwg", False)

translations_dict = get_translations(
    script.get_script_path(),
    "config",
    user_config.user_locale
)

opts = [
    MyOption(translations_dict["Options.SetTypeWorkset.Text"], set_type_ws),
    MyOption(translations_dict["Options.SetAll.Text"], set_all),
    MyOption(translations_dict["Options.CustomPrefixRvt.Text"], custom_prefix_for_rvt),
    MyOption(translations_dict["Options.CustomPrefixDwg.Text"], custom_prefix_for_dwg),
]

results = forms.SelectFromList.show(
    opts,
    multiselect=True,
    title=translations_dict["Options.WindowTitle"],
    button_name=translations_dict["Options.Select.Button"],
    return_all=True,
    width=330,
    height=300,
)

if results:
    selected_items = {item.item: item.state for item in results}

    my_config.set_option(
        "set_type_ws",
        selected_items.get(translations_dict["Options.SetTypeWorkset.Text"], False)
    )
    my_config.set_option(
        "set_all",
        selected_items.get(translations_dict["Options.SetAll.Text"], False)
    )
    my_config.set_option(
        "custom_prefix_for_rvt",
        selected_items.get(translations_dict["Options.CustomPrefixRvt.Text"], False)
    )
    my_config.set_option(
        "custom_prefix_for_dwg",
        selected_items.get(translations_dict["Options.CustomPrefixDwg.Text"], False)
    )

    if selected_items.get(translations_dict["Options.CustomPrefixRvt.Text"], False):
        custom_prefix_value = my_config.get_option("custom_prefix_rvt_value", "ZL_RVT_")
        custom_prefix_value = forms.ask_for_string(
            default=custom_prefix_value,
            prompt=translations_dict["PrefixRvt.Prompt"]
        )
        my_config.set_option("custom_prefix_rvt_value", custom_prefix_value)

    if selected_items.get(translations_dict["Options.CustomPrefixDwg.Text"], False):
        custom_prefix_value = my_config.get_option("custom_prefix_dwg_value", "ZL_DWG_")
        custom_prefix_value = forms.ask_for_string(
            default=custom_prefix_value,
            prompt=translations_dict["PrefixDwg.Prompt"]
        )
        my_config.set_option("custom_prefix_dwg_value", custom_prefix_value)

    script.save_config()
    main()
