# -*- coding: utf-8 -*-
# pylint: disable=import-error
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=wrong-import-position
# pylint: disable=broad-except
# pylint: disable=line-too-long
# pylint: disable=protected-access
# pylint: disable=unused-argument
# pylint: disable=attribute-defined-outside-init
# pyright: reportMissingImports=false
import sys
from re import split
from math import fabs
from random import randint
from os.path import exists, isfile
from traceback import extract_tb
from unicodedata import normalize
from unicodedata import category as unicode_category
from pyrevit.framework import Forms
from pyrevit.framework import Drawing
from pyrevit.framework import System
from pyrevit import HOST_APP, revit, DB, UI
from pyrevit.framework import List
from pyrevit.compat import get_elementid_value_func
from pyrevit.script import get_logger
import clr
clr.AddReference('System.Data')
clr.AddReference('System')
from System.Data import DataTable


# Categories to exclude
CAT_EXCLUDED = (int(DB.BuiltInCategory.OST_RoomSeparationLines), int(DB.BuiltInCategory.OST_Cameras), int(DB.BuiltInCategory.OST_CurtainGrids), int(DB.BuiltInCategory.OST_Elev), int(DB.BuiltInCategory.OST_Grids), int(DB.BuiltInCategory.OST_IOSModelGroups), int(DB.BuiltInCategory.OST_Views), int(DB.BuiltInCategory.OST_SitePropertyLineSegment), int(DB.BuiltInCategory.OST_SectionBox), int(DB.BuiltInCategory.OST_ShaftOpening), int(DB.BuiltInCategory.OST_BeamAnalytical), int(DB.BuiltInCategory.OST_StructuralFramingOpening), int(DB.BuiltInCategory.OST_MEPSpaceSeparationLines), int(DB.BuiltInCategory.OST_DuctSystem), int(DB.BuiltInCategory.OST_Lines), int(DB.BuiltInCategory.OST_PipingSystem), int(DB.BuiltInCategory.OST_Matchline), int(DB.BuiltInCategory.OST_CenterLines), int(DB.BuiltInCategory.OST_CurtainGridsRoof), int(DB.BuiltInCategory.OST_SWallRectOpening), -2000278, -1)

logger = get_logger() # get logger and trigger debug mode using CTRL+click


class SubscribeView(UI.IExternalEventHandler):
    def __init__(self):
        self.registered = 1

    def Execute(self, uiapp):
        try:
            if self.registered == 1:
                self.registered = 0
                uiapp.ViewActivated += self.view_changed
            else:
                self.registered = 1
                uiapp.ViewActivated -= self.view_changed
        except Exception:
            external_event_trace()

    def view_changed(self, sender, e):
        if wndw.IsOpen == 1:
            if self.registered == 0:
                new_doc = e.Document
                if new_doc:
                    new_uiapp = new_doc.Application
                    if wndw:
                        if not new_doc.Equals(doc):
                            wndw.Close()
                # Update categories in dropdown
                new_view = get_active_view(e.Document)
                if new_view != 0:
                    # Unsubcribe
                    wndw.list_box2.SelectedIndexChanged -= wndw.list_selected_index_changed
                    # Update categories for new view
                    wndw.crt_view = new_view
                    categ_inf_used_up = get_used_categories_parameters(CAT_EXCLUDED, wndw.crt_view)
                    wndw.table_data = DataTable("Data")
                    wndw.table_data.Columns.Add("Key", System.String)
                    wndw.table_data.Columns.Add("Value", System.Object)
                    names = [x.name for x in categ_inf_used_up]
                    wndw.table_data.Rows.Add("Select a Category Here!", 0)
                    for key_, value_ in zip(names, categ_inf_used_up):
                        wndw.table_data.Rows.Add(key_, value_)
                    wndw._categories.DataSource = wndw.table_data
                    wndw._categories.DisplayMember = "Key"
                    # Empty range of values
                    wndw._table_data_3 = DataTable("Data")
                    wndw._table_data_3.Columns.Add("Key", System.String)
                    wndw._table_data_3.Columns.Add("Value", System.Object)
                    wndw.list_box2.DataSource = wndw._table_data_3
                    wndw.list_box2.DisplayMember = "Key"

    def GetName(self):
        return "Subscribe View Changed Event"


class ApplyColors(UI.IExternalEventHandler):
    def __init__(self):
        pass

    def Execute(self, uiapp):
        try:
            new_doc = uiapp.ActiveUIDocument.Document
            view = get_active_view(new_doc)
            if not view:
                return
            solid_fill_id = solid_fill_pattern_id()
            with revit.Transaction("Apply colors to elements"):
                sel_cat = wndw._categories.SelectedItem['Value']
                get_elementid_value = get_elementid_value_func()
                if get_elementid_value(sel_cat.cat.Id) in (int(DB.BuiltInCategory.OST_Rooms), int(DB.BuiltInCategory.OST_MEPSpaces), int(DB.BuiltInCategory.OST_Areas)):
                    # In case of rooms, spaces and areas. Check Color scheme is applied and if not
                    if version > 2021:
                        if str(wndw.crt_view.GetColorFillSchemeId(sel_cat.cat.Id)) == "-1":
                            color_schemes = DB.FilteredElementCollector(new_doc).OfClass(DB.BuiltInCategoryFillScheme).ToElements()
                            if len(color_schemes) > 0:
                                for sch in color_schemes:
                                    if sch.CategoryId == sel_cat.cat.Id:
                                        if len(sch.GetEntries()) > 0:
                                            wndw.crt_view.SetColorFillSchemeId(sel_cat.cat.Id, sch.Id)
                                            break
                    else:
                        wndw._txt_block5.Visible = True
                else:
                    wndw._txt_block5.Visible = False

                for indx in range(wndw.list_box2.Items.Count):
                    ogs = DB.OverrideGraphicSettings()
                    color = DB.Color(wndw.list_box2.Items[indx]['Value'].n1, wndw.list_box2.Items[indx]['Value'].n2, wndw.list_box2.Items[indx]['Value'].n3)
                    ogs.SetProjectionLineColor(color)
                    ogs.SetSurfaceForegroundPatternColor(color)
                    ogs.SetCutForegroundPatternColor(color)
                    if solid_fill_id is not None:
                        ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                        ogs.SetCutForegroundPatternId(solid_fill_id)
                    ogs.SetProjectionLinePatternId(DB.ElementId(-1))
                    for idt in wndw.list_box2.Items[indx]['Value'].ele_id:
                        view.SetElementOverrides(idt, ogs)
        except Exception:
            external_event_trace()

    def GetName(self):
        return "Set colors to elements"


