from pyrevit import script, forms

my_config = script.get_config()
scope = my_config.get_option("scope", "Visibility")

opts = [
    "Visibility",
    "Active State",
]
result = forms.ask_for_one_item(opts, default=scope, prompt="Select Scope")

if result:
    my_config.set_option("scope", result)
    script.save_config()
