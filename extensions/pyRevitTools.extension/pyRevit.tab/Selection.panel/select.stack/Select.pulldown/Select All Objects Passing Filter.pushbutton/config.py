from pyrevit import script, forms

my_config = script.get_config()

exclude_nested = my_config.get_option("exclude_nested", True)
only_current_view = my_config.get_option("only_current_view", True)
reverse_filter = my_config.get_option("reverse_filter", False)


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Exclude Nested", exclude_nested),
    MyOption("Only Current View", only_current_view),
    MyOption("Reverse Selection", reverse_filter),
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
    my_config.set_option(
        "only_current_view", selected_items.get("Only Current View", True)
    )
    my_config.set_option(
        "reverse_filter", selected_items.get("Reverse Selection", False)
    )

    script.save_config()
