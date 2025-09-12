from pyrevit import script, forms

my_config = script.get_config()

set_workset = my_config.get_option("set_workset", True)
set_workset_checkout = my_config.get_option("set_workset_checkout", False)
set_workplane_to_level = my_config.get_option("set_workplane_to_level", False)
set_workplane_visible = my_config.get_option("set_workplane_visible", False)
set_phase = my_config.get_option("set_phase", False)
# set_design_option = my_config.get_option("set_design_option", False)


class MyOption(forms.TemplateListItem):
    @property
    def name(self):
        return str(self.item)


opts = [
    MyOption("Workset", set_workset),
    MyOption("Workset Checkout", set_workset_checkout),
    MyOption("Workplane to Level", set_workplane_to_level),
    MyOption("View Workplane", set_workplane_visible),
    MyOption("Phase", set_phase),
    # MyOption("Design Option", set_design_option),
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

    my_config.set_option("set_workset", selected_items.get("Workset", False))
    my_config.set_option("set_workset_checkout", selected_items.get("Workset Checkout", False))
    my_config.set_option("set_workplane_to_level", selected_items.get("Workplane to Level", False))
    my_config.set_option("set_workplane_visible", selected_items.get("View Workplane", False))
    my_config.set_option("set_phase", selected_items.get("Phase", False))
    # my_config.set_option(
    #     "set_design_option", selected_items.get("Design Option", False)
    # )

    script.save_config()
