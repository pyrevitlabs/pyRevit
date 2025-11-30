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
from pyrevit import script as pyrevit_script
import clr

clr.AddReference("System.Data")
clr.AddReference("System")
from System.Data import DataTable


# Categories to exclude
CAT_EXCLUDED = (
    int(DB.BuiltInCategory.OST_RoomSeparationLines),
    int(DB.BuiltInCategory.OST_Cameras),
    int(DB.BuiltInCategory.OST_CurtainGrids),
    int(DB.BuiltInCategory.OST_Elev),
    int(DB.BuiltInCategory.OST_Grids),
    int(DB.BuiltInCategory.OST_IOSModelGroups),
    int(DB.BuiltInCategory.OST_Views),
    int(DB.BuiltInCategory.OST_SitePropertyLineSegment),
    int(DB.BuiltInCategory.OST_SectionBox),
    int(DB.BuiltInCategory.OST_ShaftOpening),
    int(DB.BuiltInCategory.OST_BeamAnalytical),
    int(DB.BuiltInCategory.OST_StructuralFramingOpening),
    int(DB.BuiltInCategory.OST_MEPSpaceSeparationLines),
    int(DB.BuiltInCategory.OST_DuctSystem),
    int(DB.BuiltInCategory.OST_Lines),
    int(DB.BuiltInCategory.OST_PipingSystem),
    int(DB.BuiltInCategory.OST_Matchline),
    int(DB.BuiltInCategory.OST_CenterLines),
    int(DB.BuiltInCategory.OST_CurtainGridsRoof),
    int(DB.BuiltInCategory.OST_SWallRectOpening),
    -2000278,
    -1,
)

