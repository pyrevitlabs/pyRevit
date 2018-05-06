# coding: utf8
import os

from System.Windows.Controls import DataGridComboBoxColumn
from System.Windows.Data import Binding
from System.ComponentModel import ListSortDirection, SortDescription
from System.Collections.ObjectModel import ObservableCollection

from Autodesk.Revit.ApplicationServices import Application
from Autodesk.Revit.DB import Document, BindingMap, ElementBinding, CategorySet, LabelUtils
from Autodesk.Revit import Exceptions

import rpw
from pyrevit import script
from pyrevit.forms import WPFWindow

from pypevitmep.parameter import SharedParameter, ProjectParameter, BoundAllowedCategory
from pypevitmep.parameter.manageshared import ManageSharedParameter

app = rpw.revit.app  # type: Application
doc = rpw.revit.doc # type: Document
uidoc = rpw.uidoc
logger = script.get_logger()


class ManageProjectParameter(WPFWindow):
    def __init__(self):
        file_dir = os.path.dirname(__file__)
        xaml_source = os.path.join(file_dir, "manageproject.xaml")
        WPFWindow.__init__(self, xaml_source)

        # Set icons
        image_dict = {"instance_img": "icon_instance_32.png",
                      "type_img": "icons8-type-32.png",
                      "ok_img": "icons8-checkmark-32.png",
                      "save_img": "icons8-save-32.png",
                      "delete_img": "icons8-trash-32.png",
                      "copy_img": "icons8-copy-32.png",
                      "paste_img": "icons8-paste-32.png",
                      "check_img": "icons8-checked-checkbox-32.png",
                      "uncheck_img": "icons8-unchecked-checkbox-32.png"}
        for k, v in image_dict.items():
            self.set_image_source(k, os.path.join(file_dir, v))

        self.headerdict = {"name": "Name",
                           "pt_name": "ParameterType",
                           "ut_name": "UnitType",
                           "pg_name": "ParameterGroup",
                           "is_instance": "Instance?"}

        self.binding_headerdict = {"name": "Name",
                                   "category_type": "CategoryType",
                                   "is_bound": "IsBound?"}

        # Read existing project parameters and add it to datagrid
        self.project_parameters_datagrid_content = ObservableCollection[object]()
        for project_parameter in sorted([pp for pp in ProjectParameter.read_from_revit_doc()], key=lambda o:o.name):
            self.project_parameters_datagrid_content.Add(project_parameter)
        self.datagrid.ItemsSource = self.project_parameters_datagrid_content

        # Insert all available category to the grid
        self.category_datagrid_content = ObservableCollection[object]()
        bound_allowed_category_list = sorted(
            [BoundAllowedCategory(cat) for cat in ProjectParameter.bound_allowed_category_generator()],
            key=lambda o:o.name)
        for category in bound_allowed_category_list:
            self.category_datagrid_content.Add(category)
        self.category_datagrid.ItemsSource = [category for category in self.category_datagrid_content]

        self.memory_categories = CategorySet()
        for category in self.category_datagrid_content:  # type: BoundAllowedCategory
            self.memory_categories.Insert(category.category)

    # noinspection PyUnusedLocal
    def auto_generating_column(self, sender, e):
        # Generate only desired columns
        headername = e.Column.Header.ToString()
        if headername in self.headerdict.keys():
            if headername == "pg_name":
                cb = DataGridComboBoxColumn()
                cb.ItemsSource = sorted([pp for pp in ProjectParameter.bip_group_name_generator()])
                cb.SelectedItemBinding = Binding(headername)
                cb.SelectedValuePath = "pg_name"
                e.Column = cb
            else:
                e.Column.IsReadOnly = True
            e.Column.Header = self.headerdict[headername]
        else:
            e.Cancel = True

    # noinspection PyUnusedLocal
    def binding_auto_generating_column(self, sender, e):
        # Generate only desired columns
        headername = e.Column.Header.ToString()
        if headername in self.binding_headerdict.keys():
            e.Column.Header = self.binding_headerdict[headername]
            e.Column.IsReadOnly = True
        else:
            e.Cancel = True

    # noinspection PyUnusedLocal
    def auto_generated_columns(self, sender, e):
        # Sort column in desired way
        for column in sender.Columns:
            headerindex = {"Name": 0,
                           "UnitType": 1,
                           "ParameterType": 2,
                           "ParameterGroup": 3,
                           "Instance?": 4,
                           "CategoryType": 1,
                           "IsBound?": 2}
            column.DisplayIndex = headerindex[column.Header.ToString()]

    @staticmethod
    def sortdatagrid(datagrid, columnindex=0, sortdirection=ListSortDirection.Ascending):
        """Sort a datagrid. Cf. https://stackoverflow.com/questions/16956251/sort-a-wpf-datagrid-programmatically"""
        column = datagrid.Columns(columnindex)
        datagrid.Items.SortDescription.Clear()
        datagrid.Items.SortDescription.Add(SortDescription(column.SortMemberPath, sortdirection))
        for col in datagrid.Columns:
            col.SortDirection = None
        column.SortDirection = sortdirection
        datagrid.Items.Refresh()

    # noinspection PyUnusedLocal
    def ok_click(self, sender, e):
        self.save_click(sender, e)
        self.Close()

    # noinspection PyUnusedLocal
    def save_click(self, sender, e):
        with rpw.db.Transaction("Save project parameters"):
            for projectparam in self.project_parameters_datagrid_content:  # type: ProjectParameter
                bindingmap = doc.ParameterBindings # type: BindingMap
                try:
                    if bindingmap[projectparam.definition]:
                        bindingmap.ReInsert(projectparam.definition, projectparam.binding)
                    else:
                        bindingmap.Insert(projectparam.definition, projectparam.binding)
                except Exceptions.ArgumentException:
                    logger.info("Saving {} failed. At least 1 category must be selected.".format(projectparam))
        for projectparam in self.project_parameters_datagrid_content:  # type:
            bip_group = ProjectParameter.bip_group_by_name(projectparam.pg_name)
            if projectparam.definition.ParameterGroup != bip_group:
                iter = doc.ParameterBindings.ForwardIterator()
                for binding in iter:
                    if iter.Key.Name == projectparam.name:
                        iter.Key.ParameterGroup = bip_group


    # noinspection PyUnusedLocal
    def delete_click(self, sender, e):
        with rpw.db.Transaction("Delete project parameters"):
            for projectparam in list(self.datagrid.SelectedItems):  # type: ProjectParameter
                doc.ParameterBindings.Remove(projectparam.definition)
                self.project_parameters_datagrid_content.Remove(projectparam)

    # noinspection PyUnusedLocal
    def copy_binding_click(self, sender, e):
        self.memory_categories = CategorySet()
        for category in self.category_datagrid_content:  # type: BoundAllowedCategory
            if category.is_bound:
                self.memory_categories.Insert(category.category)

    # noinspection PyUnusedLocal
    def paste_binding_click(self, sender, e):
        for category in self.category_datagrid_content: # type: BoundAllowedCategory
            category.is_bound = False
        for bound_category in self.memory_categories:
            for category in self.category_datagrid_content: # type: BoundAllowedCategory
                if bound_category.Name == category.name :
                    category.is_bound = True
        self.category_datagrid.Items.Refresh()

    # noinspection PyUnusedLocal
    def mouse_down(self, sender, e):
        if sender.SelectedItem is None:
            return
        for category in self.category_datagrid_content: # type: BoundAllowedCategory
            category.is_bound = False
        for bound_category in sender.SelectedItem.binding.Categories:
            for category in self.category_datagrid_content: # type: BoundAllowedCategory
                if bound_category.Name == category.name :
                    category.is_bound = True
        self.category_datagrid.Items.Refresh()

    def bind_shared_parameters(self, instance=True):
        if instance:
            binding = app.Create.NewInstanceBinding() # type: ElementBinding
        else:
            binding = app.Create.NewTypeBinding() # type: ElementBinding
        for category in ProjectParameter.bound_allowed_category_generator():
            binding.Categories.Insert(category)
        for definition in ManageSharedParameter.show_dialog():
            self.project_parameters_datagrid_content.Add(ProjectParameter(definition, binding))

    # noinspection PyUnusedLocal
    def bind_as_instance_click(self, sender, e):
        self.bind_shared_parameters()

    # noinspection PyUnusedLocal
    def bind_as_type_click(self, sender, e):
        self.bind_shared_parameters(instance=False)

    # noinspection PyUnusedLocal
    def check_binding_click(self, sender, e):
        for cat in self.category_datagrid.SelectedItems:  # type: BoundAllowedCategory
            for parameter in self.datagrid.SelectedItems:  # type: ProjectParameter
                parameter.binding.Categories.Insert(cat.category)
            cat.is_bound = True
        self.category_datagrid.Items.Refresh()


    # noinspection PyUnusedLocal
    def uncheck_binding_click(self, sender, e):
        for cat in self.category_datagrid.SelectedItems:  # type: BoundAllowedCategory
            for parameter in self.datagrid.SelectedItems:  # type: ProjectParameter
                parameter.binding.Categories.Erase(cat.category)
            cat.is_bound = False
        self.category_datagrid.Items.Refresh()

    @classmethod
    def show_dialog(cls):
        gui = cls()
        gui.ShowDialog()
        return


if __name__ == '__main__':
    ManageProjectParameter.show_dialog()
