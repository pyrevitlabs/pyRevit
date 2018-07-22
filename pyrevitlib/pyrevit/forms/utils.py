"""Utility functions to support forms module."""

from pyrevit import framework
from pyrevit.framework import Imaging


def bitmap_from_file(bitmap_file):
    """Create BitmapImage from a bitmap file.

    Args:
        bitmap_file (str): path to bitmap file

    Returns:
        BitmapImage: bitmap image object
    """
    bitmap = Imaging.BitmapImage()
    bitmap.BeginInit()
    bitmap.UriSource = framework.Uri(bitmap_file)
    bitmap.CacheOption = Imaging.BitmapCacheOption.OnLoad
    bitmap.EndInit()
    return bitmap
