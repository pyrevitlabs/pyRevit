__doc__ = 'This tool tries to remove all cutom project parameters in the file but sometimes fails.'

from pyrevit import HOST_APP
from pyrevit import DB, revit
from pyrevit.compat import get_elementid_value_func

doc = revit.doc

pm = doc.ParameterBindings
it = pm.ForwardIterator()
it.Reset()

deflist = []
paramidlist = set()
while it.MoveNext():
    p = it.Key
    b = pm[p]

    if isinstance(b, DB.InstanceBinding):
        BIND = 'Instance'
    elif isinstance(b, DB.TypeBinding):
        BIND = 'Type'
    else:
        BIND = 'Unknown'

    name = p.Name
    if HOST_APP.is_exactly('2022'):
        ut = str(p.GetSpecTypeId().TypeId)
        tp = str(p.ParameterType)
        pg = str(p.ParameterGroup)
    elif HOST_APP.is_newer_than('2022'):
        ut = str(p.GetDataType().TypeId)
        tp = str(p.GetDataType().TypeId.split('.')[-3])
        pg = str(p.GetGroupTypeId().TypeId)
    else:
        ut = str(p.UnitType)
        tp = str(p.ParameterType)
        pg = str(p.ParameterGroup)

    print('\n')
    print('-' * 100)
    print('PARAM: {0:<30} UNIT: {1:<10} TYPE: {2:<10} GROUP: {3:<20} BINDING: {4:<10} VISIBLE: {6}\n'
          'APPLIED TO: {5}\n'.format(name, ut, tp, pg, BIND, [cat.Name for cat in b.Categories], p.Visible))
    deflist.append(p)

    for cat in b.Categories:
        try:
            get_elementid_value = get_elementid_value_func()
            elements = DB.FilteredElementCollector(doc).OfCategoryId(
                cat.Id).WhereElementIsNotElementType()
            if BIND == 'Type' and p.Visible:
                elementTypes = DB.FilteredElementCollector(
                    doc).OfCategoryId(cat.Id).WhereElementIsElementType()
                print('Searching through {0} ElementTypes of Category {1}'.format(
                    len(list(elements)), cat.Name))
                for elType in elementTypes:
                    paramidlist.add(get_elementid_value(elType.LookupParameter(
                        p.Name).Id))
            elif p.Visible:
                print('Searching through {0} Elements of Category {1}'.format(
                    len(list(elements)), cat.Name))
                for el in elements:
                    paramidlist.add(get_elementid_value(el.LookupParameter(p.Name).Id))
        except Exception as e:
            print('---ERROR---\n', p.Name, cat.Name, cat.Id, e)
            continue

with revit.Transaction('Remove all project parameters'):
    for pid in paramidlist:
        try:
            doc.Delete(DB.ElementId(pid))
        except Exception as e:
            print(pid, e)
            continue
    for p in deflist:
        pm.Remove(p)