class ResetColors(UI.IExternalEventHandler):
    def __init__(self):
        pass

    def Execute(self, uiapp):
        try:
            new_doc = revit.DOCS.doc
            view = get_active_view(new_doc)
            if view == 0:
                return
            ogs = DB.OverrideGraphicSettings()
            collector = DB.FilteredElementCollector(new_doc, view.Id).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElementIds()
            sel_cat = wndw._categories.SelectedItem['Value']
            if sel_cat == 0:
                task_no_cat = UI.TaskDialog("Color Elements by Parameter")
                task_no_cat.MainInstruction = "Please, select a category to reset the colors."
                wndw.TopMost = False
                task_no_cat.Show()
                wndw.TopMost = True
                return
            with revit.Transaction("Reset colors in elements"):
                try:
                    # Get and ResetView Filters
                    filter_name = sel_cat.name + "/"
                    filters = view.GetFilters()
                    for filt_id in filters:
                        filt_ele = new_doc.GetElement(filt_id)
                        if filt_ele.Name.StartsWith(filter_name):
                            view.RemoveFilter(filt_id)
                            try:
                                new_doc.Delete(filt_id)
                            except Exception:
                                external_event_trace()
                except Exception:
                    external_event_trace()
                # Reset visibility
                for i in collector:
                    view.SetElementOverrides(i, ogs)
        except Exception:
            external_event_trace()

    def GetName(self):
        return "Reset colors in elements"


class CreateLegend(UI.IExternalEventHandler):
    def __init__(self):
        pass

    def Execute(self, uiapp):
        try:
            new_doc = uiapp.ActiveUIDocument.Document
            # Get legend view
            collector = DB.FilteredElementCollector(new_doc).OfClass(DB.View).ToElements()
            legends = []
            for vw in collector:
                if vw.ViewType == DB.ViewType.Legend:
                    legends.append(vw)
                    break
            if len(legends) < 0:
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = "In order to create a new legend, you need to have at least one. Please, create a legend view."
                wndw.TopMost = False
                task2.Show()
                wndw.TopMost = True
            else:
                # Duplicate existing legend
                t = DB.Transaction(new_doc, "Create Legend")
                t.Start()
                trans = DB.SubTransaction(new_doc)
                trans.Start()
                new_id_legend = legends[0].Duplicate(DB.ViewDuplicateOption.Duplicate)
                new_legend = new_doc.GetElement(new_id_legend)
                sel_cat = wndw._categories.SelectedItem['Value']
                sel_par = wndw._list_box1.SelectedItem['Value']
                try:
                    new_legend.Name = "Color Splasher - " + sel_cat.name + " - " + sel_par.name
                    renamed = True
                except Exception:
                    external_event_trace()
                    renamed = False
                if not renamed:
                    for i in range(1000):
                        try:
                            new_legend.Name = "Color Splasher - " + sel_cat.name + " - " + sel_par.name + " - " + str(i)
                            break
                        except Exception:
                            external_event_trace()
                trans.Commit()
                old_all_ele = DB.FilteredElementCollector(new_doc, legends[0].Id).ToElements()
                ele_id_type = DB.ElementId(0)
                for ele in old_all_ele:
                    if ele.Id != new_legend.Id and ele.Category is not None:
                        if isinstance(ele, DB.TextNote):
                            ele_id_type = ele.GetTypeId()
                            break
                get_elementid_value = get_elementid_value_func()
                if get_elementid_value(ele_id_type) == 0:
                    # Get any text in model
                    all_text_notes = DB.FilteredElementCollector(new_doc).OfClass(DB.TextNoteType).ToElements()
                    for ele in all_text_notes:
                        ele_id_type = ele.Id
                        break
                list_max_x = []
                list_y = []
                # FilledRegionType
                filled_type = None
                filled_region_types = DB.FilteredElementCollector(new_doc).OfClass(DB.FilledRegionType).ToElements()
                for filled_region_type in filled_region_types:
                    pattern = new_doc.GetElement(filled_region_type.ForegroundPatternId)
                    if pattern is not None and pattern.GetFillPattern().IsSolidFill and filled_region_type.ForegroundPatternColor.IsValid:
                        filled_type = filled_region_type
                        break
                # Create Type if none is fill
                if not filled_type and filled_region_types:
                    for idx in range(100):
                        try:
                            new_type = filled_region_types[0].Duplicate("Fill Region " + str(idx))
                            break
                        except Exception:
                            external_event_trace()
                    # Create pattern
                    for idx in range(100):
                        try:
                            new_pattern = DB.FillPattern("Fill Pattern " + str(idx), DB.FillPatternTarget.Drafting, DB.FillPatternHostOrientation.ToView, float(0), float(0.00001))
                            new_ele_pat = DB.FillPatternElement.Create(new_doc, new_pattern)
                            break
                        except Exception:
                            external_event_trace()
                    # Assign to type
                    new_type.ForegroundPatternId = new_ele_pat.Id
                    filled_type = new_type
                # Create Text
                fin_coord_y = 0
                for index, vw_item in enumerate(wndw.list_box2.Items):
                    punto = DB.XYZ(0, 0, 0)
                    if index != 0:
                        punto = DB.XYZ(0, fin_coord_y, 0)
                    item = vw_item['Value']
                    text_line = sel_cat.name + "/" + sel_par.name + " - " + item.value
                    new_text = DB.TextNote.Create(new_doc, new_legend.Id, punto, text_line, ele_id_type)
                    new_doc.Regenerate()
                    prev_bbox = new_text.get_BoundingBox(new_legend)
                    offset = (prev_bbox.Max.Y - prev_bbox.Min.Y)*0.25
                    fin_coord_y = prev_bbox.Min.Y - offset
                    list_max_x.append(prev_bbox.Max.X)
                    list_y.append(fin_coord_y + offset)
                    height = prev_bbox.Max.Y - prev_bbox.Min.Y
                ini_x = max(list_max_x)
                ogs = DB.OverrideGraphicSettings()
                # Create filled color region
                for indx, y in enumerate(list_y):
                    coord_y = y
                    item = wndw.list_box2.Items[indx]['Value']
                    point0 = DB.XYZ(ini_x, coord_y, 0)
                    point1 = DB.XYZ(ini_x, coord_y + height, 0)
                    point2 = DB.XYZ(ini_x * 1.5, coord_y + height, 0)
                    point3 = DB.XYZ(ini_x * 1.5, coord_y, 0)
                    line01 = DB.Line.CreateBound(point0, point1)
                    line12 = DB.Line.CreateBound(point1, point2)
                    line23 = DB.Line.CreateBound(point2, point3)
                    line30 = DB.Line.CreateBound(point3, point0)
                    list_curve_loops = List[DB.CurveLoop]()
                    curve_loops = DB.CurveLoop()
                    curve_loops.Append(line01)
                    curve_loops.Append(line12)
                    curve_loops.Append(line23)
                    curve_loops.Append(line30)
                    list_curve_loops.Add(curve_loops)
                    reg = DB.FilledRegion.Create(new_doc, filled_type.Id, new_legend.Id, list_curve_loops)
                    # Assign color filled region
                    color = DB.Color(item.n1, item.n2, item.n3)
                    ogs.SetProjectionLineColor(color)
                    ogs.SetSurfaceForegroundPatternColor(color)
                    ogs.SetCutForegroundPatternColor(color)
                    ogs.SetProjectionLinePatternId(DB.ElementId(-1))
                    new_legend.SetElementOverrides(reg.Id, ogs)
                t.Commit()
        except Exception:
            external_event_trace()

    def GetName(self):
        return "Create Legend"