logger = get_logger()  # get logger and trigger debug mode using CTRL+click


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
        wndw = SubscribeView._wndw
        if wndw and wndw.IsOpen == 1:
            if self.registered == 0:
                new_doc = e.Document
                if new_doc:
                    if wndw:
                        # Compare with current document from Revit context
                        try:
                            current_doc = revit.DOCS.doc
                            if not new_doc.Equals(current_doc):
                                wndw.Close()
                        except (AttributeError, RuntimeError):
                            # If can't get current doc, just continue
                            pass
                # Update categories in dropdown
                new_view = get_active_view(e.Document)
                if new_view != 0:
                    # Unsubcribe
                    wndw.list_box2.SelectedIndexChanged -= (
                        wndw.list_selected_index_changed
                    )
                    # Update categories for new view
                    wndw.crt_view = new_view
                    categ_inf_used_up = get_used_categories_parameters(
                        CAT_EXCLUDED, wndw.crt_view, new_doc
                    )
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
            wndw = ApplyColors._wndw
            if not wndw:
                return
            apply_line_color = wndw._chk_line_color.Checked
            apply_foreground_pattern_color = wndw._chk_foreground_pattern.Checked
            apply_background_pattern_color = wndw._chk_background_pattern.Checked
            if not apply_line_color and not apply_foreground_pattern_color and not apply_background_pattern_color:
                apply_foreground_pattern_color = True
            solid_fill_id = solid_fill_pattern_id()

            # Get current category and parameter selection
            sel_cat = wndw._categories.SelectedItem["Value"]
            if sel_cat == 0:
                return

            # Get the currently selected parameter
            if wndw._list_box1.SelectedIndex == -1:
                return
            checked_param = wndw._list_box1.SelectedItem["Value"]

            # Refresh element-to-value mappings to reflect current parameter values
            refreshed_values = get_range_values(sel_cat, checked_param, view)

            # Create a mapping of value strings to user-selected colors
            color_map = {}
            for indx in range(wndw.list_box2.Items.Count):
                item = wndw.list_box2.Items[indx]["Value"]
                color_map[item.value] = (item.n1, item.n2, item.n3)

            with revit.Transaction("Apply colors to elements"):
                get_elementid_value = get_elementid_value_func()
                version = int(HOST_APP.version)
                if get_elementid_value(sel_cat.cat.Id) in (
                    int(DB.BuiltInCategory.OST_Rooms),
                    int(DB.BuiltInCategory.OST_MEPSpaces),
                    int(DB.BuiltInCategory.OST_Areas),
                ):
                    # In case of rooms, spaces and areas. Check Color scheme is applied and if not
                    if version > 2021:
                        if wndw.crt_view.GetColorFillSchemeId(sel_cat.cat.Id).ToString() == "-1":
                            color_schemes = (
                                DB.FilteredElementCollector(new_doc)
                                .OfClass(DB.ColorFillScheme)
                                .ToElements()
                            )
                            if len(color_schemes) > 0:
                                for sch in color_schemes:
                                    if sch.CategoryId == sel_cat.cat.Id:
                                        if len(sch.GetEntries()) > 0:
                                            wndw.crt_view.SetColorFillSchemeId(
                                                sel_cat.cat.Id, sch.Id
                                            )
                                            break
                    else:
                        wndw._txt_block5.Visible = True
                else:
                    wndw._txt_block5.Visible = False

                # Apply colors using refreshed element IDs but preserved color choices
                for val_info in refreshed_values:
                    if val_info.value in color_map:
                        ogs = DB.OverrideGraphicSettings()
                        r, g, b = color_map[val_info.value]
                        base_color = DB.Color(r, g, b)
                        # Get color shades if multiple override types are enabled
                        line_color, foreground_color, background_color = get_color_shades(
                            base_color,
                            apply_line_color,
                            apply_foreground_pattern_color,
                            apply_background_pattern_color,
                        )
                        # Apply line color if enabled (both projection and cut)
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        # Apply foreground pattern color if enabled
                        if apply_foreground_pattern_color:
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        # Apply background pattern color if enabled (Revit 2019+)
                        # version already defined above
                        if apply_background_pattern_color and version >= 2019:
                            ogs.SetSurfaceBackgroundPatternColor(background_color)
                            ogs.SetCutBackgroundPatternColor(background_color)
                            # Set background pattern ID (solid fill) same as foreground
                            if solid_fill_id is not None:
                                ogs.SetSurfaceBackgroundPatternId(solid_fill_id)
                                ogs.SetCutBackgroundPatternId(solid_fill_id)
                        for idt in val_info.ele_id:
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
            wndw = ResetColors._wndw
            if not wndw:
                return
            ogs = DB.OverrideGraphicSettings()
            collector = (
                DB.FilteredElementCollector(new_doc, view.Id)
                .WhereElementIsNotElementType()
                .WhereElementIsViewIndependent()
                .ToElementIds()
            )
            sel_cat = wndw._categories.SelectedItem["Value"]
            if sel_cat == 0:
                task_no_cat = UI.TaskDialog("Color Elements by Parameter")
                task_no_cat.MainInstruction = (
                    "Please, select a category to reset the colors."
                )
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
            wndw = CreateLegend._wndw
            if not wndw:
                return
            apply_line_color = wndw._chk_line_color.Checked
            apply_foreground_pattern_color = wndw._chk_foreground_pattern.Checked
            apply_background_pattern_color = wndw._chk_background_pattern.Checked
            if not apply_line_color and not apply_foreground_pattern_color and not apply_background_pattern_color:
                apply_foreground_pattern_color = True
            # Get legend view
            collector = (
                DB.FilteredElementCollector(new_doc).OfClass(DB.View).ToElements()
            )
            legends = []
            for vw in collector:
                if vw.ViewType == DB.ViewType.Legend:
                    legends.append(vw)
                    break

            if len(legends) == 0:
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = "In order to create a new legend, you need to have at least one. Please, create a legend view."
                wndw.TopMost = False
                task2.Show()
                wndw.TopMost = True
                return

            # Check if we have selected items
            if wndw.list_box2.Items.Count == 0:
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = "No items to create a legend. Please select a category and parameter with values."
                wndw.TopMost = False
                task2.Show()
                wndw.TopMost = True
                return

            # Start transaction for legend creation
            t = DB.Transaction(new_doc, "Create Legend")
            t.Start()

            try:
                new_id_legend = legends[0].Duplicate(DB.ViewDuplicateOption.Duplicate)
                new_legend = new_doc.GetElement(new_id_legend)
                sel_cat = wndw._categories.SelectedItem["Value"]
                sel_par = wndw._list_box1.SelectedItem["Value"]
                cat_name = strip_accents(sel_cat.name)
                par_name = strip_accents(sel_par.name)
                renamed = False
                try:
                    new_legend.Name = "Color Splasher - " + cat_name + " - " + par_name
                    renamed = True
                except Exception:
                    external_event_trace()
                if not renamed:
                    for i in range(1000):
                        try:
                            new_legend.Name = (
                                "Color Splasher - "
                                + cat_name
                                + " - "
                                + par_name
                                + " - "
                                + str(i)
                            )
                            break
                        except Exception:
                            external_event_trace()
                            if i == 999:
                                raise Exception("Could not rename legend view")
                old_all_ele = DB.FilteredElementCollector(
                    new_doc, legends[0].Id
                ).ToElements()
                ele_id_type = None
                for ele in old_all_ele:
                    if ele.Id != new_legend.Id and ele.Category is not None:
                        if isinstance(ele, DB.TextNote):
                            ele_id_type = ele.GetTypeId()
                            break
                get_elementid_value = get_elementid_value_func()
                if not ele_id_type:
                    all_text_notes = (
                        DB.FilteredElementCollector(new_doc)
                        .OfClass(DB.TextNoteType)
                        .ToElements()
                    )
                    for ele in all_text_notes:
                        ele_id_type = ele.Id
                        break
                if get_elementid_value(ele_id_type) == 0:
                    raise Exception("No text note type found in the model")
                filled_type = None
                filled_region_types = (
                    DB.FilteredElementCollector(new_doc)
                    .OfClass(DB.FilledRegionType)
                    .ToElements()
                )

                for filled_region_type in filled_region_types:
                    pattern = new_doc.GetElement(filled_region_type.ForegroundPatternId)
                    if (
                        pattern is not None
                        and pattern.GetFillPattern().IsSolidFill
                        and filled_region_type.ForegroundPatternColor.IsValid
                    ):
                        filled_type = filled_region_type
                        break
                if not filled_type and filled_region_types:
                    for idx in range(100):
                        try:
                            new_type = filled_region_types[0].Duplicate(
                                "Fill Region " + str(idx)
                            )
                            break
                        except Exception:
                            external_event_trace()
                            if idx == 99:
                                raise Exception("Could not create fill region type")
                    for idx in range(100):
                        try:
                            new_pattern = DB.FillPattern(
                                "Fill Pattern " + str(idx),
                                DB.FillPatternTarget.Drafting,
                                DB.FillPatternHostOrientation.ToView,
                                float(0),
                                float(0.00001),
                            )
                            new_ele_pat = DB.FillPatternElement.Create(
                                new_doc, new_pattern
                            )
                            break
                        except Exception:
                            external_event_trace()
                            if idx == 99:
                                raise Exception("Could not create fill pattern")
                    new_type.ForegroundPatternId = new_ele_pat.Id
                    filled_type = new_type
                if filled_type is None:
                    raise Exception("Could not find or create a fill region type")

                list_max_x = []
                list_y = []
                list_text_heights = []
                y_pos = 0
                spacing = 0
                for index, vw_item in enumerate(wndw.list_box2.Items):
                    punto = DB.XYZ(0, y_pos, 0)
                    item = vw_item["Value"]
                    text_line = cat_name + " / " + par_name + " - " + item.value
                    new_text = DB.TextNote.Create(
                        new_doc, new_legend.Id, punto, text_line, ele_id_type
                    )
                    new_doc.Regenerate()
                    prev_bbox = new_text.get_BoundingBox(new_legend)
                    height = prev_bbox.Max.Y - prev_bbox.Min.Y
                    spacing = height * 0.25
                    list_max_x.append(prev_bbox.Max.X)
                    list_y.append(prev_bbox.Min.Y)
                    list_text_heights.append(height)
                    y_pos = prev_bbox.Min.Y - (height + spacing)
                ini_x = max(list_max_x) + spacing
                solid_fill_id = solid_fill_pattern_id() if apply_foreground_pattern_color else None
                for indx, y in enumerate(list_y):
                    try:
                        item = wndw.list_box2.Items[indx]["Value"]
                        height = list_text_heights[indx]
                        rect_width = height * 2

                        point0 = DB.XYZ(ini_x, y, 0)
                        point1 = DB.XYZ(ini_x, y + height, 0)
                        point2 = DB.XYZ(ini_x + rect_width, y + height, 0)
                        point3 = DB.XYZ(ini_x + rect_width, y, 0)
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
                        reg = DB.FilledRegion.Create(
                            new_doc, filled_type.Id, new_legend.Id, list_curve_loops
                        )
                        ogs = DB.OverrideGraphicSettings()
                        base_color = DB.Color(item.n1, item.n2, item.n3)
                        # Get color shades if multiple override types are enabled
                        line_color, foreground_color, background_color = get_color_shades(
                            base_color,
                            apply_line_color,
                            apply_foreground_pattern_color,
                            apply_background_pattern_color,
                        )
                        # Apply line color if enabled (both projection and cut)
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        # For filled regions, apply color to foreground pattern
                        # If foreground pattern is selected, use foreground_color
                        # If only background pattern is selected, use background_color for foreground
                        if apply_foreground_pattern_color:
                            # Use foreground color for filled region foreground
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        elif apply_background_pattern_color:
                            # If only background pattern is selected, use background_color for foreground
                            # (Revit doesn't display background pattern color on filled regions properly)
                            ogs.SetSurfaceForegroundPatternColor(background_color)
                            ogs.SetCutForegroundPatternColor(background_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        new_legend.SetElementOverrides(reg.Id, ogs)

                    except Exception as e:
                        logger.debug("Error creating filled region: %s", str(e))
                        continue

                t.Commit()

                # Inform user of success
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = (
                    "Legend created successfully: " + new_legend.Name
                )
                wndw.TopMost = False
                task2.Show()
                wndw.TopMost = True

            except Exception as e:
                # Rollback transaction on error
                if t.HasStarted() and not t.HasEnded():
                    t.RollBack()

                logger.debug("Legend creation failed: %s", str(e))
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = "Failed to create legend: " + str(e)
                wndw.TopMost = False
                task2.Show()
                wndw.TopMost = True
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
                wndw = CreateFilters._wndw
                if not wndw:
                    return
                apply_line_color = wndw._chk_line_color.Checked
                apply_foreground_pattern_color = wndw._chk_foreground_pattern.Checked
                apply_background_pattern_color = wndw._chk_background_pattern.Checked
                if not apply_line_color and not apply_foreground_pattern_color and not apply_background_pattern_color:
                    apply_foreground_pattern_color = True
                dict_filters = {}
                for filt_id in view.GetFilters():
                    filter_ele = new_doc.GetElement(filt_id)
                    dict_filters[filter_ele.Name] = filt_id
                # Get rules apply in document
                dict_rules = {}
                iterator = (
                    DB.FilteredElementCollector(new_doc)
                    .OfClass(DB.ParameterFilterElement)
                    .GetElementIterator()
                )
                while iterator.MoveNext():
                    ele = iterator.Current
                    dict_rules[ele.Name] = ele.Id
                with revit.Transaction("Create View Filters"):
                    sel_cat = wndw._categories.SelectedItem["Value"]
                    sel_par = wndw._list_box1.SelectedItem["Value"]
                    parameter_id = sel_par.rl_par.Id
                    param_storage_type = sel_par.rl_par.StorageType
                    categories = List[DB.ElementId]()
                    categories.Add(sel_cat.cat.Id)
                    solid_fill_id = solid_fill_pattern_id()
                    version = int(HOST_APP.version)
                    items_listbox = wndw.list_box2.Items
                    for i, element in enumerate(items_listbox):
                        item = wndw.list_box2.Items[i]["Value"]
                        # Assign color filled region
                        ogs = DB.OverrideGraphicSettings()
                        base_color = DB.Color(item.n1, item.n2, item.n3)
                        # Get color shades if multiple override types are enabled
                        line_color, foreground_color, background_color = get_color_shades(
                            base_color,
                            apply_line_color,
                            apply_foreground_pattern_color,
                            apply_background_pattern_color,
                        )
                        # Apply line color if enabled (both projection and cut)
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        # Apply foreground pattern color if enabled
                        if apply_foreground_pattern_color:
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        # Apply background pattern color if enabled (Revit 2019+)
                        if apply_background_pattern_color and version >= 2019:
                            ogs.SetSurfaceBackgroundPatternColor(background_color)
                            ogs.SetCutBackgroundPatternColor(background_color)
                            # Set background pattern ID (solid fill) same as foreground
                            if solid_fill_id is not None:
                                ogs.SetSurfaceBackgroundPatternId(solid_fill_id)
                                ogs.SetCutBackgroundPatternId(solid_fill_id)
                        # Get filters apply to view
                        filter_name = (
                            sel_cat.name + " " + sel_par.name + " - " + item.value
                        )
                        filter_name = filter_name.translate(
                            {ord(i): None for i in "{}[]:\\|?/<>*"}
                        )
                        if filter_name in dict_filters or filter_name in dict_rules:
                            if (
                                filter_name in dict_rules
                                and filter_name not in dict_filters
                            ):
                                view.AddFilter(dict_rules[filter_name])
                                view.SetFilterOverrides(dict_rules[filter_name], ogs)
                            else:
                                # Reassign filter
                                view.SetFilterOverrides(dict_filters[filter_name], ogs)
                        else:
                            # Create filter
                            if param_storage_type == DB.StorageType.Double:
                                if item.value == "None" or len(item.values_double) == 0:
                                    equals_rule = (
                                        DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                            parameter_id, "", 0.001
                                        )
                                    )
                                else:
                                    minimo = min(item.values_double)
                                    maximo = max(item.values_double)
                                    avg_values = (maximo + minimo) / 2
                                    equals_rule = (
                                        DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                            parameter_id,
                                            avg_values,
                                            fabs(avg_values - minimo) + 0.001,
                                        )
                                    )
                            elif param_storage_type == DB.StorageType.ElementId:
                                if item.value == "None":
                                    prevalue = DB.ElementId.InvalidElementId
                                else:
                                    prevalue = item.par.AsElementId()
                                equals_rule = (
                                    DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                        parameter_id, prevalue
                                    )
                                )
                            elif param_storage_type == DB.StorageType.Integer:
                                if item.value == "None":
                                    prevalue = 0
                                else:
                                    prevalue = item.par.AsInteger()
                                equals_rule = (
                                    DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                        parameter_id, prevalue
                                    )
                                )
                            elif param_storage_type == DB.StorageType.String:
                                if item.value == "None":
                                    prevalue = ""
                                else:
                                    prevalue = item.value
                                if version > 2023:
                                    equals_rule = (
                                        DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                            parameter_id, prevalue
                                        )
                                    )
                                else:
                                    equals_rule = (
                                        DB.ParameterFilterRuleFactory.CreateEqualsRule(
                                            parameter_id, prevalue, True
                                        )
                                    )
                            else:
                                task2 = UI.TaskDialog("Color Elements by Parameter")
                                task2.MainInstruction = "Creation of filters for this type of parameter is not supported."
                                wndw.TopMost = False
                                task2.Show()
                                wndw.TopMost = True
                                break
                            try:
                                elem_filter = DB.ElementParameterFilter(equals_rule)
                                fltr = DB.ParameterFilterElement.Create(
                                    new_doc, filter_name, categories, elem_filter
                                )
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


