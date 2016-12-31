"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Increases the sheet number of the selected sheets by one.'

__window__.Close()

import os, subprocess
import os.path as op


# Checks to see if notepad++ program is installed and available.
def nplusplusexists():
    pffolder = os.getenv('ProgramFiles(x86)')
    return op.isfile(op.join(pffolder, 'Notepad++\\Notepad++.EXE'))


# def getcurrentjournalfile():
#     appdataFolder = os.getenv('localappdata')
#     journalsFolder = op.join(appdataFolder,
#                             'Autodesk\\Revit\\Autodesk Revit {0}\\Journals'.format(__revit__.Application.VersionNumber))
#     os.chdir(journalsFolder)
#     journalFiles = [x for x in os.listdir(journalsFolder) if op.splitext(x)[1].lower() == '.txt']
#     currentJournal = max(journalFiles, key=op.getctime)
#     return currentJournal

def getcurrentjournalfile():
    return __revit__.Application.RecordingJournalFilename


currentJournal = getcurrentjournalfile()

if nplusplusexists():
    os.system('start notepad++ -lvb -n9999999999 "{0}"'.format(currentJournal))
else:
    os.system('start notepad "{0}"'.format(currentJournal))
