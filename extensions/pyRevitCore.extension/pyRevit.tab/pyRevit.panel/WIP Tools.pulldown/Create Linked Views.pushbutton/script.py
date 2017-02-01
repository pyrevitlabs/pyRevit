"""Create views in current model and set the Revit link visibility graphics to show a view from the linked model."""

import clr
import os.path as op

from scriptutils import logger
from scriptutils.userinput import WPFWindow

from revitutils import doc, all_docs

from Autodesk.Revit.DB import Element, FilteredElementCollector, BuiltInCategory, RevitLinkType, \
                              Transaction, View, ViewType


class CreateLinkedViews(WPFWindow):
    def __init__(self, xaml_file_name):
        self.linked_models = []

        WPFWindow.__init__(self, xaml_file_name)
        self._find_linked_models()
        self.viewtype_cb.SelectedIndex = 0

    def _find_linked_models(self):
        cl = FilteredElementCollector(doc)
        self.linked_models = cl.OfClass(clr.GetClrType(RevitLinkType)).ToElements()
        self.linkedmodels_lb.ItemsSource = self.linked_models
        self.linkedmodels_lb.SelectedIndex = 0

    def _get_linked_model_doc(self):
        linked_model = self.linkedmodels_lb.SelectedItem
        for open_doc in all_docs:
            if open_doc.Title == Element.Name.GetValue(linked_model):
                return open_doc

    def _filter_views(self, view_list, view_type):
        return [v for v in view_list if v.ViewType == view_type]

    def _list_views(self):
        open_doc = self._get_linked_model_doc()
        if open_doc:
            cl_sheets = FilteredElementCollector(open_doc)
            view_cl = cl_sheets.OfClass(clr.GetClrType(View)).WhereElementIsNotElementType().ToElements()

            all_views = [v for v in view_cl if not v.IsTemplate]
            view_type = str(self.viewtype_cb.SelectedItem)
            filtered_views = []

            if 'Floor Plans' in view_type:
                filtered_views = self._filter_views(all_views, ViewType.FloorPlan)
            elif 'Reflected Ceiling Plans' in view_type:
                filtered_views = self._filter_views(all_views, ViewType.CeilingPlan)
            elif 'Sections' in view_type:
                filtered_views = self._filter_views(all_views, ViewType.Section)
            elif 'Elevations' in view_type:
                filtered_views = self._filter_views(all_views, ViewType.Elevation)

            self.linkedsheets_lb.ItemsSource = filtered_views

    def linked_model_selected(self, sender, args):
        self._list_views()

    def view_type_changed(self, sender, args):
        self._list_views()

    def selection_changed(self, sender, args):
        self._list_views()

    def create_views(self, sender, args):
        self.Close()


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    CreateLinkedViews('CreateLinkedViews.xaml').ShowDialog()
