from collections import defaultdict

from pyrevit import revit, DB
from pyrevit import script


__title__ = 'Find Legends with Revision Clouds'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

__doc__ = 'Lists all legends with revision clouds on them. '\
          'Legends with revision clouds will not trigger the sheet '\
          'index of the sheet they are placed on and '\
          'that is why this tool is useful.'


output = script.get_output()


clouded_views = defaultdict(list)
rev_clouds = DB.FilteredElementCollector(revit.doc)\
               .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
               .WhereElementIsNotElementType()\
               .ToElements()

notification = """
Note that legends with revision clouds will not trigger
the sheet index of the sheet they are placed on!"""


for rev_cloud in rev_clouds:
    rev_view_id = rev_cloud.OwnerViewId
    rev_view = revit.doc.GetElement(rev_view_id)
    if rev_view.ViewType.ToString() == "Legend":
        clouded_views[rev_view_id].append(rev_cloud)


output.print_md("####LEGENDS WITH REVISION CLOUDS:")
output.print_md('By: [{}]({})'.format(__author__, __contact__))

for view_id in clouded_views:
    view = revit.doc.GetElement(view_id)
    output.print_md("{1} **Legend: {0}**".format(view.Name,
                                                 output.linkify(view_id)))

    for rev_cloud in clouded_views[view_id]:
        rev_cloud_id = rev_cloud.Id
        rev_date = revit.doc.GetElement(rev_cloud.RevisionId).RevisionDate
        rev_creator = \
            DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                          rev_cloud.Id).Creator
        commet_param = \
            rev_cloud.Parameter[DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS]
        if commet_param.HasValue:
            rev_comments = commet_param.AsString()
        else:
            rev_comments = ""

        print('{0} Revision (On {1} By {2}. Comments: {3}'
              .format(output.linkify(rev_cloud_id),
                      rev_date,
                      rev_creator,
                      rev_comments))

    output.print_md('----')

print(notification)
