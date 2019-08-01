"""Provides options for flipping (Hand/Face) selected elements."""

from pyrevit import revit, DB
from pyrevit import forms


__context__ = 'selection'


def flip_facing():
    with revit.Transaction('Flip Facing Selected'):
        for el in revit.get_selection():
            if hasattr(el, 'flipFacing'):
                el.flipFacing()
            elif hasattr(el, 'Flip'):
                el.Flip()


def flip_hand():
    with revit.Transaction('Flip Hand Selected'):
        for el in revit.get_selection():
            if hasattr(el, 'flipHand'):
                el.flipHand()
            elif hasattr(el, 'Flip'):
                el.Flip()


location_line_values = {'Wall Centerline': (0, 0),
                        'Core Centerline': (1, 1),
                        'Finish Face: Exterior': (2, 3),
                        'Finish Face: Interior': (3, 2),
                        'Core Face: Exterior': (4, 5),
                        'Core Face: Interior': (5, 4)}


def flip_wall_location():
    with revit.TransactionGroup("Flip Wall On CenterLine"):
        for el in revit.get_selection():
            if isinstance(el, DB.Wall):
                param = el.Parameter[DB.BuiltInParameter.WALL_KEY_REF_PARAM]
                current_value = param.AsInteger()
                with revit.Transaction('Change Wall Location Line'):
                    param.Set(location_line_values['Core Centerline'][0])

                with revit.Transaction('Flip Selected Wall'):
                    el.Flip()
                    param.Set(current_value)


def flip_wall_location_line():
    for el in revit.get_selection():
        if isinstance(el, DB.Wall):
            param = el.Parameter[DB.BuiltInParameter.WALL_KEY_REF_PARAM]
            current_value = param.AsInteger()
            for pair in location_line_values.values():
                if pair[0] == current_value:
                    with revit.Transaction('Flip Wall Location Line'):
                        param.Set(pair[1])
                    return



options_dict = {'Flip Facing': flip_facing,
                'Flip Hand': flip_hand,
                'Flip Wall On CenterLine': flip_wall_location,
                'Flip Wall Location Line': flip_wall_location_line}

selected_switch = \
    forms.CommandSwitchWindow.show(options_dict.keys())

option_func = options_dict.get(selected_switch, None)

if option_func:
    option_func()
