import os
import sys
import os.path as op

from pyrevit import UI
from pyrevit import forms


__context__ = 'zero-doc'
__doc__ = 'Renames PDF sheets printed from Revit and removes the Central ' \
          'model name from the PDF names. The tool will ask for a folder ' \
          'containing the file.\n\n' \
          'Shift-Click:\nRename files on Desktop'


# if user shift-clicks, default to user desktop,
# otherwise ask for a folder containing the PDF files
if __shiftclick__:
    basefolder = op.expandvars('%userprofile%\\desktop')
else:
    basefolder = forms.pick_folder()


def renamePDF(pdffile):
    import re
    r = re.compile('(?<=Sheet - )(.+)')
    fname = r.findall(pdffile)[0]
    r = re.compile('(.+)\s-\s(.+)')
    fnameList = r.findall(fname)
    return fnameList[0][0] + ' - ' + fnameList[0][1].upper()


if basefolder:
    sheetcount = 0

    # list files and find the PDF files in the base folder
    filenames = os.listdir(basefolder)
    for pdffile in filenames:
        ext = op.splitext(pdffile)[1].upper()
        if ext == '.PDF' and ('Sheet' in pdffile):
            # if PDF make a new file name and rename the exisitng PDF file
            newfile = renamePDF(pdffile)
            try:
                os.rename(op.join(basefolder, pdffile),
                          op.join(basefolder, newfile))
                sheetcount += 1
            except Exception as e:
                print("Unexpected error:", sys.exc_info()[0])

    # let user know how many sheets have been renames
    forms.alert('{0} FILES RENAMED.'.format(sheetcount))
