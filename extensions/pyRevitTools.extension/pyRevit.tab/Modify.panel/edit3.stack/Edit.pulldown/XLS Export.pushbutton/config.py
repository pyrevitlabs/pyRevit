from pyrevit import script, forms

my_config = script.get_config("xlseximport")

exportunit = my_config.get_option("exportunit", "ValueString")
scope = my_config.get_option("scope", "document")

opts = [
    "ValueString",
    "Project Unit",
    "Internal",
]
result_format = forms.ask_for_one_item(opts, default=scope, prompt="Select Export Format")

if result_format:
    my_config.set_option("exportunit", result_format)
    script.save_config()


opts = [
    "document",
    "current view",
    "selection",
    "schedule"
]
result_scope = forms.ask_for_one_item(opts, default=scope, prompt="Select Export Scope")

if result_scope:
    my_config.set_option("scope", result_scope)
    script.save_config()
