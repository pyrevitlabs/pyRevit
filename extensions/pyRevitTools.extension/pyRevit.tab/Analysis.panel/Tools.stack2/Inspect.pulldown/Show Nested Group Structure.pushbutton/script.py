# -*- coding: utf-8 -*-
"""List the nested group structure around the selected group or element."""

from scriptutils import this_script
from revitutils import doc, uidoc, selection
from Autodesk.Revit.DB import Element, ElementId, Group, GroupType

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

    def find_subgroups(self):
        subgrps = []
        for mem_id in self.group.GetMemberIds():
            mem = doc.GetElement(mem_id)
            if isinstance(mem, Group):
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
    fruit = branch + '■ {name} {id}' \
              .format(name=groupnode.name,
                      id=this_script.output.linkify(groupnode.id))
    print(fruit)

    count = len(groupnode)
    for idx, sub_grp in enumerate(groupnode):
        last = idx == count -1
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
            while firstparent.GroupId != ElementId.InvalidElementId:
                firstparent = doc.GetElement(firstparent.GroupId)

            if isinstance(firstparent, Group):
                parent_groups.append(GroupNode(firstparent))


# print group structure for all discovered parent groups
for parent_grp in parent_groups:
    print_tree(parent_grp, 0)
    print('\n\n')
