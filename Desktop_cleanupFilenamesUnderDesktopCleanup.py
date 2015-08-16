'''	Gets a subfolder name on user desktop and removes the ! in filenames.'''
import os, sys
import os.path as op

global globalVerbose
sheetcount = 0
filecount = 0

if verbose:
	globalVerbose = True

desktop = op.expandvars('%userprofile%\\desktop')
basefolder = op.join(desktop, 'Cleanup')

def cleanupFileName( file ):
	if '!' == file[0]:
		return file[1:]
	else:
		return False

for dirname, dirnames, filenames in os.walk( basefolder ):
	for file in filenames:
		filecount += 1
		newfile = cleanupFileName(file)
		if newfile:
			try:
				os.rename(op.join(dirname, file), op.join(dirname, newfile))
				sheetcount+=1
			except:
				print("Unexpected error:", sys.exc_info()[0])
print('{0} FILES PROCESSED - {1} FILES RENAMED.'.format( filecount, sheetcount))