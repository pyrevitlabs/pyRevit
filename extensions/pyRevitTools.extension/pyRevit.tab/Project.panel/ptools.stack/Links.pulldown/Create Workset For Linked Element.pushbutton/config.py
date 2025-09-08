from pyrevit import script, forms
from script import main
my_config = script.get_config()

set_type_ws = my_config.get_option("set_type_ws", False)
set_all = my_config.get_option("set_all", False)
custom_prefix_for_rvt = my_config.get_option("custom_prefix_for_rvt", False)
custom_prefix_for_dwg = my_config.get_option("custom_prefix_for_dwg", False)


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Set Workset for Type", set_type_ws),
    MyOption("Collect all Links", set_all),
    MyOption("Custom Prefix for RVT", custom_prefix_for_rvt),
    MyOption("Custom Prefix for DWG", custom_prefix_for_dwg),
]

results = forms.SelectFromList.show(
    opts,
    multiselect=True,
    button_name="Save Selection",
    return_all=True,
    width=300,
    height=300,
)

if results:
    selected_items = {item.item: item.state for item in results}

    my_config.set_option("set_type_ws", selected_items.get("Set Workset for Type", False))
    my_config.set_option("set_all", selected_items.get("Collect all Links", False))
    my_config.set_option("custom_prefix_for_rvt", selected_items.get("Custom Prefix for RVT", False))
    my_config.set_option("custom_prefix_for_dwg", selected_items.get("Custom Prefix for DWG", False))
    if selected_items.get("Custom Prefix for RVT", False):
        custom_prefix_value = my_config.get_option("custom_prefix_rvt_value", "ZL_RVT_")
        custom_prefix_value = forms.ask_for_string(default=custom_prefix_value, prompt="Pick a Prefix for RVTs")
        my_config.set_option("custom_prefix_rvt_value", custom_prefix_value)
    if selected_items.get("Custom Prefix for DWG", False):
        custom_prefix_value = my_config.get_option("custom_prefix_dwg_value", "ZL_DWG_")
        custom_prefix_value = forms.ask_for_string(default=custom_prefix_value, prompt="Pick a Prefix for DWGs")
        my_config.set_option("custom_prefix_dwg_value", custom_prefix_value)

    script.save_config()
    main()
