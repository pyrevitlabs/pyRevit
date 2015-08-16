from Autodesk.Revit.DB import InstanceBinding, TypeBinding

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

pm = doc.ParameterBindings
it = pm.ForwardIterator()
it.Reset()
while( it.MoveNext() ):
	p = it.Key
	b = pm[ p ]
	if isinstance(b, InstanceBinding):
		bind = 'Instance'
	elif isinstance(b, TypeBinding):
		bind = 'Type'
	else:
		bind = 'Uknown'
		
	print('PARAM: {0:<10} UNIT: {1:<10} TYPE: {2:<10} GROUP: {3:<20} BINDING: {4}\nAPPLIED TO: {5}\n'.format(
			p.Name,
			str(p.UnitType),
			str(p.ParameterType),
			str(p.ParameterGroup),
			bind,
			[c.Name for c in b.Categories]
			) )