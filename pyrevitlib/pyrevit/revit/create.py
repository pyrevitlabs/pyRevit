from pyrevit import HOST_APP, PyRevitException
from pyrevit import DB
from pyrevit.revit import query


def create_category_set(category_list, doc=None):
    doc = doc or HOST_APP.doc
    cat_set = HOST_APP.app.Create.NewCategorySet()
    for builtin_cat in category_list:
        cat = doc.Settings.Categories.get_Item(builtin_cat)
        cat_set.Insert(cat)
    return cat_set


def create_shared_param(param_id_or_name, category_list, builtin_param_group,
                        type_param=False, doc=None):
    doc = doc or HOST_APP.doc
    msp_list = query.get_sharedparam_definition_file()
    for msp in msp_list:
        if msp == param_id_or_name:
            param_def = msp.param_def

    if not param_def:
        raise PyRevitException('Can not find shared parameter.')

    category_set = create_category_set(category_list, doc=doc)

    if not category_set:
        raise PyRevitException('Can not create category set.')

    if type_param:
        new_binding = \
            HOST_APP.app.Create.NewTypeBinding(category_set)
    else:
        new_binding = \
            HOST_APP.app.Create.NewInstanceBinding(category_set)

    doc.ParameterBindings.Insert(param_def,
                                 new_binding,
                                 builtin_param_group)
    return True


def new_project(template=None, imperial=True):
    if template:
        return HOST_APP.app.NewProjectDocument(template)
    else:
        units = DB.UnitSystem.Imperial if imperial else DB.UnitSystem.Metric
        return HOST_APP.app.NewProjectDocument(units)
