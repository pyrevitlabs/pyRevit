# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit

my_config = script.get_config()
doc = revit.doc

def close_inactive_views():

    form = forms.SelectFromList.show(["Yes", "No"], title = "Close all inactive views before synchronisation", height = 200)
    if form=="Yes": 
        setattr(my_config, "close_inactive_views", True)
        script.save_config()
    else:
        setattr(my_config, "close_inactive_views", False)
        script.save_config()

if __name__ == "__main__":
    close_inactive_views()