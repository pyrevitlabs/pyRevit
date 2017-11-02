from pyrevit import revit, DB


__doc__ = 'Flips the selected walls along their core axis and '\
          'changes their location lines to Core Face Exterior.'


selection = revit.get_selection()


locLineValues = {'Wall Centerline': 0,
                 'Core Centerline': 1,
                 'Finish Face: Exterior': 2,
                 'Finish Face: Interior': 3,
                 'Core Face: Exterior': 4,
                 'Core Face: Interior': 5,
                 }


with revit.TransactionGroup("Search for linked elements"):
    for el in selection:
        if isinstance(el, DB.Wall):
            param = el.LookupParameter('Location Line')
            with revit.Transaction('Change Wall Location Line'):
                param.Set(locLineValues['Core Centerline'])

            with revit.Transaction('Flip Selected Wall'):
                el.Flip()
                param.Set(locLineValues['Core Face: Exterior'])
