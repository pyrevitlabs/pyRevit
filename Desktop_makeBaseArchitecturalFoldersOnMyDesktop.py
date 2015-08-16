'''	Creates all base architectural folders for sheets per LRS Standard'''
import os, sys
import os.path as op

basefolder = op.expandvars('%userprofile%\\desktop')

archFolders = [
'A000 - CODE',
'A100 - SITE',
'A200 - PLANS',
'A300 - ROOF',
'A400 - RCP',
'A500 - ELEVATIONS',
'A600 - SECTIONS',
'A700 - DOORS & WINDOWS',
'A800 - INTERIOR',
'A9000 - DET CODE',
'A9100 - DET SITE',
'A9200 - DET PLAN',
'A9300 - DET ROOF',
'A9400 - DET RCP',
'A9500 - DET EXTERIOR',
'A9600 - DET SECTIONS',
'A9700 - DET DOORS & WINDOWS',
'A9800 - DET INTERIOR',
]

for d in archFolders:
	os.mkdir(op.join(basefolder, d))