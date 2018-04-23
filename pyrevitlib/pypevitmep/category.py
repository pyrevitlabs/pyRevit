# coding: utf8
import os

import rpw
from rpw import revit
from pyrevit.forms import WPFWindow
from Autodesk.Revit.DB import BuiltInCategory, Category
from System.Collections.ObjectModel import ObservableCollection


def get_full_name(category):
    if category:
        parent = category.Parent
        if not parent:
            name = category.Name
        else:
            name = "{} - {}".format(parent.Name, category.Name)
        return name


def categories_description():
    for category_id in BuiltInCategory.GetValues(BuiltInCategory):
        try:
            category = Category.GetCategory(revit.doc, category_id)
        except:
            raise
        print(get_full_name(category))

def selection_window():
    gui = Gui(os.path.join(os.path.dirname(__file__),"category/WPFWindow.xaml"))
    gui.ShowDialog()


class Gui(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self.categories = ObservableCollection[object]()
        for category in revit.doc.Settings.Categories:
            if category.AllowsBoundParameters:
                self.categories.Add(category)
        self.datagrid.ItemsSource = self.categories

