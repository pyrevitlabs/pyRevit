from pyrevit import script, forms
# -*- coding: utf-8 -*-
my_config = script.get_config()


def get_control_points():
    # grab token
    list_checks = ["Project Name", "Project Number", "Warnings"]
    form = forms.SelectFromList.show(
        list_checks, "Checks", 300, 500, multiselect=True, infopanel=True)
    if form:
        setattr(my_config, "qc", form)
        script.save_config()
    else:
        setattr(my_config, "qc", list_checks)
        script.save_config()


if __name__ == "__main__":
    get_control_points()
