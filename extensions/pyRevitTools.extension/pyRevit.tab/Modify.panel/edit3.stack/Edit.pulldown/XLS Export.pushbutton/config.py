from pyrevit import script, forms

my_config = script.get_config("xlseximport")

exclude_nested = my_config.get_option("exclude_nested", True)
exportunit = my_config.get_option("exportunit", "ValueString")
scope = my_config.get_option("scope", "document")


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Exclude Nested", exclude_nested),
    MyOption("Export as ValueString", exportunit == "ValueString"),
    MyOption("Export as Project Units", exportunit == "Project Unit"),
    MyOption("Export as Double (internal units)", exportunit == "Internal"),
]

only_one_exportunit_selected = False

while not only_one_exportunit_selected:
    results = forms.SelectFromList.show(
        opts,
        title="Choose what to set",
        multiselect=True,
        button_name="Save Selection",
        return_all=True,
        width=300,
        height=350,
    )

    if not results:
        forms.alert("No selection made. Canceling.")
        script.exit()

    selected_items = {item.item: item.state for item in results}

    # Count how many export unit options are selected
    export_unit_options = [
        selected_items.get("Export as ValueString", False),
        selected_items.get("Export as Project Units", False),
        selected_items.get("Export as Double (internal units)", False),
    ]

    if export_unit_options.count(True) != 1:
        forms.alert("Please select exactly one export unit option.")
    else:
        only_one_exportunit_selected = True
        # Save config
        my_config.set_option(
            "exclude_nested", selected_items.get("Exclude Nested", True)
        )
        if selected_items.get("Export as ValueString", False):
            my_config.set_option("exportunit", "ValueString")
        elif selected_items.get("Export as Project Units", False):
            my_config.set_option("exportunit", "Project Unit")
        elif selected_items.get("Export as Double (internal units)", False):
            my_config.set_option("exportunit", "Internal")

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
