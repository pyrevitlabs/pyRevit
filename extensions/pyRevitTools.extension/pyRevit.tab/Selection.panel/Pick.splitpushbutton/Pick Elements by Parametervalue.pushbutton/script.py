"""Activates selection tool that picks only elements with the same parametervalue."""

from pyrevit import forms, revit, EXEC_PARAMS
from pyrevit import UI


class ParamValueSelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, p_v_dict):
        self.p_v_dict = p_v_dict

    # standard API override function
    def AllowElement(self, element):
        matches = []

        for p, v in self.p_v_dict.items():
            try:
                el_param = element.LookupParameter(p.Definition.Name)
                if not el_param:
                    matches.append(False)
                    continue

                el_val = revit.query.get_param_value(el_param)

                matches.append(el_val == v)

            except Exception:
                matches.append(False)

        # ANY match (default mode)
        if any(matches):
            return True

        # ALL match (config mode)
        elif EXEC_PARAMS.config_mode and all(matches):
            return True

        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):
        return False


def main():
    try:
        sel = revit.get_selection()
        elem = (
            sel[0]
            if len(sel) == 1
            else revit.pick_element(message="Pick an element for parameter selection")
        )
        if not elem:
            return

        param_defs = forms.select_parameters(elem, exclude_readonly=False)

        p_v_dict = {}
        for param_def in param_defs:
            p = elem.LookupParameter(param_def.name)
            v = revit.query.get_param_value(p)
            p_v_dict[p] = v

        pvsfilter = ParamValueSelectionFilter(p_v_dict)

        selection_list = revit.pick_rectangle(
            message="Draw a rectangle to pick elements with the same parametervalue",
            pick_filter=pvsfilter,
        )

        filtered_list = []
        for el in selection_list:
            filtered_list.append(el.Id)

        sel.set_to(filtered_list)
        revit.uidoc.RefreshActiveView()

    except Exception:
        pass


if __name__ == "__main__":
    main()
