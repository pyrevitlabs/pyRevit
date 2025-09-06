from pyrevit import script, forms

my_config = script.get_config()

sb_visbility = my_config.get_option("sb_visbility", True)
sb_active = my_config.get_option("sb_active", False)


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Section Box Visibility", sb_visbility),
    MyOption("Section Box Active", sb_active),
]

results = forms.SelectFromList.show(
    opts,
    title="Choose what to set",
    multiselect=True,
    button_name="Save Selection",
    return_all=True,
    width=300,
    height=300,
)

if results:
    selected_items = {item.item: item.state for item in results}
    sb_visbility = selected_items.get("Section Box Visibility", True)
    sb_active = selected_items.get("Section Box Active", False)
    if sb_visbility and sb_active:
        forms.alert("Can't set both to enabled", exitscript=True)
    my_config.set_option("sb_visbility", sb_visbility)
    my_config.set_option("sb_active", sb_active)

    script.save_config()
