from pyrevit import framework
from pyrevit.framework import Imaging


def bitmap_from_file(bitmap_file):
    bitmap = Imaging.BitmapImage()
    bitmap.BeginInit()
    bitmap.UriSource = framework.Uri(bitmap_file)
    bitmap.CacheOption = Imaging.BitmapCacheOption.OnLoad
    bitmap.EndInit()
    return bitmap
