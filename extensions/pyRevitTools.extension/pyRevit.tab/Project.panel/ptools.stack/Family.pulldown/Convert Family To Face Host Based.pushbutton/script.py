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


def deleteallinstances(family):
    matchlist = []
    try:
        symbolidset = family.GetFamilySymbolIds()
        for symid in symbolidset:
            for faminstance in DB.FilteredElementCollector(revit.doc)\
                                 .WherePasses(
                                     DB.FamilyInstanceFilter(revit.doc,
                                                             symid))\
                                 .ToElements():
                matchlist.append(faminstance.Id)
    except Exception:
        raise Exception

    for elid in matchlist:
        revit.doc.Delete(elid)


if forms.alert('All instances of the selected families '
               'will be removed for this conversion. '
               'Are you ready to proceed?', cancel=True, yes=True):
    for el in revit.get_selection():
        fam = el.Symbol.Family
        famid = el.Symbol.Family.Id
        print('\nStarting conversion for family: {0}'.format(fam.Name))
        try:
            with revit.Transaction('Convert to Face Host Based'):
                deleteallinstances(fam)
                DB.FamilyUtils.ConvertFamilyToFaceHostBased(revit.doc, famid)

            print('Conversion Successful.')
        except Exception as e:
            print('Conversion failed for family: {0}'.format(fam.Name))
            print('Exception Description:\n{0}'.format(e))
