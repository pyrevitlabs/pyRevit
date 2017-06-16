import os, sys
import os.path as op
from Autodesk.Revit.UI import TaskDialog


__context__ = 'zerodoc'
__doc__ = 'Renames PDF sheets printed from Revit and removes the Central ' \
          'model name from the PDF names. The PDF files must be on desktop.'


basefolder = op.expandvars('%userprofile%\\desktop')
sheetcount = 0


def alert(msg):
    TaskDialog.Show('pyrevit', msg)


def renamePDF(pdffile):
    import re
    r = re.compile('(?<=Sheet - )(.+)')
    fname = r.findall(pdffile)[0]
    r = re.compile('(.+)\s-\s(.+)')
    fnameList = r.findall(fname)
    return fnameList[0][0] + ' - ' + fnameList[0][1].upper()


# for dirname, dirnames, filenames in os.walk( basefolder ):
filenames = os.listdir(basefolder)
for pdffile in filenames:
    ext = op.splitext(pdffile)[1].upper()
    if ext == '.PDF' and ('Sheet' in pdffile):
        newfile = renamePDF(pdffile)
        try:
            os.rename(op.join(basefolder, pdffile), op.join(basefolder, newfile))
            sheetcount += 1
        except Exception as e:
            print("Unexpected error:", sys.exc_info()[0])

alert('{0} FILES RENAMED.'.format(sheetcount))
