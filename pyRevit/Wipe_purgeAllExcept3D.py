from Autodesk.Revit.DB import *

#cleanup project params
#separate actions into commands and give back more info on objects and errors
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

def reportError():
	print('< ERROR DELETING ELEMENT >')

t = Transaction(doc, 'Cleanup model for 3d export only') 
t.Start()

# print('----------------- PURGING VIEWS / LEGENDS / SCHEDULES ------------------------\n')
# cl = FilteredElementCollector(doc)
# views = list( cl.OfClass(View).WhereElementIsNotElementType().ToElements() )

# for v in views:
	# print('{2}{1}{0}'.format(
		# v.ViewName.ljust(50),
		# str(v.ViewType).ljust(15),
		# str(v.Id).ljust(10),
		# ))
	# if '{3D}' == v.ViewName:
		# continue
	# try:
		# doc.Delete( v.Id )
	# except:
		# reportError()
		# continue

print('------------------------------- PURGING SHEETS -------------------------------\n')
cl = FilteredElementCollector(doc)
sheets = cl.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()

for s in sheets:
	if 'Open_Close' in s.Parameter['Sheet Name'].AsString():
		uidoc.ActiveView = s
		continue
	try:
		print('{2}{0}{1}'.format(
			s.Parameter['Sheet Number'].AsString().rjust(10),
			s.Parameter['Sheet Name'].AsString().ljust(50),
			s.Id,
			))
		doc.Delete( s.Id )
	except:
		reportError()
		continue

# print('------------------------------- PURGING ROOMS ---------------------------------\n')
# cl = FilteredElementCollector(doc)
# rooms = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()

# for r in rooms:
	# try:
		# print('{2}{1}{0}'.format(
			# r.Parameter['Name'].AsString().ljust(30),
			# r.Parameter['Number'].AsString().ljust(20),
			# r.Id
			# ))
		# doc.Delete( r.Id )
	# except:
		# reportError()
		# continue

# print('------------------------------- PURGING AREAS ---------------------------------\n')
# cl = FilteredElementCollector(doc)
# areas = cl.OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()

# for a in areas:
	# try:
		# print('{2}{1}{0}'.format(
			# a.ParametersMap['Name'].AsString().ljust(30),
			# a.ParametersMap['Number'].AsString().ljust(10),
			# a.Id))
		# doc.Delete( a.Id )
	# except:
		# reportError()
		# continue

# print('--------------------- PURGING ROOM SEPARATIONS LINES --------------------------\n')
# cl = FilteredElementCollector(doc)
# rslines = cl.OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType().ToElements()

# for line in rslines:
	# try:
		# # print('ID: {0}'.format( line.Id ))
		# doc.Delete( line.Id )
	# except:
		# reportError()
		# continue

# print('--------------------- PURGING AREA SEPARATIONS LINES --------------------------\n')
# cl = FilteredElementCollector(doc)
# aslines = cl.OfCategory(BuiltInCategory.OST_AreaSchemeLines).WhereElementIsNotElementType().ToElements()

# for line in aslines:
	# try:
		# # print('ID: {0}'.format( line.Id ))
		# doc.Delete( line.Id )
	# except:
		# reportError()
		# continue

# print('---------------------------- PURGING SCOPE BOXES -------------------------------\n')
# cl = FilteredElementCollector(doc)
# scopeboxes = cl.OfCategory(BuiltInCategory.OST_VolumeOfInterest).WhereElementIsNotElementType().ToElements()

# for s in scopeboxes:
	# try:
		# # print('ID: {0}'.format( s.Id ))
		# doc.Delete( s.Id )
	# except:
		# reportError()
		# continue

# print('---------------------------- PURGING MATERIALS -------------------------------\n')
# cl = FilteredElementCollector(doc)
# mats = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()

# for m in mats:
	# try:
		# # print('ID: {0}'.format( m.Id ))
		# doc.Delete( m.Id )
	# except:
		# reportError()
		# continue


t.Commit()

# print('----------------- PURGING PROJECT PARAMETERS ------------------------\n')
# pm = doc.ParameterBindings
# it = pm.ForwardIterator()
# it.Reset()
# deflist = []
# while( it.MoveNext() ):
	# p = it.Key
	# b = pm[ p ]
	# if isinstance(b, InstanceBinding):
		# bind = 'Instance'
	# elif isinstance(b, TypeBinding):
		# bind = 'Type'
	# else:
		# bind = 'Uknown'
		
	# print('PARAM: {0:<10} UNIT: {1:<10} TYPE: {2:<10} GROUP: {3:<20} BINDING: {4}\nAPPLIED TO: {5}\n'.format(
			# p.Name,
			# str(p.UnitType),
			# str(p.ParameterType),
			# str(p.ParameterGroup),
			# bind,
			# [c.Name for c in b.Categories]
			# ) )
	# deflist.append(p)
# for p in deflist:
	# pm.Remove( p )