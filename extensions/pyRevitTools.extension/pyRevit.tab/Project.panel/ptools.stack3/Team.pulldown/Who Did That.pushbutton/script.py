"""Report the username of whoever reloaded the keynotes last."""

from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


__title__ = 'Who did that??'
__authors__ = ['{{author}}', 'Frederic Beaupere']


def who_reloaded_keynotes():
    location = revit.doc.PathName
    if revit.doc.IsWorkshared:
        try:
            modelPath = \
                DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
            transData = DB.TransmissionData.ReadTransmissionData(modelPath)
            externalReferences = transData.GetAllExternalFileReferenceIds()
            for refId in externalReferences:
                extRef = transData.GetLastSavedReferenceData(refId)
                path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                    extRef.GetPath()
                    )

                if extRef.ExternalFileReferenceType == \
                        DB.ExternalFileReferenceType.KeynoteTable \
                        and '' != path:
                    ktable = revit.doc.GetElement(extRef.GetReferencingId())
                    editedByParam = \
                        ktable.Parameter[DB.BuiltInParameter.EDITED_BY]
                    if editedByParam and editedByParam.AsString() != '':
                        forms.alert('Keynote table has been reloaded by:\n'
                                    '{0}\nTable Id is: {1}'
                                    .format(editedByParam.AsString(),
                                            ktable.Id))
                    else:
                        forms.alert('No one own the keynote table. '
                                    'You can make changes and reload.\n'
                                    'Table Id is: {0}'.format(ktable.Id))
        except Exception as e:
            forms.alert('Model is not saved yet. '
                        'Can not aquire keynote file location.')
    else:
        forms.alert('Model is not workshared.')


def who_created_selection():
    selection = revit.get_selection()
    if revit.doc.IsWorkshared:
        if selection and len(selection) == 1:
            eh = revit.query.get_history(selection.first)

            forms.alert('Creator: {0}\n'
                        'Current Owner: {1}\n'
                        'Last Changed By: {2}'.format(eh.creator,
                                                      eh.owner,
                                                      eh.last_changed_by))
        else:
            forms.alert('Exactly one element must be selected.')
    else:
        forms.alert('Model is not workshared.')


def who_created_activeview():
    active_view = revit.active_view
    view_id = active_view.Id.ToString()
    view_name = active_view.Name
    view_creator = \
        DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                      active_view.Id).Creator

    forms.alert('{}\n{}\n{}'
                .format("Creator of the current view: " + view_name,
                        "with the id: " + view_id,
                        "is: " + view_creator))


options = {'Who Created Active View?': who_created_activeview,
           'Who Created Selected Element?': who_created_selection,
           'Who Reloaded Keynotes Last?': who_reloaded_keynotes}

selected_option = \
    forms.CommandSwitchWindow.show(options.keys())

if selected_option:
    options[selected_option]()