class CreateFilters(UI.IExternalEventHandler):
    def __init__(self):
        pass

    def Execute(self, uiapp):
        try:
            new_doc = uiapp.ActiveUIDocument.Document
            view = get_active_view(new_doc)
            if view != 0:
                dict_filters = {}
                for filt_id in view.GetFilters():
                    filter_ele = new_doc.GetElement(filt_id)
                    dict_filters[filter_ele.Name] = filt_id
                # Get rules apply in document
                dict_rules = {}
                iterator = DB.FilteredElementCollector(new_doc).OfClass(DB.ParameterFilterElement).GetElementIterator()
                while iterator.MoveNext():
                    ele = iterator.Current
                    dict_rules[ele.Name] = ele.Id
                with revit.Transaction("Create View Filters"):
                    sel_cat = wndw._categories.SelectedItem['Value']
                    sel_par = wndw._list_box1.SelectedItem['Value']
                    parameter_id = sel_par.rl_par.Id
                    param_storage_type = sel_par.rl_par.StorageType
                    categories = List[DB.ElementId]()
                    categories.Add(sel_cat.cat.Id)
                    solid_fill_id = solid_fill_pattern_id()
                    items_listbox = wndw.list_box2.Items
                    for i, element in enumerate(items_listbox):
                        item = wndw.list_box2.Items[i]['Value']
                        # Assign color filled region
                        ogs = DB.OverrideGraphicSettings()
                        color = DB.Color(item.n1, item.n2, item.n3)
                        ogs.SetSurfaceForegroundPatternColor(color)
                        ogs.SetCutForegroundPatternColor(color)
                        ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                        ogs.SetCutForegroundPatternId(solid_fill_id)
                        # Get filters apply to view
                        filter_name = sel_cat.name + "/" + sel_par.name + " - " + item.value
                        # added ':' character and chaged the removal method to translate, ref: issue #2466
                        filter_name = filter_name.translate({ord(i): None for i in "{}[]:\\|?/<>*"})
                        if filter_name in dict_filters or filter_name in dict_rules:
                            if filter_name in dict_rules and filter_name not in dict_filters:
                                view.AddFilter(dict_rules[filter_name])
                                view.SetFilterOverrides(dict_rules[filter_name], ogs)
                            else:
                                # Reassign filter
                                view.SetFilterOverrides(dict_filters[filter_name], ogs)
                        else:
                            # Create filter
                            if param_storage_type == DB.StorageType.Double:
                                if item.value == "None" or len(item.values_double) == 0:
                                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, "" , 0.001)
                                else:
                                    minimo = min(item.values_double)
                                    maximo = max(item.values_double)
                                    avg_values = (maximo+minimo)/2
                                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, avg_values, fabs(avg_values-minimo)+0.001)
                            elif param_storage_type == DB.StorageType.ElementId:
                                if item.value == "None":
                                    prevalue = DB.ElementId.InvalidElementId
                                else:
                                    prevalue = item.par.AsElementId()
                                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, prevalue)
                            elif param_storage_type == DB.StorageType.Integer:
                                if item.value == "None":
                                    prevalue = 0
                                else:
                                    prevalue = item.par.AsInteger()
                                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, prevalue)
                            elif param_storage_type == DB.StorageType.String:
                                if item.value == "None":
                                    prevalue = ""
                                else:
                                    prevalue = item.value
                                if version > 2023:
                                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, prevalue)
                                else:
                                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, prevalue, True)
                            else:
                                task2 = UI.TaskDialog("Color Elements by Parameter")
                                task2.MainInstruction = "Creation of filters for this type of parameter is not supported."
                                wndw.TopMost = False
                                task2.Show()
                                wndw.TopMost = True
                                break
                            try:
                                elem_filter = DB.ElementParameterFilter(equals_rule)
                                fltr = DB.ParameterFilterElement.Create(new_doc, filter_name, categories, elem_filter)
                                view.AddFilter(fltr.Id)
                                view.SetFilterOverrides(fltr.Id, ogs)
                            except Exception:
                                external_event_trace()
                                task2 = UI.TaskDialog("Color Elements by Parameter")
                                task2.MainInstruction = "View filters were not created. The selected parameter is not exposed by Revit and rules cannot be created."
                                wndw.TopMost = False
                                task2.Show()
                                wndw.TopMost = True
                                break
        except Exception:
            external_event_trace()

    def GetName(self):
        return "Create Filters"


class ValuesInfo():
    def __init__(self, para, val, idt, num1, num2, num3):
        self.par = para
        self.value = val
        self.name = strip_accents(para.Definition.Name)
        self.ele_id = List[DB.ElementId]()
        self.ele_id.Add(idt)
        self.n1 = num1
        self.n2 = num2
        self.n3 = num3
        self.colour = Drawing.Color.FromArgb(self.n1, self.n2, self.n3)
        self.values_double = []
        if para.StorageType == DB.StorageType.Double:
            self.values_double.append(para.AsDouble())
        elif para.StorageType == DB.StorageType.ElementId:
            self.values_double.append(para.AsElementId())


class ParameterInfo():
    def __init__(self, param_type, para):
        self.param_type = param_type
        self.rl_par = para
        self.par = para.Definition
        self.name = strip_accents(para.Definition.Name)


class CategoryInfo():
    def __init__(self, category, param):
        self.name = strip_accents(category.Name)
        self.cat = category
        get_elementid_value = get_elementid_value_func()
        self.int_id = get_elementid_value(category.Id)
        self.par = param



