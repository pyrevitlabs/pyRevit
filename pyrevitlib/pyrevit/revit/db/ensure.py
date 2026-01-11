"""Idempotent operations to ensure a database object exists."""
import os.path as op

from System import Int64

from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.compat import get_elementid_from_value_func
from pyrevit.revit.db import query
from pyrevit.revit.db import create
from pyrevit.revit.db import transaction    #pylint: disable=E0611


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)
get_elementid_from_value = get_elementid_from_value_func()

def ensure_sharedparam(sparam_name, sparam_categories, sparam_group,
                       load_param=True, allow_vary_betwen_groups=False,
                       doc=None):
    doc = doc or DOCS.doc
    if query.model_has_parameter(sparam_name, doc=doc):
        if allow_vary_betwen_groups:
            param = query.get_project_parameter(sparam_name, doc=doc)
            if isinstance(param.param_def, DB.InternalDefinition) \
                    and not param.param_def.VariesAcrossGroups:
                param.param_def.SetAllowVaryBetweenGroups(doc, True)
        return True
    elif load_param:
        create.create_shared_param(
            sparam_name,
            sparam_categories,
            sparam_group,
            doc=doc,
            allow_vary_betwen_groups=allow_vary_betwen_groups
            )
        return True


def ensure_sharedparam_file(spfilepath):
    if spfilepath and not HOST_APP.app.SharedParametersFilename:
        HOST_APP.app.SharedParametersFilename = spfilepath
    elif HOST_APP.app.SharedParametersFilename \
            and not op.normpath(HOST_APP.app.SharedParametersFilename) \
                == op.normpath(spfilepath):
        HOST_APP.app.SharedParametersFilename = spfilepath

    return HOST_APP.app.OpenSharedParameterFile()


def ensure_family(family_name, family_file, doc=None):
    doc = doc or DOCS.doc
    famsym = query.get_family(family_name, doc=doc)
    if not famsym:
        with transaction.Transaction('Load Family', doc=doc):
            mlogger.debug('Family \"%s\" did not exist.', family_name)
            if create.load_family(family_file, doc=doc):
                return query.get_family(family_name, doc=doc)
            else:
                raise PyRevitException('Error loading family from: {}'
                                       .format(family_file))
    return famsym


def ensure_element_ids(mixed_list):
    element_id_list = []

    if not hasattr(mixed_list, '__iter__'):
        mixed_list = [mixed_list]

    for item in mixed_list:
        if isinstance(item, DB.ElementId):
            element_id_list.append(item)
        elif isinstance(item, DB.Element):
            element_id_list.append(item.Id)
        elif hasattr(item, 'Id') and isinstance(item.Id, DB.ElementId):
            element_id_list.append(item.Id)
        elif isinstance(item, (int, Int64)):
            element_id_list.append(get_elementid_from_value(item))

    return element_id_list


def ensure_workset(workset_name, partial=False, doc=None):
    doc = doc or DOCS.doc
    workset = query.model_has_workset(workset_name, partial=partial, doc=doc)
    if workset:
        return workset
    else:
        return create.create_workset(workset_name, doc=doc)


def ensure_text_type(name,
                     font_name=None,
                     font_size=0.01042,
                     tab_size=0.02084,
                     bold=False,
                     italic=False,
                     underline=False,
                     width_factor=1.0,
                     doc=None):
    doc = doc or DOCS.doc
    # check if type exists
    for ttype in query.get_types_by_class(DB.TextNoteType, doc=doc):
        if query.get_name(ttype) == name:
            return ttype
    # otherwise create it
    return create.create_text_type(
        name,
        font_name=font_name,
        font_size=font_size,
        tab_size=tab_size,
        bold=bold,
        italic=italic,
        underline=underline,
        width_factor=width_factor,
        doc=doc)


def revision_has_numbertype(revision):
    doc = revision.Document
    none_numtype = coreutils.get_enum_none(DB.RevisionNumberType)
    if HOST_APP.is_newer_than(2022):
        numbering = doc.GetElement(revision.RevisionNumberingSequenceId)
        if numbering:
            return numbering.NumberType != none_numtype
    else:
        return revision.NumberType != none_numtype
