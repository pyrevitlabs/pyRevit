"""Reloads choosen Revit, CAD and DWG Links.
Can reload links "locally" for workshared models"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens

from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit.revit import query
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


need_tsaxn_dict = [DB.ExternalFileReferenceType.CADLink]


def reload_links(linktype=DB.ExternalFileReferenceType.RevitLink):
    """Reload links of selected type"""
    try:
        extrefs = query.get_links(linktype)
        for ref in extrefs:
            logger.debug(ref)

        if extrefs:
            refcount = len(extrefs)
            if refcount > 1:
                selected_extrefs = \
                    forms.SelectFromList.show(
                        extrefs,
                        title='Select Links to Reload',
                        width=500,
                        button_name='Reload',
                        multiselect=True
                        )
                if not selected_extrefs:
                    script.exit()
            elif refcount == 1:
                selected_extrefs = extrefs

            if revit.doc.IsWorkshared\
                    and linktype == DB.ExternalFileReferenceType.RevitLink:
                reload_locally = forms.alert(
                    'Do you want to reload links locally, without taking '\
                    'ownership and without affecting other users?\n'\
                    'Clicking "No" will reload for all users.',
                    title='Reload locally?',
                    yes=True, no=True)
            else:
                reload_locally = False

            for extref in selected_extrefs:
                print("Reloading...\n\t{0}{1}"
                      .format(str(extref.linktype) + ':', extref.path))
                if linktype in need_tsaxn_dict:
                    with revit.Transaction('Reload Links'):
                        extref.reload()
                elif linktype \
                        and linktype == DB.ExternalFileReferenceType.RevitLink:
                    if reload_locally:
                        try:
                            if not extref.link.LocallyUnloaded:
                                extref.link.UnloadLocally(None)
                            extref.link.RevertLocalUnloadStatus()
                        except Exception as local_reload_err:
                            logger.debug(
                                'Error while locally reloading '
                                'linked model: %s' % local_reload_err)
                    else:
                        extref.reload()
                else:
                    extref.reload()
    except Exception as reload_err:
        logger.debug('Load error: %s' % reload_err)
        forms.alert('Model is not saved yet. Can not acquire location.')


linktypes = {'Revit Links': DB.ExternalFileReferenceType.RevitLink}

if HOST_APP.is_newer_than(2017):
    linktypes['CAD Links'] = DB.ExternalFileReferenceType.CADLink
    linktypes['DWF Markup'] = DB.ExternalFileReferenceType.DWFMarkup

if len(linktypes) > 1:
    selected_option = \
        forms.CommandSwitchWindow.show(linktypes.keys(),
                                       message='Select link type:')
else:
    selected_option = 'Revit Links'

if selected_option:
    reload_links(linktypes[selected_option])