class FormCats(Forms.Form):
    def __init__(self, categories, ext_ev, uns_ev, s_view, reset_event, ev_legend, ev_filters):
        self.Font = Drawing.Font("Arial", 15, Drawing.FontStyle.Regular, Drawing.GraphicsUnit.Pixel)
        self.IsOpen = 1
        self.filter_ev = ev_filters
        self.legend_ev = ev_legend
        self.reset_ev = reset_event
        self.crt_view = s_view
        self.event = ext_ev
        self.uns_event = uns_ev
        self.uns_event.Raise()
        self.categs = categories
        self.width_par = 1
        self.table_data = DataTable("Data")
        self.table_data.Columns.Add("Key", System.String)
        self.table_data.Columns.Add("Value", System.Object)
        names = [x.name for x in self.categs]
        self.table_data.Rows.Add("Select a Category Here!", 0 )
        for key_, value_ in zip(names, self.categs):
            self.table_data.Rows.Add(key_, value_)
        self.out = []
        self.InitializeComponent()

    def InitializeComponent(self):
        self._spr_top = Forms.Label()
        self._categories = Forms.ComboBox()
        self._list_box1 = Forms.CheckedListBox()
        self.list_box2 = Forms.ListBox()
        self._button_set_colors = Forms.Button()
        self._button_reset_colors = Forms.Button()
        self._button_random_colors = Forms.Button()
        self._button_gradient_colors = Forms.Button()
        self._button_create_legend = Forms.Button()
        self._button_create_view_filters = Forms.Button()
        self._button_save_load_scheme = Forms.Button()
        self._txt_block2 = Forms.Label()
        self._txt_block3 = Forms.Label()
        self._txt_block4 = Forms.Label()
        self._txt_block5 = Forms.Label()
        self.tooltips = Forms.ToolTip()
        self.SuspendLayout()
        # Separator Top
        self._spr_top.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        self._spr_top.Location = Drawing.Point(0, 0)
        self._spr_top.Name = "spr_top"
        self._spr_top.Size = Drawing.Size(2000, 2)
        self._spr_top.BackColor = Drawing.Color.FromArgb(82, 53, 239)
        # TextBlock2
        self._txt_block2.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block2.Location = Drawing.Point(12, 2)
        self._txt_block2.Name = "txtBlock2"
        self._txt_block2.Size = Drawing.Size(120, 25)
        self._txt_block2.Text = "Category:"
        self.tooltips.SetToolTip(self._txt_block2, "Select a category to start coloring.")
        # comboBox1 Cat
        self._categories.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        self._categories.Location = Drawing.Point(12, 27)
        self._categories.Name = "dropDown"
        self._categories.DataSource = self.table_data
        self._categories.DisplayMember = "Key"
        self._categories.Size = Drawing.Size(310, 244)
        self._categories.DropDownWidth = 150
        self._categories.DropDownStyle = Forms.ComboBoxStyle.DropDownList
        self._categories.SelectedIndexChanged += self.update_filter
        self.tooltips.SetToolTip(self._categories, "Select a category to start coloring.")
        # TextBlock3
        self._txt_block3.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block3.Location = Drawing.Point(12, 57)
        self._txt_block3.Name = "txtBlock3"
        self._txt_block3.Size = Drawing.Size(120, 20)
        self._txt_block3.Text = "Parameters:"
        self.tooltips.SetToolTip(self._txt_block3, "Select a parameter to color elements based on its value.")
        # checkedListBox1
        self._list_box1.Anchor = Forms.AnchorStyles.Top |  Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        self._list_box1.FormattingEnabled = True
        self._list_box1.CheckOnClick = True
        self._list_box1.HorizontalScrollbar = True
        self._list_box1.Location = Drawing.Point(12, 80)
        self._list_box1.Name = "checkedListBox1"
        self._list_box1.DisplayMember = "Key"
        self._list_box1.Size = Drawing.Size(310, 158)
        self._list_box1.ItemCheck += self.check_item
        self.tooltips.SetToolTip(self._list_box1, "Select a parameter to color elements based on its value.")
        # TextBlock4
        self._txt_block4.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block4.Location = Drawing.Point(12, 238)
        self._txt_block4.Name = "txtBlock4"
        self._txt_block4.Size = Drawing.Size(120, 23)
        self._txt_block4.Text = "Values:"
        self.tooltips.SetToolTip(self._txt_block4, "Reassign colors by clicking on their value.")
        # TextBlock5
        self._txt_block5.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._txt_block5.Location = Drawing.Point(12, 585)
        self._txt_block5.Name = "txtBlock5"
        self._txt_block5.Size = Drawing.Size(310, 27)
        self._txt_block5.Text = "*Spaces may require a color scheme in the view."
        self._txt_block5.ForeColor = Drawing.Color.Red
        self._txt_block5.Font = Drawing.Font("Arial", 8, Drawing.FontStyle.Underline)
        self._txt_block5.Visible = False
        # checkedListBox2
        self.list_box2.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self.list_box2.FormattingEnabled = True
        self.list_box2.HorizontalScrollbar = True
        self.list_box2.Location = Drawing.Point(12, 262)
        self.list_box2.Name = "listBox2"
        self.list_box2.DisplayMember = "Key"
        self.list_box2.DrawMode = Forms.DrawMode.OwnerDrawFixed
        self.list_box2.DrawItem += self.colour_item
        self.new_fnt = Drawing.Font(self.Font.FontFamily, self.Font.Size-4, Drawing.FontStyle.Bold)
        g = self.list_box2.CreateGraphics()
        self.list_box2.ItemHeight = int(g.MeasureString("Sample", self.new_fnt).Height)
        self.list_box2.Size = Drawing.Size(310, 280)
        self.tooltips.SetToolTip(self.list_box2, "Reassign colors by clicking on their value.")
        # set_colors_button
        self._button_set_colors.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self._button_set_colors.Location = Drawing.Point(222, 632)
        self._button_set_colors.Name = "button_set_colors"
        self._button_set_colors.Size = Drawing.Size(100, 27)
        self._button_set_colors.Text = "Set Colors"
        self._button_set_colors.UseVisualStyleBackColor = True
        self._button_set_colors.Click += self.button_click_set_colors
        self.tooltips.SetToolTip(self._button_set_colors, "Apply the colors from each value in your Revit view.")
        # reset_colors_button
        self._button_reset_colors.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._button_reset_colors.Location = Drawing.Point(12, 632)
        self._button_reset_colors.Name = "button_reset_colors"
        self._button_reset_colors.Size = Drawing.Size(100, 27)
        self._button_reset_colors.Text = "Reset"
        self._button_reset_colors.UseVisualStyleBackColor = True
        self._button_reset_colors.Click += self.button_click_reset
        self.tooltips.SetToolTip(self._button_reset_colors, "Reset the colors in your Revit view to its initial stage.")
        # random_colors_button
        self._button_random_colors.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self._button_random_colors.Location = Drawing.Point(167, 538)
        self._button_random_colors.Name = "button_random_colors"
        self._button_random_colors.Size = Drawing.Size(156, 25)
        self._button_random_colors.Text = "Random Colors"
        self._button_random_colors.UseVisualStyleBackColor = True
        self._button_random_colors.Click += self.button_click_random_colors
        self.tooltips.SetToolTip(self._button_random_colors, "Reassign new random colors to all values.")
        # gradient_colors_button
        self._button_gradient_colors.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._button_gradient_colors.Location = Drawing.Point(11, 538)
        self._button_gradient_colors.Name = "button_gradient_colors"
        self._button_gradient_colors.Size = Drawing.Size(156, 25)
        self._button_gradient_colors.Text = "Gradient Colors"
        self._button_gradient_colors.UseVisualStyleBackColor = True
        self._button_gradient_colors.Click += self.button_click_gradient_colors
        self.tooltips.SetToolTip(self._button_gradient_colors, "Based on the color of the first and last value,\nreassign gradients colors to all values.")
        # create_legend_button
        self._button_create_legend.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._button_create_legend.Location = Drawing.Point(11, 593)
        self._button_create_legend.Name = "button_create_legend"
        self._button_create_legend.Size = Drawing.Size(156, 25)
        self._button_create_legend.Text = "Create Legend"
        self._button_create_legend.UseVisualStyleBackColor = True
        self._button_create_legend.Click += self.button_click_create_legend
        self.tooltips.SetToolTip(self._button_create_legend, "Create a new legend view for all the values and their colors.")
        # create_view_filters_button
        self._button_create_view_filters.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self._button_create_view_filters.Location = Drawing.Point(167, 593)
        self._button_create_view_filters.Name = "button_create_view_filters"
        self._button_create_view_filters.Size = Drawing.Size(156, 25)
        self._button_create_view_filters.Text = "Create View Filters"
        self._button_create_view_filters.UseVisualStyleBackColor = True
        self._button_create_view_filters.Click += self.button_click_create_view_filters
        self.tooltips.SetToolTip(self._button_create_view_filters, "Create view filters and rules for all the values and their colors.")
        # save_load_button
        self._button_save_load_scheme.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right | Forms.AnchorStyles.Left
        self._button_save_load_scheme.Location = Drawing.Point(11, 565)
        self._button_save_load_scheme.Name = "button_save_load_scheme"
        self._button_save_load_scheme.Size = Drawing.Size(312, 25)
        self._button_save_load_scheme.Text = "Save / Load Color Scheme"
        self._button_save_load_scheme.UseVisualStyleBackColor = True
        self._button_save_load_scheme.Click += self.save_load_color_scheme
        self.tooltips.SetToolTip(self._button_save_load_scheme, "Save the current color scheme or load an existing one.")
        # Form
        self.TopMost = True
        self.ShowInTaskbar = False
        self.ClientSize = Drawing.Size(334, 672)
        self.MaximizeBox = 0
        self.MinimizeBox = 0
        self.CenterToScreen()
        self.FormBorderStyle = Forms.FormBorderStyle.Sizable
        self.SizeGripStyle = Forms.SizeGripStyle.Show
        self.ShowInTaskbar = True
        self.MaximizeBox = True
        self.MinimizeBox = True
        self.Controls.Add(self._spr_top)
        self.Controls.Add(self._button_set_colors)
        self.Controls.Add(self._button_reset_colors)
        self.Controls.Add(self._button_random_colors)
        self.Controls.Add(self._button_gradient_colors)
        self.Controls.Add(self._button_create_legend)
        self.Controls.Add(self._button_create_view_filters)
        self.Controls.Add(self._button_save_load_scheme)
        self.Controls.Add(self._categories)
        self.Controls.Add(self._txt_block2)
        self.Controls.Add(self._txt_block3)
        self.Controls.Add(self._txt_block4)
        self.Controls.Add(self._txt_block5)
        self.Controls.Add(self._list_box1)
        self.Controls.Add(self.list_box2)
        self.Name = "Color Elements By Parameter"
        self.Text = "Color Elements By Parameter"
        self.Closing += self.closing_event
        icon_filename = __file__.replace('script.py', 'color_splasher.ico')
        if not exists(icon_filename):
            icon_filename = __file__.replace('script.py', 'color_splasher.ico')
        self.Icon = Drawing.Icon(icon_filename)
        self.ResumeLayout(False)

    def button_click_set_colors(self, sender, e):
        if self.list_box2.Items.Count <= 0:
            return
        else:
            self.event.Raise()

    def button_click_reset(self, sender, e):
        self.reset_ev.Raise()

    def button_click_random_colors(self, sender, e):
        try:
            checkindex = self._list_box1.CheckedIndices
            for indx in checkindex:
                self._list_box1.SetItemChecked(indx, False)
                self._list_box1.SetItemChecked(indx, True)
        except Exception:
            external_event_trace()

    def button_click_gradient_colors(self, sender, e):
        self.list_box2.SelectedIndexChanged -= self.list_selected_index_changed
        try:
            list_values=[]
            number_items = len(self.list_box2.Items)
            if number_items <= 2:
                return
            else:
                start_color = self.list_box2.Items[0]['Value'].colour
                end_color = self.list_box2.Items[number_items-1]['Value'].colour
                list_colors = self.get_gradient_colors(start_color, end_color, number_items)
                for indx, item in enumerate(self.list_box2.Items):
                    value = item['Value']
                    value.n1 = abs(list_colors[indx][1])
                    value.n2 = abs(list_colors[indx][2])
                    value.n3 = abs(list_colors[indx][3])
                    value.colour = Drawing.Color.FromArgb(value.n1, value.n2, value.n3)
                    list_values.append(value)
                self._table_data_3 = DataTable("Data")
                self._table_data_3.Columns.Add("Key", System.String)
                self._table_data_3.Columns.Add("Value", System.Object)
                vl_par = [x.value for x in list_values]
                for key_, value_ in zip(vl_par, list_values):
                    self._table_data_3.Rows.Add(key_, value_)
                self.list_box2.DataSource = self._table_data_3
                self.list_box2.DisplayMember = "Key"
                self.list_box2.SelectedIndex = -1
        except Exception:
            external_event_trace()
        self.list_box2.SelectedIndexChanged += self.list_selected_index_changed

    def button_click_create_legend(self, sender, e):
        if self.list_box2.Items.Count <= 0:
            return
        else:
            self.legend_ev.Raise()

    def button_click_create_view_filters(self, sender, e):
        if self.list_box2.Items.Count <= 0:
            return
        else:
            self.reset_ev.Raise()
            self.filter_ev.Raise()

    def save_load_color_scheme(self, sender, e):
        saveform = FormSaveLoadScheme()
        saveform.Show()

    def get_gradient_colors(self, start_color, end_color, steps):
        a_step = float((end_color.A - start_color.A) / steps)
        r_step = float((end_color.R - start_color.R) / steps)
        g_step = float((end_color.G - start_color.G) / steps)
        b_step = float((end_color.B - start_color.B) / steps)
        color_list = []
        for index in range(steps):
            a = max(start_color.A + int(a_step * index) - 1, 0)
            r = max(start_color.R + int(r_step * index) - 1, 0)
            g = max(start_color.G + int(g_step * index) - 1, 0)
            b = max(start_color.B + int(b_step * index) - 1, 0)
            color_list.append([a, r, g, b])
        return color_list

    def closing_event(self, sender, e):
        self.IsOpen = 0
        self.uns_event.Raise()

    def list_selected_index_changed(self, sender, e):
        if sender.SelectedIndex == -1:
            return
        else:
            clr_dlg = Forms.ColorDialog()
            clr_dlg.AllowFullOpen = True
            if clr_dlg.ShowDialog() == Forms.DialogResult.OK:
                sender.SelectedItem['Value'].n1 = clr_dlg.Color.R
                sender.SelectedItem['Value'].n2 = clr_dlg.Color.G
                sender.SelectedItem['Value'].n3 = clr_dlg.Color.B
                sender.SelectedItem['Value'].colour = Drawing.Color.FromArgb(clr_dlg.Color.R, clr_dlg.Color.G, clr_dlg.Color.B)
            self.list_box2.SelectedIndex = -1

    def colour_item(self, sender, e):
        try:
            cnt = e.Index
            g = e.Graphics
            text_device = sender.Items[e.Index]['Key']
            color = sender.Items[e.Index]['Value'].colour
            if cnt == self.list_box2.SelectedIndex or color == Drawing.Color.FromArgb(Drawing.Color.White.R, Drawing.Color.White.G, Drawing.Color.White.B):
                color = Drawing.Color.White
                font_color = Drawing.Color.Black
            else:
                font_color = Drawing.Color.White
            wdth = g.MeasureString(text_device, self.new_fnt).Width + 30
            if self.list_box2.Width < wdth and self.list_box2.HorizontalExtent < wdth:
                self.list_box2.HorizontalExtent = wdth
            e.DrawBackground()
            g.FillRectangle(Drawing.SolidBrush(color), e.Bounds)
            Forms.TextRenderer.DrawText(g, text_device, self.new_fnt, e.Bounds, font_color, Forms.TextFormatFlags.Left)
            e.DrawFocusRectangle()
        except Exception:
            external_event_trace()

    def check_item(self, sender, e):
        # Only one element can be selected
        for indx in range(self._list_box1.Items.Count):
            if indx != e.Index:
                self._list_box1.SetItemChecked(indx, False)
        try:
            self.list_box2.SelectedIndexChanged -= self.list_selected_index_changed
        except Exception:
            external_event_trace()
        sel_cat = self._categories.SelectedItem['Value']
        sel_param = sender.Items[e.Index]['Value']
        if sel_cat is None or sel_cat == 0:
            return
        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)
        if e.NewValue == Forms.CheckState.Unchecked:
            self.list_box2.DataSource = self._table_data_3
            self.list_box2.DisplayMember = "Key"
        else:
            rng_val = get_range_values(sel_cat, sel_param, self.crt_view)
            vl_par = [x.value for x in rng_val]
            g = self.list_box2.CreateGraphics()
            if len(vl_par) != 0:
                width = [int(g.MeasureString(x, self.list_box2.Font).Width) for x in vl_par]
                self.list_box2.HorizontalExtent = max(width) + 50
            for key_, value_ in zip(vl_par, rng_val):
                self._table_data_3.Rows.Add(key_, value_)
            self.list_box2.DataSource = self._table_data_3
            self.list_box2.DisplayMember = "Key"
            self.list_box2.SelectedIndex = -1
            self.list_box2.SelectedIndexChanged += self.list_selected_index_changed

    def update_filter(self, sender, e):
        # Update param listbox
        sel_cat = sender.SelectedItem['Value']
        self._table_data_2 = DataTable("Data")
        self._table_data_2.Columns.Add("Key", System.String)
        self._table_data_2.Columns.Add("Value", System.Object)
        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)
        if sel_cat != 0 and sender.SelectedIndex != 0:
            names_par = [x.name for x in sel_cat.par]
            for key_, value_ in zip(names_par, sel_cat.par):
                self._table_data_2.Rows.Add(key_, value_)
            self._list_box1.DataSource = self._table_data_2
            self._list_box1.DisplayMember = "Key"
            for indx in range(self._list_box1.Items.Count):
                self._list_box1.SetItemChecked(indx, False)
            self.list_box2.DataSource = self._table_data_3
        else:
            self._list_box1.DataSource = self._table_data_2
            self.list_box2.DataSource = self._table_data_3


