# -*- coding: utf-8 -*-
import os.path as op
from pathlib import Path

from pyrevit import forms

def renamepdf(old_name):
    new_name = prefix_stripper.sub("", old_name)
    new_name = capitalizer.sub(lambda m : "-{}".format(m.group(1).upper()), new_name)
    new_name = normalizer.sub("-", new_name)
    if not new_name:
        raise ValueError("Renaming results in an empty string.")
    return new_name

# if user shift-clicks, default to user desktop,
# otherwise ask for a folder containing the PDF files
if __shiftclick__:
    basefolder = op.expandvars(r"%userprofile%\desktop")
else:
    basefolder = forms.pick_folder()
# exist script if no folder selected
if not basefolder:
    forms.alert("No Folder Selected.", exitscript=True)

# Continue Script if basefolder
import re
prefix_stripper = re.compile(r"^.*?Sheet\s*-\s*")   #"Sheet -", with space management
capitalizer = re.compile(r"-(?!.*-)\s*(.*)")        #Capitalized after the last hyphen
normalizer = re.compile("\s*-\s*")                  #Normalize all other hyphens surrounded by spaces
pdf_count, sheet_count, rename_count, err_count = 0, 0, 0, 0

# Ask for sub folder treatment and difine a research patern
dir_pattern = "**/" if forms.alert("Do you want to include subfolders?", yes=True, no=True) else ""

#Search all .pdf file
for pdf_file in Path(basefolder).glob("{}*.pdf".format(dir_pattern)):
    pdf_count += 1
    # do nothing if not a 'Sheet - ' pdf (test with the regex prefixe stripper use for renaminf file)
    if not prefix_stripper.search(pdf_file.stem):
        continue
    sheet_count += 1
    try:
        new_pdf = renamepdf(pdf_file.stem)
    except (ValueError, re.error):
        continue
    try :
        pdf_file.rename(pdf_file.with_name("{}.pdf".format(new_pdf)))
        rename_count += 1
    except Exception as e:
        err_count += 1
        print("File NOT RENAME : {}".format(pdf_file))
        print(" -> File already exist : {}".format(pdf_file.with_name("{}.pdf".format(new_pdf))))
        continue

# let user know how many sheets have been renames
if err_count != 0:
    print("\n{0} PDF files found\n{1} Files with 'SHEET - '\n{2} Files rename\n{3} Erreur".format(pdf_count, sheet_count, rename_count, err_count))

forms.alert("{0} PDF Files found\n{1} Files with 'SHEET - '\n{2} Files rename".format(pdf_count, sheet_count, rename_count))
