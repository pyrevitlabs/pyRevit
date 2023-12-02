# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit

my_config = script.get_config()
doc = revit.doc

def close_inactive_views():

    try:
        current_setting = getattr(my_config, "view_handling")
    except:
        current_setting = "nothing"
    options = {
        "nothing": "Don't touch my views",
        "reopen": "Close them, but reopen them right after",
        "close": "Close them, and call it a day"
    }

    selection = forms.ask_for_one_item(
        items=options.values(),
        default=options.get(current_setting),
        title="View Handling",
        prompt="Specify what to do with open views"
    )

    setattr(
        my_config,
        "view_handling",
        next((k for k in options if options[k] == selection), None)
    )


if __name__ == "__main__":
    close_inactive_views()