class ValuesInfo:
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


class ParameterInfo:
    def __init__(self, param_type, para):
        self.param_type = param_type
        self.rl_par = para
        self.par = para.Definition
        self.name = strip_accents(para.Definition.Name)


class CategoryInfo:
    def __init__(self, category, param):
        self.name = strip_accents(category.Name)
        self.cat = category
        get_elementid_value = get_elementid_value_func()
        self.int_id = get_elementid_value(category.Id)
        self.par = param


class FormCats(Forms.Form):
    def __init__(
        self, categories, ext_ev, uns_ev, s_view, reset_event, ev_legend, ev_filters
    ):
        self.Font = Drawing.Font(
            "Arial", 15, Drawing.FontStyle.Regular, Drawing.GraphicsUnit.Pixel
        )
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
        self.table_data.Rows.Add("Select a Category Here!", 0)
        for key_, value_ in zip(names, self.categs):
            self.table_data.Rows.Add(key_, value_)
        self.out = []
        self._filtered_parameters = []
        self._all_parameters = []
        self.InitializeComponent()

    def InitializeComponent(self):
        self._spr_top = Forms.Label()
        self._categories = Forms.ComboBox()
        self._list_box1 = Forms.ComboBox()
        self.list_box2 = Forms.ListBox()
        self._button_set_colors = Forms.Button()
        self._button_reset_colors = Forms.Button()
        self._button_random_colors = Forms.Button()
        self._button_gradient_colors = Forms.Button()
        self._button_create_legend = Forms.Button()
        self._button_create_view_filters = Forms.Button()
        self._button_save_load_scheme = Forms.Button()
        self._chk_line_color = Forms.CheckBox()
        self._chk_foreground_pattern = Forms.CheckBox()
        self._chk_background_pattern = Forms.CheckBox()
        self._txt_block2 = Forms.Label()
        self._txt_block3 = Forms.Label()
        self._txt_block4 = Forms.Label()
        self._txt_block5 = Forms.Label()
        self._search_label = Forms.Label()
        self._search_box = Forms.TextBox()
        self._lbl_generate_colors = Forms.Label()
        self._lbl_manage_schemes = Forms.Label()
        self._lbl_apply_settings = Forms.Label()
        self.tooltips = Forms.ToolTip()
        self._config = pyrevit_script.get_config()
        self.SuspendLayout()
        # Layout constants
        left_col_x = 12
        left_col_width = 200
        right_col_x = 220
        right_col_width = 200
        row1_y_start = 2
        spacing = 5
        section_margin = 15

        # LEFT COLUMN - Data Selection
        left_y_pos = row1_y_start + section_margin

        # Category label
        self._txt_block2.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block2.Location = Drawing.Point(left_col_x, left_y_pos)
        self._txt_block2.Name = "txtBlock2"
        self._txt_block2.Size = Drawing.Size(left_col_width, 20)
        self._txt_block2.Text = "Category Selection"
        self._txt_block2.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        self.tooltips.SetToolTip(
            self._txt_block2, "Select a category to start coloring."
        )
        left_y_pos += 22

        # RIGHT COLUMN - Actions & Settings (start positioning)
        right_y_pos = row1_y_start + section_margin

        # Section: Manage Schemes
        self._lbl_manage_schemes.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._lbl_manage_schemes.Location = Drawing.Point(right_col_x, right_y_pos)
        self._lbl_manage_schemes.Name = "lbl_manage_schemes"
        self._lbl_manage_schemes.Size = Drawing.Size(right_col_width, 20)
        self._lbl_manage_schemes.Text = "Manage Schemes"
        self._lbl_manage_schemes.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        right_y_pos += 25

        # Category dropdown - align with Save/Load Color Scheme button (adjusted for button border)
        self._categories.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._categories.Location = Drawing.Point(left_col_x, right_y_pos + 2)
        self._categories.Name = "dropDown"
        self._categories.DataSource = self.table_data
        self._categories.DisplayMember = "Key"
        self._categories.Size = Drawing.Size(left_col_width, 21)
        self._categories.DropDownWidth = 150
        self._categories.DropDownStyle = Forms.ComboBoxStyle.DropDownList
        self._categories.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._categories.SelectedIndexChanged += self.update_filter
        self.tooltips.SetToolTip(
            self._categories, "Select a category to start coloring."
        )

        # Save / Load Color Scheme button - align with Category dropdown
        self._button_save_load_scheme.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_save_load_scheme.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_save_load_scheme.Name = "button_save_load_scheme"
        self._button_save_load_scheme.Size = Drawing.Size(right_col_width, 28)
        self._button_save_load_scheme.Text = "Save / Load Color Scheme"
        self._button_save_load_scheme.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_save_load_scheme.UseVisualStyleBackColor = True
        self._button_save_load_scheme.Click += self.save_load_color_scheme
        self.tooltips.SetToolTip(
            self._button_save_load_scheme,
            "Save the current color scheme or load an existing one.",
        )
        right_y_pos += 40

        # Parameters label - align with Generate Colors label
        self._txt_block3.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block3.Location = Drawing.Point(left_col_x, right_y_pos)
        self._txt_block3.Name = "txtBlock3"
        self._txt_block3.Size = Drawing.Size(left_col_width, 20)
        self._txt_block3.Text = "Parameter Selection"
        self._txt_block3.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        self.tooltips.SetToolTip(
            self._txt_block3, "Select a parameter to color elements based on its value."
        )

        # Section: Generate Colors - align with Parameters label
        self._lbl_generate_colors.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._lbl_generate_colors.Location = Drawing.Point(right_col_x, right_y_pos)
        self._lbl_generate_colors.Name = "lbl_generate_colors"
        self._lbl_generate_colors.Size = Drawing.Size(right_col_width, 20)
        self._lbl_generate_colors.Text = "Generate Colors"
        self._lbl_generate_colors.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        right_y_pos += 25

        # Search TextBox - align with Gradient Colors button (adjusted for button border)
        self._search_box.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._search_box.Location = Drawing.Point(left_col_x, right_y_pos + 2)
        self._search_box.Name = "searchBox"
        self._search_box.Size = Drawing.Size(left_col_width, 20)
        self._search_box.Text = "Search parameters..."
        self._search_box.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._search_box.ForeColor = Drawing.Color.Gray
        self._search_box.TextChanged += self.on_search_text_changed
        self._search_box.Enter += self.search_box_enter
        self._search_box.Leave += self.search_box_leave
        self.tooltips.SetToolTip(
            self._search_box, "Type to search and filter parameters."
        )

        # Gradient Colors button - align with Search box
        self._button_gradient_colors.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_gradient_colors.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_gradient_colors.Name = "button_gradient_colors"
        self._button_gradient_colors.Size = Drawing.Size(right_col_width, 28)
        self._button_gradient_colors.Text = "Gradient Colors"
        self._button_gradient_colors.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_gradient_colors.UseVisualStyleBackColor = True
        self._button_gradient_colors.Click += self.button_click_gradient_colors
        self.tooltips.SetToolTip(
            self._button_gradient_colors,
            "Based on the color of the first and last value,\nreassign gradients colors to all values.",
        )
        right_y_pos += 32

        # Parameters dropdown - align with Random Colors button (adjusted for button border)
        self._list_box1.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._list_box1.FormattingEnabled = True
        self._list_box1.DropDownStyle = Forms.ComboBoxStyle.DropDownList
        self._list_box1.Location = Drawing.Point(left_col_x, right_y_pos + 2)
        self._list_box1.Name = "comboBoxParameters"
        self._list_box1.DisplayMember = "Key"
        self._list_box1.Size = Drawing.Size(left_col_width, 21)
        self._list_box1.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._list_box1.SelectedIndexChanged += self.check_item
        self.tooltips.SetToolTip(
            self._list_box1, "Select a parameter to color elements based on its value."
        )

        # Random Colors button - align with Parameters dropdown
        self._button_random_colors.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_random_colors.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_random_colors.Name = "button_random_colors"
        self._button_random_colors.Size = Drawing.Size(right_col_width, 28)
        self._button_random_colors.Text = "Random Colors"
        self._button_random_colors.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_random_colors.UseVisualStyleBackColor = True
        self._button_random_colors.Click += self.button_click_random_colors
        self.tooltips.SetToolTip(
            self._button_random_colors, "Reassign new random colors to all values."
        )
        right_y_pos += 40

        # Values label - align with Apply Settings label
        self._txt_block4.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block4.Location = Drawing.Point(left_col_x, right_y_pos)
        self._txt_block4.Name = "txtBlock4"
        self._txt_block4.Size = Drawing.Size(left_col_width, 20)
        self._txt_block4.Text = "Values Color Assignment"
        self._txt_block4.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        self.tooltips.SetToolTip(
            self._txt_block4, "Reassign colors by clicking on their value."
        )

        # Section: Apply Settings - align with Values label
        self._lbl_apply_settings.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._lbl_apply_settings.Location = Drawing.Point(right_col_x, right_y_pos)
        self._lbl_apply_settings.Name = "lbl_apply_settings"
        self._lbl_apply_settings.Size = Drawing.Size(right_col_width, 20)
        self._lbl_apply_settings.Text = "Apply Settings"
        self._lbl_apply_settings.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Bold)
        right_y_pos += 25

        # Values listbox (will be sized to align with Set Colors button + margin)
        values_listbox_top = right_y_pos
        self.list_box2.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self.list_box2.FormattingEnabled = True
        self.list_box2.HorizontalScrollbar = True
        self.list_box2.Location = Drawing.Point(left_col_x, values_listbox_top)
        self.list_box2.Name = "listBox2"
        self.list_box2.DisplayMember = "Key"
        self.list_box2.DrawMode = Forms.DrawMode.OwnerDrawFixed
        self.list_box2.DrawItem += self.colour_item
        self.list_box2.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self.new_fnt = Drawing.Font(
            self.Font.FontFamily, 9, Drawing.FontStyle.Regular
        )
        g = self.list_box2.CreateGraphics()
        self.list_box2.ItemHeight = int(g.MeasureString("Sample", self.new_fnt).Height)
        # Initial size - will be set properly after form height calculation
        self.list_box2.Size = Drawing.Size(left_col_width, 350)
        self.tooltips.SetToolTip(
            self.list_box2, "Reassign colors by clicking on their value."
        )

        # TextBlock5 - Hidden warning message
        self._txt_block5.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._txt_block5.Location = Drawing.Point(left_col_x, 600)
        self._txt_block5.Name = "txtBlock5"
        self._txt_block5.Size = Drawing.Size(left_col_width + right_col_width, 27)
        self._txt_block5.Text = "*Spaces may require a color scheme in the view."
        self._txt_block5.ForeColor = Drawing.Color.Red
        self._txt_block5.Font = Drawing.Font(self.Font.FontFamily, 8, Drawing.FontStyle.Underline)
        self._txt_block5.Visible = False

        # Checkbox: Line Color
        self._chk_line_color.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._chk_line_color.Location = Drawing.Point(right_col_x, right_y_pos)
        self._chk_line_color.Name = "chk_line_color"
        self._chk_line_color.Size = Drawing.Size(right_col_width, 20)
        self._chk_line_color.Text = "Apply Line Color"
        self._chk_line_color.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._chk_line_color.Checked = self._config.get_option("apply_line_color", False)
        self._chk_line_color.CheckedChanged += self.checkbox_changed
        self.tooltips.SetToolTip(
            self._chk_line_color,
            "When enabled, applies the color to projection line color.",
        )
        right_y_pos += 25

        # Checkbox: Foreground Pattern Color
        self._chk_foreground_pattern.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._chk_foreground_pattern.Location = Drawing.Point(right_col_x, right_y_pos)
        self._chk_foreground_pattern.Name = "chk_foreground_pattern"
        self._chk_foreground_pattern.Size = Drawing.Size(right_col_width, 20)
        self._chk_foreground_pattern.Text = "Apply Foreground Pattern Color"
        self._chk_foreground_pattern.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._chk_foreground_pattern.Checked = self._config.get_option("apply_foreground_pattern_color", True)
        self._chk_foreground_pattern.CheckedChanged += self.checkbox_changed
        self.tooltips.SetToolTip(
            self._chk_foreground_pattern,
            "When enabled, applies the color to surface and cut foreground pattern colors.",
        )
        right_y_pos += 25

        # Checkbox: Background Pattern Color
        self._chk_background_pattern.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._chk_background_pattern.Location = Drawing.Point(right_col_x, right_y_pos)
        self._chk_background_pattern.Name = "chk_background_pattern"
        self._chk_background_pattern.Size = Drawing.Size(right_col_width, 20)
        self._chk_background_pattern.Text = "Apply Background Pattern Color"
        self._chk_background_pattern.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._chk_background_pattern.Checked = self._config.get_option("apply_background_pattern_color", False)
            self._chk_background_pattern.Enabled = True
        else:
            self._chk_background_pattern.Checked = False
            self._chk_background_pattern.Enabled = False
            self._chk_background_pattern.Text += " (Requires Revit 2019 or newer)"
        self._chk_background_pattern.CheckedChanged += self.checkbox_changed
        self.tooltips.SetToolTip(
            self._chk_background_pattern,
            "When enabled, applies the color to surface and cut background pattern colors. Requires Revit 2019 or newer.",
        )
        right_y_pos += 40

        # Create Legend button
        self._button_create_legend.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_create_legend.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_create_legend.Name = "button_create_legend"
        self._button_create_legend.Size = Drawing.Size(right_col_width, 28)
        self._button_create_legend.Text = "Create Legend"
        self._button_create_legend.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_create_legend.UseVisualStyleBackColor = True
        self._button_create_legend.Click += self.button_click_create_legend
        self.tooltips.SetToolTip(
            self._button_create_legend,
            "Create a new legend view for all the values and their colors.",
        )
        right_y_pos += 32

        # Create View Filters button
        self._button_create_view_filters.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_create_view_filters.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_create_view_filters.Name = "button_create_view_filters"
        self._button_create_view_filters.Size = Drawing.Size(right_col_width, 28)
        self._button_create_view_filters.Text = "Create View Filters"
        self._button_create_view_filters.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_create_view_filters.UseVisualStyleBackColor = True
        self._button_create_view_filters.Click += self.button_click_create_view_filters
        self.tooltips.SetToolTip(
            self._button_create_view_filters,
            "Create view filters and rules for all the values and their colors.",
        )
        right_y_pos += 40

        # Reset and Set Colors buttons (grouped under Create View Filters)
        button_width = int((right_col_width - 15) / 2)
        button_spacing = 15

        # Reset button
        self._button_reset_colors.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_reset_colors.Location = Drawing.Point(right_col_x, right_y_pos)
        self._button_reset_colors.Name = "button_reset_colors"
        self._button_reset_colors.Size = Drawing.Size(button_width, 32)
        self._button_reset_colors.Text = "Reset"
        self._button_reset_colors.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_reset_colors.UseVisualStyleBackColor = True
        self._button_reset_colors.Click += self.button_click_reset
        self.tooltips.SetToolTip(
            self._button_reset_colors,
            "Reset the colors in your Revit view to its initial stage.",
        )

        # Set Colors button - Blue with white text
        self._button_set_colors.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._button_set_colors.Location = Drawing.Point(right_col_x + button_width + button_spacing, right_y_pos)
        self._button_set_colors.Name = "button_set_colors"
        self._button_set_colors.Size = Drawing.Size(button_width, 32)
        self._button_set_colors.Text = "Set Colors"
        self._button_set_colors.Font = Drawing.Font(self.Font.FontFamily, 9, Drawing.FontStyle.Regular)
        self._button_set_colors.UseVisualStyleBackColor = False
        blue_color = Drawing.Color.FromArgb(0, 102, 204)
        self._button_set_colors.BackColor = blue_color
        self._button_set_colors.ForeColor = Drawing.Color.White
        self._button_set_colors.FlatStyle = Forms.FlatStyle.Flat
        self._button_set_colors.FlatAppearance.BorderSize = 0
        # Add rounded corners using Region
        import System.Drawing.Drawing2D as Drawing2D
        rounded_path = Drawing2D.GraphicsPath()
        corner_radius = 5
        rounded_path.AddArc(0, 0, corner_radius * 2, corner_radius * 2, 180, 90)
        rounded_path.AddArc(button_width - corner_radius * 2, 0, corner_radius * 2, corner_radius * 2, 270, 90)
        rounded_path.AddArc(button_width - corner_radius * 2, 32 - corner_radius * 2, corner_radius * 2, corner_radius * 2, 0, 90)
        rounded_path.AddArc(0, 32 - corner_radius * 2, corner_radius * 2, corner_radius * 2, 90, 90)
        rounded_path.CloseFigure()
        self._button_set_colors.Region = Drawing.Region(rounded_path)
        self._button_set_colors.Tag = blue_color
        self._button_set_colors.MouseEnter += self.button_mouse_enter
        self._button_set_colors.MouseLeave += self.button_mouse_leave
        self._button_set_colors.Click += self.button_click_set_colors
        self.tooltips.SetToolTip(
            self._button_set_colors,
            "Replace the colors per element in the view.",
        )

        # Calculate form height: Set Colors button bottom + margin + extra margin for values section
        set_colors_bottom = right_y_pos + 32
        bottom_margin = 25
        values_section_bottom_margin = 15
        form_height = set_colors_bottom + bottom_margin + values_section_bottom_margin

        # Calculate values listbox height to align with Set Colors button + margin
        # The listbox should end at the same level as Set Colors button + margin
        values_listbox_bottom = set_colors_bottom + bottom_margin
        values_listbox_height = values_listbox_bottom - values_listbox_top
        if values_listbox_height < 100:
            values_listbox_height = 100  # Minimum height
        self.list_box2.Size = Drawing.Size(left_col_width, values_listbox_height)

        # Form
        self.TopMost = True
        self.ShowInTaskbar = False
        form_width = right_col_x + right_col_width + 12
        self.ClientSize = Drawing.Size(form_width, form_height)
        self.MaximizeBox = 0
        self.MinimizeBox = 0
        self.CenterToScreen()
        self.FormBorderStyle = Forms.FormBorderStyle.Sizable
        self.SizeGripStyle = Forms.SizeGripStyle.Show
        self.ShowInTaskbar = True
        self.MaximizeBox = True
        self.MinimizeBox = True
        self.Controls.Add(self._categories)
        self.Controls.Add(self._txt_block2)
        self.Controls.Add(self._txt_block3)
        self.Controls.Add(self._search_box)
        self.Controls.Add(self._txt_block4)
        self.Controls.Add(self._list_box1)
        self.Controls.Add(self.list_box2)
        self.Controls.Add(self._lbl_generate_colors)
        self.Controls.Add(self._button_gradient_colors)
        self.Controls.Add(self._button_random_colors)
        self.Controls.Add(self._lbl_manage_schemes)
        self.Controls.Add(self._button_save_load_scheme)
        self.Controls.Add(self._lbl_apply_settings)
        self.Controls.Add(self._chk_line_color)
        self.Controls.Add(self._chk_foreground_pattern)
        self.Controls.Add(self._chk_background_pattern)
        self.Controls.Add(self._button_create_legend)
        self.Controls.Add(self._button_create_view_filters)
        self.Controls.Add(self._button_reset_colors)
        self.Controls.Add(self._button_set_colors)
        self.Controls.Add(self._txt_block5)
        self.Name = "Color Elements By Parameter"
        self.Text = "Color Elements By Parameter"
        self.Closing += self.closing_event
        icon_filename = __file__.replace("script.py", "color_splasher.ico")
        if not exists(icon_filename):
            icon_filename = __file__.replace("script.py", "color_splasher.ico")
        self.Icon = Drawing.Icon(icon_filename)
        self.ResumeLayout(False)

    def search_box_enter(self, sender, e):
        """Clear placeholder text when search box gets focus"""
        if self._search_box.Text == "Search parameters...":
            self._search_box.Text = ""
            self._search_box.ForeColor = Drawing.Color.Black

    def search_box_leave(self, sender, e):
        """Restore placeholder text if search box is empty"""
        if self._search_box.Text == "":
            self._search_box.Text = "Search parameters..."
            self._search_box.ForeColor = Drawing.Color.Gray

    def button_mouse_enter(self, sender, e):
        """Lighten button color on hover - only for Set Colors button"""
        if sender == self._button_set_colors and hasattr(sender, 'Tag') and sender.Tag is not None:
            original_color = sender.Tag
            lighter = Drawing.Color.FromArgb(
                min(255, original_color.R + 20),
                min(255, original_color.G + 20),
                min(255, original_color.B + 20)
            )
            sender.BackColor = lighter
            sender.ForeColor = Drawing.Color.White

    def button_mouse_leave(self, sender, e):
        """Restore original button color on leave - only for Set Colors button"""
        if sender == self._button_set_colors and hasattr(sender, 'Tag') and sender.Tag is not None:
            sender.BackColor = sender.Tag
            sender.ForeColor = Drawing.Color.White

    def checkbox_changed(self, sender, e):
        self._config.set_option("apply_line_color", self._chk_line_color.Checked)
        self._config.set_option("apply_foreground_pattern_color", self._chk_foreground_pattern.Checked)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._config.set_option("apply_background_pattern_color", self._chk_background_pattern.Checked)
        pyrevit_script.save_config()

    def button_click_set_colors(self, sender, e):
        if self.list_box2.Items.Count <= 0:
            return
        else:
            self.event.Raise()

    def button_click_reset(self, sender, e):
        self.reset_ev.Raise()

    def button_click_random_colors(self, sender, e):
        try:
            if self._list_box1.SelectedIndex != -1:
                sel_index = self._list_box1.SelectedIndex
                self._list_box1.SelectedIndex = -1
                self._list_box1.SelectedIndex = sel_index
        except Exception:
            external_event_trace()

    def button_click_gradient_colors(self, sender, e):
        self.list_box2.SelectedIndexChanged -= self.list_selected_index_changed
        try:
            list_values = []
            number_items = len(self.list_box2.Items)
            if number_items <= 2:
                return
            else:
                start_color = self.list_box2.Items[0]["Value"].colour
                end_color = self.list_box2.Items[number_items - 1]["Value"].colour
                list_colors = self.get_gradient_colors(
                    start_color, end_color, number_items
                )
                for indx, item in enumerate(self.list_box2.Items):
                    value = item["Value"]
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
                sender.SelectedItem["Value"].n1 = clr_dlg.Color.R
                sender.SelectedItem["Value"].n2 = clr_dlg.Color.G
                sender.SelectedItem["Value"].n3 = clr_dlg.Color.B
                sender.SelectedItem["Value"].colour = Drawing.Color.FromArgb(
                    clr_dlg.Color.R, clr_dlg.Color.G, clr_dlg.Color.B
                )
            self.list_box2.SelectedIndex = -1

    def colour_item(self, sender, e):
        try:
            cnt = e.Index
            g = e.Graphics
            text_device = sender.Items[e.Index]["Key"]
            color = sender.Items[e.Index]["Value"].colour
            if cnt == self.list_box2.SelectedIndex or color == Drawing.Color.FromArgb(
                Drawing.Color.White.R, Drawing.Color.White.G, Drawing.Color.White.B
            ):
                color = Drawing.Color.White
                font_color = Drawing.Color.Black
            else:
                font_color = Drawing.Color.White
            wdth = g.MeasureString(text_device, self.new_fnt).Width + 30
            if self.list_box2.Width < wdth and self.list_box2.HorizontalExtent < wdth:
                self.list_box2.HorizontalExtent = wdth
            e.DrawBackground()
            g.FillRectangle(Drawing.SolidBrush(color), e.Bounds)
            Forms.TextRenderer.DrawText(
                g,
                text_device,
                self.new_fnt,
                e.Bounds,
                font_color,
                Forms.TextFormatFlags.Left,
            )
            e.DrawFocusRectangle()
        except Exception:
            external_event_trace()

    def check_item(self, sender, e):
        try:
            self.list_box2.SelectedIndexChanged -= self.list_selected_index_changed
        except Exception:
            external_event_trace()
        sel_cat = self._categories.SelectedItem["Value"]
        if sel_cat is None or sel_cat == 0:
            return
        if sender.SelectedIndex == -1:
            self._table_data_3 = DataTable("Data")
            self._table_data_3.Columns.Add("Key", System.String)
            self._table_data_3.Columns.Add("Value", System.Object)
            self.list_box2.DataSource = self._table_data_3
            self.list_box2.DisplayMember = "Key"
            return
        sel_param = sender.SelectedItem["Value"]
        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)
        rng_val = get_range_values(sel_cat, sel_param, self.crt_view)
        vl_par = [x.value for x in rng_val]
        g = self.list_box2.CreateGraphics()
        if len(vl_par) != 0:
            width = [
                int(g.MeasureString(x, self.list_box2.Font).Width) for x in vl_par
            ]
            self.list_box2.HorizontalExtent = max(width) + 50
        for key_, value_ in zip(vl_par, rng_val):
            self._table_data_3.Rows.Add(key_, value_)
        self.list_box2.DataSource = self._table_data_3
        self.list_box2.DisplayMember = "Key"
        self.list_box2.SelectedIndex = -1
        self.list_box2.SelectedIndexChanged += self.list_selected_index_changed

    def update_filter(self, sender, e):
        # Update param listbox
        sel_cat = sender.SelectedItem["Value"]
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
            self._all_parameters = [
                (key_, value_) for key_, value_ in zip(names_par, sel_cat.par)
            ]
            self._list_box1.DataSource = self._table_data_2
            self._list_box1.DisplayMember = "Key"
            self._list_box1.SelectedIndex = -1
            self._search_box.Text = ""
            self.list_box2.DataSource = self._table_data_3
        else:
            self._all_parameters = []
            self._list_box1.DataSource = self._table_data_2
            self.list_box2.DataSource = self._table_data_3

    def on_search_text_changed(self, sender, e):
        """Filter parameters based on search text"""
        # Skip filtering if placeholder text is shown
        if self._search_box.Text == "Search parameters...":
            return
        search_text = self._search_box.Text.lower()

        # Create new filtered data table
        filtered_table = DataTable("Data")
        filtered_table.Columns.Add("Key", System.String)
        filtered_table.Columns.Add("Value", System.Object)

        # Filter parameters based on search text
        if len(self._all_parameters) > 0:
            for key_, value_ in self._all_parameters:
                if search_text == "" or search_text in key_.lower():
                    filtered_table.Rows.Add(key_, value_)

        # Store current selected item
        selected_item_value = None
        if self._list_box1.SelectedIndex != -1 and self._list_box1.SelectedIndex < len(self._list_box1.Items):
            selected_item_value = self._list_box1.SelectedItem["Value"]

        # Update data source
        self._list_box1.DataSource = filtered_table
        self._list_box1.DisplayMember = "Key"

        # Restore selected item if it's still visible
        if selected_item_value is not None:
            for indx in range(self._list_box1.Items.Count):
                if self._list_box1.Items[indx]["Value"] == selected_item_value:
                    self._list_box1.SelectedIndex = indx
                    break