class FormSaveLoadScheme(Forms.Form):
    def __init__(self):
        self.Font = Drawing.Font(self.Font.FontFamily, 16, Drawing.FontStyle.Regular, Drawing.GraphicsUnit.Pixel)
        self.TopMost = True
        self.InitializeComponent()

    def InitializeComponent(self):
        self._btn_save = Forms.Button()
        self._btn_load = Forms.Button()
        self._txt_ifloading = Forms.Label()
        self._radio_by_value = Forms.RadioButton()
        self._radio_by_pos = Forms.RadioButton()
        self.tooltip1 = Forms.ToolTip()
        self._spr_top = Forms.Label()
        self.SuspendLayout()
        # Separator Top
        self._spr_top.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        self._spr_top.Location = Drawing.Point(0, 0)
        self._spr_top.Name = "spr_top"
        self._spr_top.Size = Drawing.Size(500, 2)
        self._spr_top.BackColor = Drawing.Color.FromArgb(82, 53, 239)
        # If loading
        self._txt_ifloading.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_ifloading.Location = Drawing.Point(12, 10)
        self._txt_ifloading.Text = "If Loading a Color Scheme:"
        self._txt_ifloading.Name = "_radio_byValue"
        self._txt_ifloading.Size = Drawing.Size(239, 23)
        self.tooltip1.SetToolTip(self._txt_ifloading, "Only if loading.")
        # Radio by value
        self._radio_by_value.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._radio_by_value.Location = Drawing.Point(19, 35)
        self._radio_by_value.Text = "Load by Parameter Value."
        self._radio_by_value.Name = "_radio_byValue"
        self._radio_by_value.Size = Drawing.Size(230, 25)
        self._radio_by_value.Checked = True
        self.tooltip1.SetToolTip(self._radio_by_value, "Only if loading. This will load the color scheme based on the Value the item had when saving.")
        # Radio by Pos
        self._radio_by_pos.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._radio_by_pos.Location = Drawing.Point(250, 35)
        self._radio_by_pos.Text = "Load by Position in Window."
        self._radio_by_pos.Name = "_radio_byValue"
        self._radio_by_pos.Size = Drawing.Size(239, 25)
        self.tooltip1.SetToolTip(self._radio_by_pos, "Only if loading. This will load the color scheme based on the Position the item had when saving.")
        # Button Save
        self._btn_save.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self._btn_save.Location = Drawing.Point(13, 70)
        self._btn_save.Name = "btn_cancel"
        self._btn_save.Size = Drawing.Size(236, 25)
        self._btn_save.Text = "Save Color Scheme"
        self._btn_save.Cursor = Forms.Cursors.Hand
        self._btn_save.Click += self.specify_path_save
        # Button Load
        self._btn_load.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        self._btn_load.Location = Drawing.Point(253, 70)
        self._btn_load.Name = "btn_cancel"
        self._btn_load.Size = Drawing.Size(236, 25)
        self._btn_load.Text = "Load Color Scheme"
        self._btn_load.Cursor = Forms.Cursors.Hand
        self._btn_load.Click += self.specify_path_load
        # Add Controls and Window configuration.
        self.Controls.Add(self._txt_ifloading)
        self.Controls.Add(self._radio_by_value)
        self.Controls.Add(self._radio_by_pos)
        self.Controls.Add(self._btn_save)
        self.Controls.Add(self._btn_load)
        self.Controls.Add(self._spr_top)
        self.MaximizeBox = 0
        self.MinimizeBox = 0
        self.ClientSize = Drawing.Size(500, 105)
        self.Name = "Save / Load Color Scheme"
        self.Text = "Save / Load Color Scheme"
        self.FormBorderStyle = Forms.FormBorderStyle.FixedSingle
        self.CenterToScreen()
        icon_filename = __file__.replace('script.py', 'color_splasher.ico')
        if not exists(icon_filename):
            icon_filename = __file__.replace('script.py', 'color_splasher.ico')
        self.Icon = Drawing.Icon(icon_filename)
        self.ResumeLayout(False)

    def specify_path_save(self, sender, e):
        # Prompt save file dialog and its configuration.
        with Forms.SaveFileDialog() as save_file_dialog:
            save_file_dialog.Title = "Specify Path to Save Color Scheme"
            save_file_dialog.Filter = "Color Scheme (*.cschn)|*.cschn"
            save_file_dialog.RestoreDirectory = True
            save_file_dialog.OverwritePrompt = True
            save_file_dialog.InitialDirectory = System.Environment.GetFolderPath(System.Environment.SpecialFolder.Desktop)
            save_file_dialog.FileName = "Color Scheme.cschn"
            if len(wndw.list_box2.Items) == 0:
                wndw.Hide()
                self.Hide()
                UI.TaskDialog.Show("No Colors Detected", "The list of values in the main window is empty. Please, select a category and parameter to add items with colors.")
                wndw.Show()
                self.Close()
            elif save_file_dialog.ShowDialog() == Forms.DialogResult.OK:
                # Main path for new file
                self.save_path_to_file(save_file_dialog.FileName)
                self.Close()

    def save_path_to_file(self, new_path):
        try:
            # Save location selected in save file dialog.
            with open(new_path, "w") as file:
                for item in wndw.list_box2.Items:
                    color_inst = item['Value'].colour
                    file.write(item['Key'] + "::R" + str(color_inst.R) + "G" + str(color_inst.G) + "B" + str(color_inst.B) + "\n")
        except Exception as ex:
            # If file is being used or blocked by OS/program.
            external_event_trace()
            UI.TaskDialog.Show("Error Saving Scheme", str(ex))

    def specify_path_load(self, sender, e):
        # Prompt save file dialog and its configuration.
        with Forms.OpenFileDialog() as open_file_dialog:
            open_file_dialog.Title = "Specify Path to Load Color Scheme"
            open_file_dialog.Filter = "Color Scheme (*.cschn)|*.cschn"
            open_file_dialog.RestoreDirectory = True
            open_file_dialog.InitialDirectory = System.Environment.GetFolderPath(System.Environment.SpecialFolder.Desktop)
            if len(wndw.list_box2.Items) == 0:
                wndw.Hide()
                self.Hide()
                UI.TaskDialog.Show("No Values Detected", "The list of values in the main window is empty. Please, select a category and parameter to add items to apply colors.")
                wndw.Show()
                self.Close()
            elif open_file_dialog.ShowDialog() == Forms.DialogResult.OK:
                # Main path for new file
                self.load_path_from_file(open_file_dialog.FileName)
                self.Close()

    def load_path_from_file(self, path):
        if not isfile(path):
            UI.TaskDialog.Show("Error Loading Scheme", "The file does not exist.")
        else:
            # Load last location selected in save file dialog.
            try:
                with open(path, "r") as file:
                    all_lines = file.readlines()
                    if self._radio_by_value.Checked:
                        for line in all_lines:
                            line_val = line.strip().split("::R")
                            par_val = line_val[0]
                            rgb_result = split(r'[RGB]', line_val[1])
                            for item in wndw._table_data_3.Rows:
                                if item['Key'] == par_val:
                                    self.apply_color_to_item(rgb_result, item)
                                    break
                    else:
                        for ind, line in enumerate(all_lines):
                            if ind < len(wndw._table_data_3.Rows):
                                line_val = line.strip().split("::R")
                                par_val = line_val[0]
                                rgb_result = split(r'[RGB]', line_val[1])
                                item = wndw._table_data_3.Rows[ind]
                                self.apply_color_to_item(rgb_result, item)
                            else:
                                break
                    wndw.list_box2.Refresh()
            except Exception as ex:
                external_event_trace()
                # If file is being used or blocked by OS/program.
                UI.TaskDialog.Show("Error Loading Scheme", str(ex))

    def apply_color_to_item(self, rgb_result, item):
        r = int(rgb_result[0])
        g = int(rgb_result[1])
        b = int(rgb_result[2])
        item['Value'].n1 = r
        item['Value'].n2 = g
        item['Value'].n3 = b
        item['Value'].colour = Drawing.Color.FromArgb(r, g, b)


