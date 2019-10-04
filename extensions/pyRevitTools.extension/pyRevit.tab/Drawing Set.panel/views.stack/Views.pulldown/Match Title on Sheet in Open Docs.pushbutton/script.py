from pyrevit import revit, DB


__doc__ = 'Matches the "Title On Sheet" value of all views in open documents '\
          'to current document so all views with matching names will have '\
          'matching "Title On Sheet" values.'


def collect_views(input_doc):
    return DB.FilteredElementCollector(input_doc) \
           .OfCategory(DB.BuiltInCategory.OST_Views) \
           .WhereElementIsNotElementType() \
           .ToElements()


# current document views
curdoc_views = collect_views(revit.doc)
curdoc_views_dict = {revit.query.get_name(v): v for v in curdoc_views}

for open_doc in revit.docs:
    if open_doc is not revit.doc \
            and not open_doc.IsLinked:
        views = collect_views(open_doc)
        with revit.Transaction('Match Title on Sheets', doc=open_doc):
            for v in views:
                if revit.query.get_name(v) in curdoc_views_dict:
                    tos_param = v.Parameter[
                        DB.BuiltInParameter.VIEW_DESCRIPTION
                        ]
                    matching_view = curdoc_views_dict[revit.query.get_name(v)]
                    orig_tos_param = matching_view.Parameter[
                        DB.BuiltInParameter.VIEW_DESCRIPTION
                        ]

                    if orig_tos_param and tos_param:
                        print('Matching Views: {} / {}'
                              .format(revit.query.get_name(v),
                                      revit.query.get_name(matching_view)))

                        print('{} = {}'.format(tos_param.AsString(),
                                               orig_tos_param.AsString()))

                        tos_param.Set(orig_tos_param.AsString())
