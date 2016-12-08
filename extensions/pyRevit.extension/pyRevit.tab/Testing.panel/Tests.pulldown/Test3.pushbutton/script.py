import pyrevit.usagedata as ud
db = ud.get_usagedata_db()

with open(r'H:\res.txt', 'w') as f:
	for item in sorted(db.get_scripts()):
		f.write(item + '\n')