def get_active_view(ac_doc):
    selected_view = ac_doc.ActiveView
    if selected_view.ViewType == DB.ViewType.ProjectBrowser or selected_view.ViewType == DB.ViewType.SystemBrowser:
        selected_view = ac_doc.GetElement(uidoc.GetOpenUIViews()[0].ViewId)
    if not selected_view.CanUseTemporaryVisibilityModes():
        task2 = UI.TaskDialog("Color Elements by Parameter")
        task2.MainInstruction = "Visibility settings cannot be modified in " + str(selected_view.ViewType) + " views. Please, change your current view."
        try:
            wndw.TopMost = False
        except Exception:
            external_event_trace()
        task2.Show()
        try:
            wndw.TopMost = True
        except Exception:
            external_event_trace()
        return 0
    else:
        return selected_view


def get_parameter_value(para):
    if not para.HasValue:
        return "None"
    if para.StorageType == DB.StorageType.Double:
        return get_double_value(para)
    if para.StorageType == DB.StorageType.ElementId:
        return get_elementid_value(para)
    if para.StorageType == DB.StorageType.Integer:
        return get_integer_value(para)
    if para.StorageType == DB.StorageType.String:
        return para.AsString()
    else:
        return "None"

def get_double_value(para):
    return para.AsValueString()

