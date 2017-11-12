# -*- coding: utf-8 -*-
"""List the nested group structure around the selected group or element."""

from pyrevit import revit, DB
from pyrevit import script


__context__ = 'selection'


output = script.get_output()
selection = revit.get_selection()


class GroupNode:
    def __init__(self, group_element, par=None):
        self.group = group_element
        self.subgroups = self.find_subgroups()

    @property
    def name(self):
        return self.group.Name

    @property
    def id(self):
        return self.group.Id

    @property
    def members(self):
        return [revit.doc.GetElement(x) for x in self.group.GetMemberIds()]

    def find_subgroups(self):
        subgrps = []
        for mem in self.members:
            if isinstance(mem, DB.Group):
                subgrps.append(GroupNode(mem))
        return subgrps

    def __len__(self):
        return len(self.subgroups)

    def __iter__(self):
        return self.subgroups

    def __repr__(self):
        return '<{} name:{}>'.format(self.__class__.__name__, self.name)


def print_tree(groupnode, level, trunk='', branch=''):
    """recursive method for printing (nested) group structure"""
    inset = '\t'
    fruit = \
        branch + '■ {name} {id}'\
                 .format(name=groupnode.name, id=output.linkify(groupnode.id))

    if groupnode.id in selection.element_ids:
        print(fruit + '\t<<< selected group element')
    elif any([x in selection.element_ids
              for x in [y.Id for y in groupnode.members
                        if not isinstance(y, DB.Group)]]):
        print(fruit + '\t<<< selected group members')
    else:
        print(fruit)

    count = len(groupnode)
    for idx, sub_grp in enumerate(groupnode):
        last = idx == count - 1
        if last:
            sub_grp_trunk = trunk + inset + ' '
            sub_grp_branch = trunk + inset + '└──'
        else:
            sub_grp_trunk = trunk + inset + '│'
            sub_grp_branch = trunk + inset + '├──'

        print_tree(sub_grp, level + 1, sub_grp_trunk, sub_grp_branch)


# inspect the selection and find first parents
parent_groups = []

if not selection.is_empty:
    for element in selection.elements:
        if hasattr(element, 'GroupId'):
            firstparent = element
            while firstparent.GroupId != DB.ElementId.InvalidElementId:
                firstparent = revit.doc.GetElement(firstparent.GroupId)

            if isinstance(firstparent, DB.Group):
                parent_groups.append(GroupNode(firstparent))


# print group structure for all discovered parent groups
for parent_grp in parent_groups:
    print_tree(parent_grp, 0)
    print('\n\n')
