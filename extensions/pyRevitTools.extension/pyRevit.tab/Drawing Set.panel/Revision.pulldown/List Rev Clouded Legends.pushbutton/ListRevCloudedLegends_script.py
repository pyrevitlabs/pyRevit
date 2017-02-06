"""
Lists all legends with revision clouds on them.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit

"""

__title__ = 'List Legends with Revision Clouds'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Lists all legends with revision clouds on them. Legends with revision clouds will not trigger '\
          'the sheet index of the sheet they are placed on and that is why this tool is useful.'

import clr
from collections import defaultdict

from scriptutils import print_md, this_script
from revitutils import doc

clr.AddReference("RevitAPI")

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import BuiltInCategory, WorksharingUtils


clouded_views = defaultdict(list)
rev_clouds = Fec(doc).OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType().ToElements()

notification = """
Note that legends with revision clouds will not trigger
the sheet index of the sheet they are placed on!"""


for rev_cloud in rev_clouds:
    rev_view_id = rev_cloud.OwnerViewId
    rev_view = doc.GetElement(rev_view_id)
    if rev_view.ViewType.ToString() == "Legend":
        clouded_views[rev_view_id].append(rev_cloud)


print_md("####LEGENDS WITH REVISION CLOUDS:")
print_md('By: [{}]({})'.format(__author__, __contact__))

for view_id in clouded_views:
    view = doc.GetElement(view_id)
    print_md("{1} **Legend: {0}**".format(view.Name,
                                          this_script.output.linkify(view_id)))

    for rev_cloud in clouded_views[view_id]:
        rev_cloud_id = rev_cloud.Id
        rev_date = doc.GetElement(rev_cloud.RevisionId).RevisionDate
        rev_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, rev_cloud.Id).Creator
        if rev_cloud.LookupParameter("Comments").HasValue:
            rev_comments = rev_cloud.LookupParameter("Comments").AsString()
        else:
            rev_comments = ""
        #print("    " + rev_date + " - "  + rev_creator + " - " + rev_comments)


        print('{0} Revision (On {1} By {2}. Comments: {3}'.format(this_script.output.linkify(rev_cloud_id),
                                                                  rev_date,
                                                                  rev_creator,
                                                                  rev_comments))
    print_md('----')

print(notification)