class FormSaveLoadScheme(Forms.Form):
    def __init__(self):
        self.Font = Drawing.Font(
            self.Font.FontFamily,
            9,
            Drawing.FontStyle.Regular,
            Drawing.GraphicsUnit.Pixel,
        )
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
        self._spr_top.Anchor = (
            Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        )
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
        self.tooltip1.SetToolTip(
            self._radio_by_value,
            "Only if loading. This will load the color scheme based on the Value the item had when saving.",
        )
        # Radio by Pos
        self._radio_by_pos.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._radio_by_pos.Location = Drawing.Point(250, 35)
        self._radio_by_pos.Text = "Load by Position in Window."
        self._radio_by_pos.Name = "_radio_byValue"
        self._radio_by_pos.Size = Drawing.Size(239, 25)
        self.tooltip1.SetToolTip(
            self._radio_by_pos,
            "Only if loading. This will load the color scheme based on the Position the item had when saving.",
        )
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
        icon_filename = __file__.replace("script.py", "color_splasher.ico")
        if not exists(icon_filename):
            icon_filename = __file__.replace("script.py", "color_splasher.ico")
        self.Icon = Drawing.Icon(icon_filename)
        self.ResumeLayout(False)

    def specify_path_save(self, sender, e):
        # Prompt save file dialog and its configuration.
        with Forms.SaveFileDialog() as save_file_dialog:
            save_file_dialog.Title = "Specify Path to Save Color Scheme"
            save_file_dialog.Filter = "Color Scheme (*.cschn)|*.cschn"
            save_file_dialog.RestoreDirectory = True
            save_file_dialog.OverwritePrompt = True
            save_file_dialog.InitialDirectory = System.Environment.GetFolderPath(
                System.Environment.SpecialFolder.Desktop
            )
            save_file_dialog.FileName = "Color Scheme.cschn"
            wndw = getattr(FormCats, '_current_wndw', None)
            if not wndw or len(wndw.list_box2.Items) == 0:
                if wndw:
                    wndw.Hide()
                self.Hide()
                UI.TaskDialog.Show(
                    "No Colors Detected",
                    "The list of values in the main window is empty. Please, select a category and parameter to add items with colors.",
                )
                if wndw:
                    wndw.Show()
                self.Close()
            elif save_file_dialog.ShowDialog() == Forms.DialogResult.OK:
                # Main path for new file
                self.save_path_to_file(save_file_dialog.FileName)
                self.Close()

    def save_path_to_file(self, new_path):
        try:
            wndw = getattr(FormCats, '_current_wndw', None)
            if not wndw:
                return
            # Save location selected in save file dialog.
            with open(new_path, "w") as file:
                for item in wndw.list_box2.Items:
                    color_inst = item["Value"].colour
                    file.write(
                        item["Key"]
                        + "::R"
                        + str(color_inst.R)
                        + "G"
                        + str(color_inst.G)
                        + "B"
                        + str(color_inst.B)
                        + "\n"
                    )
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
            open_file_dialog.InitialDirectory = System.Environment.GetFolderPath(
                System.Environment.SpecialFolder.Desktop
            )
            wndw = getattr(FormCats, '_current_wndw', None)
            if not wndw or len(wndw.list_box2.Items) == 0:
                if wndw:
                    wndw.Hide()
                self.Hide()
                UI.TaskDialog.Show(
                    "No Values Detected",
                    "The list of values in the main window is empty. Please, select a category and parameter to add items to apply colors.",
                )
                if wndw:
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
            wndw = getattr(FormCats, '_current_wndw', None)
            if not wndw:
                return
            # Load last location selected in save file dialog.
            try:
                with open(path, "r") as file:
                    all_lines = file.readlines()
                    if self._radio_by_value.Checked:
                        for line in all_lines:
                            line_val = line.strip().split("::R")
                            par_val = line_val[0]
                            rgb_result = split(r"[RGB]", line_val[1])
                            for item in wndw._table_data_3.Rows:
                                if item["Key"] == par_val:
                                    self.apply_color_to_item(rgb_result, item)
                                    break
                    else:
                        for ind, line in enumerate(all_lines):
                            if ind < len(wndw._table_data_3.Rows):
                                line_val = line.strip().split("::R")
                                par_val = line_val[0]
                                rgb_result = split(r"[RGB]", line_val[1])
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
        item["Value"].n1 = r
        item["Value"].n2 = g
        item["Value"].n3 = b
        item["Value"].colour = Drawing.Color.FromArgb(r, g, b)


