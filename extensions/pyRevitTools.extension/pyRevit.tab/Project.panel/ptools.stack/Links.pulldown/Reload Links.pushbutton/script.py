"""Reloads choosen Revit, CAD and DWG Links.
Can reload links "locally" for workshared models"""

from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit.revit import query
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


need_tsaxn_dict = [DB.ExternalFileReferenceType.CADLink]


def reload_links(linktype=DB.ExternalFileReferenceType.RevitLink):
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
                    'Reload links locally, without taking '\
                    'ownership and with no effect on the other users?\n\n'\
                    '(In the other case your colleagues get the '\
                    'links reloaded after sync)',
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
                else:
                    if reload_locally:
                        if not extref.link.LocallyUnloaded:
                            extref.link.UnloadLocally(None)
                        extref.link.RevertLocalUnloadStatus()
                    else:
                        extref.reload()  
    except Exception as load_err:
        logger.debug('Load error: %s' % load_err)
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
