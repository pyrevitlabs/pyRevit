"""Utility functions to support forms module."""

from pyrevit import framework
from pyrevit.framework import wpf, Controls, Imaging, Uri, UriKind


def bitmap_from_file(bitmap_file):
    """Create BitmapImage from a bitmap file.

    Args:
        bitmap_file (str): absolute path to bitmap file

    Returns:
        (BitmapImage): bitmap image object
    """
    bitmap = Imaging.BitmapImage()
    bitmap.BeginInit()
    success, uri = Uri.TryCreate(bitmap_file, UriKind.RelativeOrAbsolute)
    if not success or uri is None:
        raise ValueError("Failed to create Uri from file path: {}".format(bitmap_file))
    bitmap.UriSource = uri
    bitmap.CacheOption = Imaging.BitmapCacheOption.OnLoad
    bitmap.CreateOptions = Imaging.BitmapCreateOptions.IgnoreImageCache
    bitmap.EndInit()
    bitmap.Freeze()
    return bitmap


def load_component(xaml_file, comp_type):
    """Load WPF component from xaml file.

    Args:
        xaml_file (str): xaml file path
        comp_type (System.Windows.Controls): WPF control type

    Returns:
        (System.Windows.Controls): loaded WPF control
    """
    return wpf.LoadComponent(comp_type, xaml_file)


def load_ctrl_template(xaml_file):
    """Load System.Windows.Controls.ControlTemplate from xaml file.

    Args:
        xaml_file (str): xaml file path

    Returns:
        (System.Windows.Controls.ControlTemplate): loaded control template
    """
    return load_component(xaml_file, Controls.ControlTemplate())


def load_itemspanel_template(xaml_file):
    """Load System.Windows.Controls.ItemsPanelTemplate from xaml file.

    Args:
        xaml_file (str): xaml file path

    Returns:
        (System.Windows.Controls.ControlTemplate): loaded items-panel template
    """
    return load_component(xaml_file, Controls.ItemsPanelTemplate())