def get_active_view(ac_doc):
    uidoc = HOST_APP.uiapp.ActiveUIDocument
    wndw = getattr(SubscribeView, '_wndw', None)
    selected_view = ac_doc.ActiveView
    if (
        selected_view.ViewType == DB.ViewType.ProjectBrowser
        or selected_view.ViewType == DB.ViewType.SystemBrowser
    ):
        selected_view = ac_doc.GetElement(uidoc.GetOpenUIViews()[0].ViewId)
    if not selected_view.CanUseTemporaryVisibilityModes():
        task2 = UI.TaskDialog("Color Elements by Parameter")
        task2.MainInstruction = (
            "Visibility settings cannot be modified in "
            + str(selected_view.ViewType)
            + " views. Please, change your current view."
        )
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


def get_elementid_value(para, doc_param=None):
    # Use provided doc parameter, or get from Revit context directly
    if doc_param is None:
        doc_param = revit.DOCS.doc
    id_val = para.AsElementId()
    elementid_value = get_elementid_value_func()
    if elementid_value(id_val) >= 0:
        return DB.Element.Name.GetValue(doc_param.GetElement(id_val))
    else:
        return "None"


def get_integer_value(para):
    version = int(HOST_APP.version)
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
    return "".join(
        char for char in normalize("NFKD", text) if unicode_category(char) != "Mn"
    )


