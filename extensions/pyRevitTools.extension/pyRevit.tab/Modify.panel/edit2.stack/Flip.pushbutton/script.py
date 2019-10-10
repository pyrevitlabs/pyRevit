"""Provides options for flipping (Hand/Face) selected elements."""

from pyrevit import revit, DB, script
from pyrevit import forms


__context__ = 'selection'

def can_flip_wall(el):
    return isinstance(el, DB.Wall)


def can_flip_facing(el):
    return (hasattr(el, 'CanFlipFacing') and el.CanFlipFacing) or hasattr(el, 'rotate')


def can_flip_hand(el):
    return hasattr(el, 'CanFlipHand') and el.CanFlipHand


def can_flip(el):
    return hasattr(el, 'Flip')


def flip():
    with revit.Transaction('Flip Selected'):
        for el in revit.get_selection():
            if hasattr(el, 'Flip'):
                el.Flip()


def flip_facing():
    with revit.Transaction('Flip Facing Selected'):
        for el in revit.get_selection():
            if hasattr(el, 'CanFlipFacing') and el.CanFlipFacing:
                el.flipFacing()
            elif can_flip(el):
                el.Flip()
            elif hasattr(el, 'rotate'):
                el.rotate()


def flip_hand():
    with revit.Transaction('Flip Hand Selected'):
        for el in revit.get_selection():
            if hasattr(el, 'CanFlipHand') and el.CanFlipHand:
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
            if can_flip_wall(el):
                param = el.Parameter[DB.BuiltInParameter.WALL_KEY_REF_PARAM]
                current_value = param.AsInteger()
                with revit.Transaction('Change Wall Location Line'):
                    param.Set(location_line_values['Core Centerline'][0])

                with revit.Transaction('Flip Selected Wall'):
                    el.Flip()
                    param.Set(current_value)


def flip_wall_location_line():
    for el in revit.get_selection():
        if can_flip_wall(el):
            param = el.Parameter[DB.BuiltInParameter.WALL_KEY_REF_PARAM]
            current_value = param.AsInteger()
            for pair in location_line_values.values():
                if pair[0] == current_value:
                    with revit.Transaction('Flip Wall Location Line'):
                        param.Set(pair[1])
                    return


def selection_can(func):
    for el in revit.get_selection():
        if func(el):
            return True
    return False


options_dict = {}

if selection_can(can_flip_wall):
    options_dict.update({'Flip Wall On CenterLine': flip_wall_location,
                         'Flip Wall Location Line': flip_wall_location_line})
if selection_can(can_flip_facing):
    options_dict.update({'Flip Facing': flip_facing})
if selection_can(can_flip_hand):
    options_dict.update({'Flip Hand': flip_hand})
if not options_dict and selection_can(can_flip):
    options_dict.update({'Flip': flip})

if options_dict:
    selected_switch = \
        forms.CommandSwitchWindow.show(options_dict.keys())

    option_func = options_dict.get(selected_switch, None)

    if option_func:
        option_func()
else:
    forms.alert("Selection cannot be flipped")