def get_elementid_value(para):
    id_val = para.AsElementId()
    elementid_value = get_elementid_value_func()
    if elementid_value(id_val) >= 0:
        return DB.Element.Name.GetValue(doc.GetElement(id_val))
    else:
        return "None"

def get_integer_value(para):
    if version > 2021:
        param_type = para.Definition.GetDataType()
        if DB.SpecTypeId.Boolean.YesNo == param_type:
            return "True" if para.AsInteger() == 1 else "False"
        else:
            return para.AsValueString()
    else:
        param_type = para.Definition.ParameterType
        if DB.ParameterType.YesNo == param_type:
            return "True" if para.AsInteger() == 1 else "False"
        else:
            return para.AsValueString()


def strip_accents(text):
    return ''.join(char for char in normalize('NFKD', text) if unicode_category(char) != 'Mn')


def random_color():
    r = randint(0, 230)
    g = randint(0, 230)
    b = randint(0, 230)
    return r, g, b


def get_range_values(category, param, new_view):
    for sample_bic in System.Enum.GetValues(DB.BuiltInCategory):
        if category.int_id == int(sample_bic):
            bic = sample_bic
            break
    collector = (DB.FilteredElementCollector(doc, new_view.Id).OfCategory(bic).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElements())
    list_values = []
    used_colors = {(x.n1, x.n2, x.n3) for x in list_values}
    for ele in collector:
        ele_par = ele if param.param_type != 1 else doc.GetElement(ele.GetTypeId())
        for pr in ele_par.Parameters:
            if pr.Definition.Name == param.par.Name:
                value = get_parameter_value(pr) or "None"
                match = [x for x in list_values if x.value == value]
                if match:
                    match[0].ele_id.Add(ele.Id)
                    if pr.StorageType == DB.StorageType.Double:
                        match[0].values_double.Add(pr.AsDouble())
                else:
                    while True:
                        r, g, b = random_color()
                        if (r, g, b) not in used_colors:
                            used_colors.add((r, g, b))
                            val = ValuesInfo(pr, value, ele.Id, r, g, b)
                            list_values.append(val)
                            break
                break
    none_values = [x for x in list_values if x.value == "None"]
    list_values = [x for x in list_values if x.value != "None"]
    list_values = sorted(list_values, key=lambda x: x.value, reverse=False)
    if len(list_values) > 1:
        try:
            first_value = list_values[0].value
            indx_del = get_index_units(first_value)
            if indx_del == 0:
                list_values = sorted(list_values, key=lambda x: safe_float(x.value))
            elif 0 < indx_del < len(first_value):
                list_values = sorted(list_values, key=lambda x: safe_float(x.value[:-indx_del]))
        except ValueError as ve:
            print("ValueError during sorting: {}".format(ve))
        except Exception:
            external_event_trace()
    if none_values and any(len(x.ele_id) > 0 for x in none_values):
        list_values.extend(none_values)
    return list_values