def random_color():
    r = randint(0, 230)
    g = randint(0, 230)
    b = randint(0, 230)
    return r, g, b


def get_range_values(category, param, new_view):
    # Get document from view (views always have Document property)
    doc_param = new_view.Document
    for sample_bic in System.Enum.GetValues(DB.BuiltInCategory):
        if category.int_id == int(sample_bic):
            bic = sample_bic
            break
    collector = (
        DB.FilteredElementCollector(doc_param, new_view.Id)
        .OfCategory(bic)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
        .ToElements()
    )
    list_values = []
    used_colors = {(x.n1, x.n2, x.n3) for x in list_values}
    for ele in collector:
        ele_par = ele if param.param_type != 1 else doc_param.GetElement(ele.GetTypeId())
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
                list_values = sorted(
                    list_values, key=lambda x: safe_float(x.value[:-indx_del])
                )
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
        return float("inf")  # Place non-numeric values at the end


def get_used_categories_parameters(cat_exc, acti_view, doc_param=None):
    # Use provided doc parameter, or get from view (views always have Document property)
    try:
        if doc_param is None:
            doc_param = acti_view.Document
    except (AttributeError, RuntimeError):
        # Fallback to Revit context if view doesn't have Document
        doc_param = revit.DOCS.doc
    # Get All elements and filter unneeded
    collector = (
        DB.FilteredElementCollector(doc_param, acti_view.Id)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
        .ToElements()
    )
    list_cat = []
    for ele in collector:
        if ele.Category is None:
            continue
        # Use the function from compat, not the global-scoped function
        elementid_value_getter = get_elementid_value_func()
        current_int_cat_id = elementid_value_getter(ele.Category.Id)
        if (
            current_int_cat_id in cat_exc
            or current_int_cat_id >= -1
            or any(x.int_id == current_int_cat_id for x in list_cat)
        ):
            continue
        list_parameters = []
        # Instance parameters
        for par in ele.Parameters:
            if par.Definition.BuiltInParameter not in (
                DB.BuiltInParameter.ELEM_CATEGORY_PARAM,
                DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT,
            ):
                list_parameters.append(ParameterInfo(0, par))
        typ = ele.Document.GetElement(ele.GetTypeId())
        # Type parameters
        if typ:
            for par in typ.Parameters:
                if par.Definition.BuiltInParameter not in (
                    DB.BuiltInParameter.ELEM_CATEGORY_PARAM,
                    DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT,
                    ):
                    list_parameters.append(ParameterInfo(1, par))
        # Sort and add
        list_parameters = sorted(
            list_parameters, key=lambda x: x.name.upper()
        )
        list_cat.append(CategoryInfo(ele.Category, list_parameters))
    list_cat = sorted(list_cat, key=lambda x: x.name)
    return list_cat


