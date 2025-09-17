# -*- coding: utf-8 -*-
import sys
import os.path as op
import re

from pathlib import Path

from pyrevit import forms


def renamepdf(old_name):
    new_name = prefix_stripper.sub("", old_name)
    new_name = capitalizer.sub(lambda m: "-{}".format(m.group(1).upper()), new_name)
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

if not basefolder:
    sys.exit()

prefix_stripper = re.compile(r"^.*?(Sheet|Feuille)\s*-\s*", re.IGNORECASE)
capitalizer = re.compile(r"-(?!.*-)\s*(.*)")  # Capitalized after the last hyphen
normalizer = re.compile("\s*-\s*")  # Normalize all other hyphens surrounded by spaces
sheet_count, rename_count, err_count = 0, 0, 0

# Ask for sub folder treatment and define a search pattern
dir_pattern = (
    "**/"
    if forms.alert("Do you want to include subfolders?", yes=True, no=True)
    else ""
)

pdf_files = list(Path(basefolder).glob("{}*.pdf".format(dir_pattern)))
pdf_count = len(pdf_files)
for pdf_file in pdf_files:
    if not prefix_stripper.search(pdf_file.stem):
        continue
    sheet_count += 1
    try:
        new_pdf = renamepdf(pdf_file.stem)
    except (ValueError, re.error):
        continue
    try:
        pdf_file.rename(pdf_file.with_name("{}.pdf".format(new_pdf)))
        rename_count += 1
    except OSError as e:
        err_count += 1
        print("File NOT RENAMED : {}".format(pdf_file))
        print(
            " -> File already exist : {}".format(
                pdf_file.with_name("{}.pdf".format(new_pdf))
            )
        )
        continue

if err_count != 0:
    print(
        "\n{0} PDF files found\n{1} Files with 'Sheet - ' (or 'Feuille - ')\n{2} Files renamed\n{3} Errors".format(
            pdf_count, sheet_count, rename_count, err_count
        )
    )

forms.alert(
    "{0} PDF Files found\n{1} Files with 'Sheet - ' (or 'Feuille - ')\n{2} Files renamed".format(
        pdf_count, sheet_count, rename_count
    )
)
