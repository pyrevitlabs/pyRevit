"""ReNumber numbered elements in order of selection."""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import coreutils
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

logger = script.get_logger()
output = script.get_output()


def toggle_room_selection_handles(view, state=True):
    # TODO: check if view has viewTemplate
    # then enable temp override on view template
    # view.EnableTemporaryViewPropertiesMode(viewtemplate_id)
    with revit.Transaction("Toggle Room Handles"):
        rr_cat = revit.query.get_subcategory('Rooms', 'Reference')
        rr_cat.Visible[view] = state
        rr_int = revit.query.get_subcategory('Rooms', 'Interior Fill')
        rr_int.Visible[view] = state


class EasilySelectableRooms():
    def __init__(self, target_view):
        self.view = target_view

    def __enter__(self):
        toggle_room_selection_handles(self.view)
        return self

    def __exit__(self, exception, exception_value, traceback):
        toggle_room_selection_handles(self.view, state=False)


def mark_room_as_renamed(view, room):
    ogs = DB.OverrideGraphicSettings()
    ogs.SetHalftone(True)
    ogs.SetSurfaceTransparency(100)
    revit.active_view.SetElementOverrides(room.Id, ogs)


def unmark_renamed_rooms(view, marked_rooms_ids):
    for marked_room_id in marked_rooms_ids:
        ogs = DB.OverrideGraphicSettings()
        revit.doc.ActiveView.SetElementOverrides(marked_room_id, ogs)


def get_rooms_dict():
    all_rooms = \
        revit.query.get_elements_by_category([DB.BuiltInCategory.OST_Rooms])
    return {x.Number:x.Id for x in all_rooms}


def find_replacement_number(existing_number, rooms_dict):
    replaced_number = coreutils.increment_str(existing_number)
    while replaced_number in rooms_dict:
        replaced_number = coreutils.increment_str(replaced_number)
    return replaced_number


def renumber_room(target_room, new_number, rooms_dict):
    if new_number in rooms_dict:
        room_with_same_number = revit.doc.GetElement(rooms_dict[new_number])
        if room_with_same_number \
                and room_with_same_number.Id != target_room.Id:
            current_number = room_with_same_number.Number
            replaced_number = \
                find_replacement_number(current_number, rooms_dict)
            room_with_same_number.Number = replaced_number
            rooms_dict[replaced_number] = room_with_same_number.Id

    logger.debug('applying %s', new_number)
    target_room.Number = new_number
    rooms_dict[new_number] = target_room.Id
    mark_room_as_renamed(revit.active_view, target_room)


def do_renumbering(category_name):
    with revit.TransactionGroup("Renumber {}".format(category_name)):
        with EasilySelectableRooms(revit.active_view):
            index = STARTING_NUM
            existing_rooms_data = get_rooms_dict()
            renumbered_rooms_ids = []
            for picked_room in revit.get_picked_elements_by_category(category_name, "Select {} in order".format(category_name.lower())):
                if isinstance(picked_room, DB.Architecture.Room):
                    with revit.Transaction("Renumber {}".format(category_name)):
                        renumber_room(picked_room, index, existing_rooms_data)
                        renumbered_rooms_ids.append(picked_room.Id)
                    index = coreutils.increment_str(index)
            with revit.Transaction("Unmark {}".format(category_name)):
                unmark_renamed_rooms(revit.active_view, renumbered_rooms_ids)


# [X] enable room reference lines on view
# [X] collect room_id:room_number data
# [ ] ask for starting number
# [ ] ask if user wants to follow the same numbering as current
# [ ] yes:
# [ ] determine numbering scheme and renumber with new starting number
# [ ] no:
# [X] ask to pick rooms one by one
# [X] see if the number exists
# [X] renumber existing
# [X] renumber room

STARTING_NUM = '150'

selected_category = \
    forms.CommandSwitchWindow.show(
        ["Rooms", "Areas", "Spaces"],
        message='Pick only elements of type:'
    )

if selected_category:
    do_renumbering(selected_category)