def solid_fill_pattern_id():
    # Get document directly from Revit context
    doc_param = revit.DOCS.doc
    solid_fill_id = None
    fillpatterns = DB.FilteredElementCollector(doc_param).OfClass(DB.FillPatternElement)
    for pat in fillpatterns:
        if pat.GetFillPattern().IsSolidFill:
            solid_fill_id = pat.Id
            break
    return solid_fill_id


def external_event_trace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    logger.debug("Exception type: %s", exc_type)
    logger.debug("Exception value: %s", exc_value)
    logger.debug("Traceback details:")
    for tb in extract_tb(exc_traceback):
        logger.debug(
            "File: %s, Line: %s, Function: %s, Code: %s", tb[0], tb[1], tb[2], tb[3]
        )


def get_index_units(str_value):
    for let in str_value[::-1]:
        if let.isdigit():
            return str_value[::-1].index(let)
    return -1


def get_color_shades(base_color, apply_line, apply_foreground, apply_background):
    """
    Generate different shades of the base color when multiple override types are enabled.
    Returns tuple: (line_color, foreground_color, background_color)
    Foreground and background always use the full base color to match UI swatches.
    Only line color is faded when used with other types.
    """
    r, g, b = base_color.Red, base_color.Green, base_color.Blue

    foreground_color = base_color
    background_color = base_color


    # Line color is faded when used with other types, otherwise uses base color
    if apply_line and (apply_foreground or apply_background):
        # When line is used with pattern colors, make line color more faded
        line_r = max(0, min(255, int(r + (255 - r) * 0.6)))
        line_g = max(0, min(255, int(g + (255 - g) * 0.6)))
        line_b = max(0, min(255, int(b + (255 - b) * 0.6)))
        # Further desaturate by mixing with gray
        gray = (line_r + line_g + line_b) / 3
        line_r = int(line_r * 0.7 + gray * 0.3)
        line_g = int(line_g * 0.7 + gray * 0.3)
        line_b = int(line_b * 0.7 + gray * 0.3)
        line_color = DB.Color(line_r, line_g, line_b)
    else:
        # When line is used alone, use base color
        line_color = base_color

    return line_color, foreground_color, background_color


def launch_color_splasher():
    """Main entry point for Color Splasher tool."""
    try:
        doc = revit.DOCS.doc
        if doc is None:
            raise AttributeError("Revit document is not available")
    except (AttributeError, RuntimeError, Exception):
        error_msg = UI.TaskDialog("Color Splasher Error")
        error_msg.MainInstruction = "Unable to access Revit document"
        error_msg.MainContent = "Please ensure you have a Revit project open and try again."
        error_msg.Show()
        return

    sel_view = get_active_view(doc)
    if sel_view != 0:
        categ_inf_used = get_used_categories_parameters(CAT_EXCLUDED, sel_view, doc)
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

        wndw = FormCats(
            categ_inf_used,
            ext_event,
            ext_event_uns,
            sel_view,
            ext_event_reset,
            ext_event_legend,
            ext_event_filters,
        )
        wndw._categories.SelectedIndex = -1
        wndw.Show()

        # Store wndw reference for event handlers
        SubscribeView._wndw = wndw
        ApplyColors._wndw = wndw
        ResetColors._wndw = wndw
        CreateLegend._wndw = wndw
        CreateFilters._wndw = wndw
        FormCats._current_wndw = wndw


if __name__ == "__main__":
    launch_color_splasher()
