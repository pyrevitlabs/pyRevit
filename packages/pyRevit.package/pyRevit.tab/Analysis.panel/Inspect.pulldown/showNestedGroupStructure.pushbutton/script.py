"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'List the nested group structure around the selected group or element.'

from Autodesk.Revit.DB import Element, ElementId, Group, GroupType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(uidoc.Selection.GetElementIds())

class GroupNode: 
    def __init__(self, id=None, chldrn=[], par=None): 
        self.groupId = id
        self.children = chldrn
        self.parent = par

    @property
    def name(self):
        return doc.GetElement(self.groupId).Name


def findchildren(gid, selectedid, lvl=0, branch='    ', node='|- ', ending=' <-- SELECTED'):
    grp = doc.GetElement(gid)
    if isinstance(grp, Group):
        grpnode = GroupNode(id=gid)
        end = ending if selectedid == gid else ''
        print branch*lvl + node + grpnode.name + end
        mems = grp.GetMemberIds()
        for memid in mems:
            mem = doc.GetElement(memid)
            if isinstance(mem, Group):
                child = findchildren(memid, selectedid, lvl+1)
                grpnode.children.append(child)
        return grpnode


def printtree(gid):
    pass


if len(selection) > 0:
    elid = selection.pop()
    el = doc.GetElement(elid)
    firstparent = elid

    while isinstance(el, Group) and el.GroupId != ElementId.InvalidElementId:
            firstparent = el.GroupId
            el = doc.GetElement(el.GroupId)

    findchildren(firstparent, elid)
else:
    pass