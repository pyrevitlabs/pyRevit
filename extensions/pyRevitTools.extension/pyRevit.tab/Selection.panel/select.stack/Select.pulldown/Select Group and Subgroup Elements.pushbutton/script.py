"""Replaces current selection with elements inside the groups
and their subgroups.
"""

from pyrevit import revit, DB

doc = revit.doc
selection = revit.get_selection()


def deepest_element_ids_extractor(group):
    """Extracts element ids from the group and its subgroups."""
    for member_id in group.GetMemberIds():
        member = doc.GetElement(member_id)
        if isinstance(member, DB.Group):
            for sub_member_id in deepest_element_ids_extractor(member):
                yield sub_member_id
        else:
            yield member_id


groups = filter(
    lambda elem: isinstance(elem, DB.Group), selection
)

deepest_element_ids = []
for group in groups:
    for id in deepest_element_ids_extractor(group):
        deepest_element_ids.append(id)

selection.set_to(deepest_element_ids)
