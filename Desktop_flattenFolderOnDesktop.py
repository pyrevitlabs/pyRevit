'''	Gets a subfolder name on user desktop and moves all the files in its subdirectories to the roof directory (flattening).'''
import os, sys, shutil
import os.path as op

sheetcount = 0
filecount = 0

desktop = op.expandvars('%userprofile%\\desktop')
basefolder = op.join(desktop, 'Flatten')

for dirname, dirnames, filenames in os.walk( basefolder ):
	for file in filenames:
		filecount += 1
		try:
			shutil.move( op.join(dirname, file), op.join(basefolder, file))
			sheetcount+=1
		except:
			print("Unexpected error:", sys.exc_info()[0])
print('{0} FILES PROCESSED - {1} FILES RENAMED.'.format( filecount, sheetcount))