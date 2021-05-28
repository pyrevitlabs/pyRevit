"""Reloads choosen Revit, CAD and DWG Links.
Can reload links "locally" for workshared models"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens

from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


need_tsaxn_dict = [DB.ExternalFileReferenceType.CADLink]


def reload_links(ref_type=DB.ExternalFileReferenceType.RevitLink):
    """Reload links of selected type"""
    try:
        link_type = DB.RevitLinkType
        if ref_type == DB.ExternalFileReferenceType.CADLink:
            link_type = DB.CADLinkType

        links = DB.FilteredElementCollector(revit.doc) \
                .OfClass(link_type)\
                .ToElements()

        for link in links:
            logger.debug(link)

        if links:
            xrefs = [revit.db.ExternalRef(x, None) for x in links]
            linkcount = len(xrefs)
            if linkcount > 1:
                selected_xrefs = \
                    forms.SelectFromList.show(
                        xrefs,
                        title='Select Links to Reload',
                        width=500,
                        button_name='Reload',
                        multiselect=True
                        )
                if not selected_xrefs:
                    script.exit()
            elif linkcount == 1:
                selected_xrefs = xrefs

            if revit.doc.IsWorkshared\
                    and ref_type == DB.ExternalFileReferenceType.RevitLink:
                reload_locally = forms.alert(
                    'Do you want to reload links locally, without taking '\
                    'ownership and without affecting other users?\n'\
                    'Clicking "No" will reload for all users.',
                    title='Reload locally?',
                    yes=True, no=True)
            else:
                reload_locally = False

            for xref in selected_xrefs:
                print("Reloading \"{}\"".format(xref.name))
                if ref_type == DB.ExternalFileReferenceType.RevitLink:
                    if reload_locally:
                        try:
                            if not xref.link.LocallyUnloaded:
                                xref.link.UnloadLocally(None)
                            xref.link.RevertLocalUnloadStatus()
                        except Exception as local_reload_err:
                            logger.debug(
                                'Error while locally reloading '
                                'linked model: %s' % local_reload_err)
                    else:
                        xref.reload()
                elif ref_type == DB.ExternalFileReferenceType.CADLink:
                    with revit.Transaction('Reload CAD Links'):
                        xref.reload()
            print("Reload Completed...")
    except Exception as reload_err:
        logger.error('Load error: %s' % reload_err)


linktypes = {'Revit Links': DB.ExternalFileReferenceType.RevitLink}

if HOST_APP.is_newer_than(2017):
    linktypes['CAD Links'] = DB.ExternalFileReferenceType.CADLink

if len(linktypes) > 1:
    selected_option = \
        forms.CommandSwitchWindow.show(linktypes.keys(),
                                       message='Select link type:')
else:
    selected_option = 'Revit Links'

if selected_option:
    reload_links(linktypes[selected_option])
