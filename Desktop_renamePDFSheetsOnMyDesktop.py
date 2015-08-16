'''	Rename Revit output PDFs on user desktop to remove the project name from file name.'''
import os, sys
import os.path as op

basefolder = op.expandvars('%userprofile%\\desktop')
sheetcount = 0

def renamePDF( file ):
	import re
	r = re.compile('(?<=Sheet - )(.+)')
	fname = r.findall(file)[0]
	r = re.compile('(.+)\s-\s(.+)')
	fnameList= r.findall(fname)
	return fnameList[0][0] + ' - ' + fnameList[0][1].upper()

# for dirname, dirnames, filenames in os.walk( basefolder ):
filenames = os.listdir( basefolder )
for file in filenames:
	ext = op.splitext(file)[1].upper()
	if ext == '.PDF' and ('Sheet' in file):
		newfile = renamePDF(file)
		try:
			os.rename( op.join( basefolder, file ), op.join( basefolder, newfile ))
			sheetcount+=1
		except:
			print("Unexpected error:", sys.exc_info()[0])

print('{0} FILES RENAMED.'.format(sheetcount))