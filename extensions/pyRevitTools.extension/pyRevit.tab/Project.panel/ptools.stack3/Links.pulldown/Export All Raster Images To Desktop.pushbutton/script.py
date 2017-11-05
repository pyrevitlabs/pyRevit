# -*- coding: utf-8 -*-
import os.path as op
import math
import re

from pyrevit.framework import Diagnostics
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script


__doc__ = 'Exports all original imported images to '\
          'chosen path and adds file size to image type name.'


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_unit = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return ".{}{}.".format(size, size_unit[i])


def cleanup(cleanup_str):
    cleanup_str = cleanup_str.replace(r'ü', 'ue')
    cleanup_str = cleanup_str.replace(r'Ü', 'Ue')
    cleanup_str = cleanup_str.replace(r'ö', 'oe')
    cleanup_str = cleanup_str.replace(r'Ö', 'Oe')
    cleanup_str = cleanup_str.replace(r'ä', 'ae')
    cleanup_str = cleanup_str.replace(r'Ä', 'Ae')
    cleanup_str = cleanup_str.replace(r'ß', 'ss')
    cleanup_str = re.sub(r'[^a-zA-Z0-9_\-]', '_', cleanup_str)
    cleanup_str = re.sub(r'_+', '_', cleanup_str)
    cleanup_str = re.sub(r'(-_|_-)', '-', cleanup_str)
    return cleanup_str


stopwatch = Diagnostics.Stopwatch()
stopwatch.Start()

# dest_dir = op.expandvars('%userprofile%\\desktop')
dest_dir = forms.pick_folder()
img_types = DB.FilteredElementCollector(revit.doc)\
              .OfClass(DB.ImageType)\
              .ToElements()

with revit.Transaction("rename_img_types"):
    for img in img_types:
        # export images
        image = img.GetImage()
        image_name = op.basename(img.Path)
        image_path = op.join(dest_dir, image_name)
        image.Save(op.join(dest_dir, image_name))

        # add info to raster image type name
        img_size = convert_size(op.getsize(image_path))
        prefix = cleanup(image_name.rsplit(".", 1)[0])
        suffix = image_name.rsplit(".", 1)[1]
        new_img_type_name = prefix + img_size + suffix
        img.Name = new_img_type_name

        print('EXPORTING {0}: {1}'.format(img_size[1:-1].rjust(8), image_name))

print("pyRevit Export All Raster Images exported {0} images to {1} in: "
      .format(len(img_types), dest_dir))

stopwatch.Stop()
timespan = stopwatch.Elapsed
print(timespan)
