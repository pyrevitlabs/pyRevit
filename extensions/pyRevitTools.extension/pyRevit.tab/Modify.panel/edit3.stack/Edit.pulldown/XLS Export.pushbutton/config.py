from pyrevit import script, forms

my_config = script.get_config()

exclude_nested = my_config.get_option("exclude_nested", True)
scope = my_config.get_option("scope", "document")


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Exclude Nested", exclude_nested),
]

results = forms.SelectFromList.show(
    opts,
    title="Choose what to set",
    multiselect=True,
    button_name="Save Selection",
    return_all=True,
    width=300,
    height=350,
)

if results:
    selected_items = {item.item: item.state for item in results}
    my_config.set_option("exclude_nested", selected_items.get("Exclude Nested", True))
    script.save_config()

opts = [
    "document",
    "current view",
    "selection",
]
result = forms.ask_for_one_item(opts, default=scope, prompt="Select Export Scope")

if result:
    my_config.set_option("scope", result)
    script.save_config()
