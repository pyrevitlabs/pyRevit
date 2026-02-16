from pyrevit import script, forms

my_config = script.get_config()
scope = my_config.get_option("scope", "Visibility")

opts = [
    "Visibility",
    "Active State",
    "Temporary Section Box",
]
result = forms.ask_for_one_item(
    opts,
    default=scope,
    prompt="Select Scope",
    title="Toggle Section Box"
)


if result:
    my_config.set_option("scope", result)
    script.save_config()
