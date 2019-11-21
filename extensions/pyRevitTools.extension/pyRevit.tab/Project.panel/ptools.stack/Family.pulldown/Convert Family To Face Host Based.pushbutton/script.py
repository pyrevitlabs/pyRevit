#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import framework
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__doc__ = 'This script removes all instances of the selected element '\
          'Family and tries to convert the family into face host based. '\
          'Only families of CommunicationDevices, DataDevices, '\
          'DuctTerminal, ElectricalEquipment, ElectricalFixtures, '\
          'FireAlarmDevices, LightingDevices, LightingFixtures, '\
          'MechanicalEquipment, NurseCallDevices, PlumbingFixtures, '\
          'SecurityDevices, Sprinklers, TelephoneDevices can be converted.'


def delete_all_instances(target_family):
    family_instances = []
    try:
        symbol_ids = target_family.GetFamilySymbolIds()
        for symbol_id in symbol_ids:
            for family_instance in DB.FilteredElementCollector(revit.doc)\
                                 .WherePasses(
                                         DB.FamilyInstanceFilter(
                                             revit.doc,
                                             symbol_id))\
                                 .ToElements():
                family_instances.append(family_instance.Id)
    except Exception:
        raise Exception

    for element_id in family_instances:
        revit.doc.Delete(element_id)


if forms.alert('All instances of the selected families '
               'will be removed for this conversion. '
               'Are you ready to proceed?', cancel=True, yes=True):
    for selected_element in revit.get_selection():
        family = selected_element.Symbol.Family
        if family:
            if not DB.FamilyUtils.FamilyCanConvertToFaceHostBased(revit.doc,
                                                                  family.Id):
                forms.alert("Revit API does not support converting this "
                            "family into a face-hosted family.",
                            exitscript=True)

            print('\nStarting conversion for family: {0}'.format(family.Name))
            try:
                with revit.Transaction('Convert to Face Host Based'):
                    delete_all_instances(family)
                    DB.FamilyUtils.ConvertFamilyToFaceHostBased(revit.doc,
                                                                family.Id)
                print('Conversion Successful.')
            except Exception as e:
                print('Conversion failed for family: {0}'.format(family.Name))
                print('Exception Description:\n{0}'.format(e))