def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return float('inf')  # Place non-numeric values at the end


def get_used_categories_parameters(cat_exc, acti_view):
    # Get All elements and filter unneeded
    collector = DB.FilteredElementCollector(doc, acti_view.Id).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElements()
    list_cat = []
    for ele in collector:
        if ele.Category is None:
            continue
        get_elementid_value = get_elementid_value_func()
        current_int_cat_id = get_elementid_value(ele.Category.Id)
        if current_int_cat_id in cat_exc or current_int_cat_id >= -1 or any(x.int_id == current_int_cat_id for x in list_cat):
            continue
        list_parameters = []
        # Instance parameters
        for par in ele.Parameters:
            if par.Definition.BuiltInParameter not in (DB.BuiltInParameter.ELEM_CATEGORY_PARAM, DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT):
                list_parameters.append(ParameterInfo(0, par))
        typ = ele.Document.GetElement(ele.GetTypeId())
        # Type parameters
        if typ is None:
            continue
        for par in typ.Parameters:
            if par.Definition.BuiltInParameter not in (DB.BuiltInParameter.ELEM_CATEGORY_PARAM, DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT):
                list_parameters.append(ParameterInfo(1, par))
        # Sort and add
        list_parameters = sorted(list_parameters, key=lambda x: x.name.upper(), reverse=False)
        list_cat.append(CategoryInfo(ele.Category, list_parameters))
    list_cat = sorted(list_cat, key=lambda x: x.name, reverse=False)
    return list_cat


def solid_fill_pattern_id():
    solid_fill_id = None
    fillpatterns = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
    for pat in fillpatterns:
        if pat.GetFillPattern().IsSolidFill:
            solid_fill_id = pat.Id
            break
    return solid_fill_id


def external_event_trace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    logger.debug("Exception type: %s",exc_type)
    logger.debug("Exception value: %s",exc_value)
    logger.debug("Traceback details:")
    for tb in extract_tb(exc_traceback):
        logger.debug("File: %s, Line: %s, Function: %s, Code: %s",tb[0], tb[1], tb[2], tb[3])


def get_index_units(str_value):
    for let in str_value[::-1]:
        if let.isdigit():
            return str_value[::-1].index(let)
    return -1


doc = revit.DOCS.doc
uidoc = HOST_APP.uiapp.ActiveUIDocument
version = int(HOST_APP.version)
uiapp = HOST_APP.uiapp

sel_view = get_active_view(doc)
if sel_view != 0:
    # Get categories in used
    categ_inf_used = get_used_categories_parameters(CAT_EXCLUDED, sel_view)
    # Window
    event_handler = ApplyColors()
    ext_event = UI.ExternalEvent.Create(event_handler)

    event_handler_uns = SubscribeView()
    ext_event_uns = UI.ExternalEvent.Create(event_handler_uns)

    event_handler_filters = CreateFilters()
    ext_event_filters = UI.ExternalEvent.Create(event_handler_filters)

    event_handler_reset = ResetColors()
    ext_event_reset = UI.ExternalEvent.Create(event_handler_reset)

    event_handler_Legend = CreateLegend()
    ext_event_legend = UI.ExternalEvent.Create(event_handler_Legend)

    wndw = FormCats(categ_inf_used, ext_event, ext_event_uns, sel_view, ext_event_reset, ext_event_legend, ext_event_filters)
    wndw._categories.SelectedIndex = -1
    wndw.Show()
