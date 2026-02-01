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
from pyrevit import forms
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
                        try:
                            current_doc = revit.DOCS.doc
                            if not new_doc.Equals(current_doc):
                                wndw.Close()
                        except (AttributeError, RuntimeError):
                            # If we can't get current doc, continue without closing window
                            pass
                new_view = get_active_view(e.Document)
                if new_view != 0:
                    wndw.list_box2.SelectionChanged -= wndw.list_selected_index_changed
                    wndw.crt_view = new_view
                    categ_inf_used_up = get_used_categories_parameters(
                        CAT_EXCLUDED, wndw.crt_view, new_doc
                    )
                    wndw.table_data = DataTable("Data")
                    wndw.table_data.Columns.Add("Key", System.String)
                    wndw.table_data.Columns.Add("Value", System.Object)
                    names = [x.name for x in categ_inf_used_up]
                    select_category_text = wndw.get_locale_string(
                        "ColorSplasher.Messages.SelectCategory"
                    )
                    wndw.table_data.Rows.Add(select_category_text, 0)
                    for key_, value_ in zip(names, categ_inf_used_up):
                        wndw.table_data.Rows.Add(key_, value_)
                    wndw._categories.ItemsSource = wndw.table_data.DefaultView
                    if wndw._categories.Items.Count > 0:
                        wndw._categories.SelectedIndex = 0
                    wndw._table_data_3 = DataTable("Data")
                    wndw._table_data_3.Columns.Add("Key", System.String)
                    wndw._table_data_3.Columns.Add("Value", System.Object)
                    wndw.list_box2.ItemsSource = wndw._table_data_3.DefaultView
                    wndw._update_placeholder_visibility()

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
            apply_line_color = wndw._chk_line_color.IsChecked
            apply_foreground_pattern_color = wndw._chk_foreground_pattern.IsChecked
            apply_background_pattern_color = wndw._chk_background_pattern.IsChecked
            if (
                not apply_line_color
                and not apply_foreground_pattern_color
                and not apply_background_pattern_color
            ):
                apply_foreground_pattern_color = True
            solid_fill_id = solid_fill_pattern_id()

            if wndw._categories.SelectedItem is None:
                return
            sel_cat_row = wndw._categories.SelectedItem
            row = wndw._get_data_row_from_item(
                sel_cat_row, wndw._categories.SelectedIndex
            )
            if row is None:
                return
            sel_cat = row["Value"]
            if sel_cat == 0:
                return

            if (
                wndw._list_box1.SelectedIndex == -1
                or wndw._list_box1.SelectedIndex == 0
            ):
                if wndw._list_box1.SelectedIndex == 0:
                    sel_param_row = wndw._list_box1.SelectedItem
                    if sel_param_row is not None:
                        param_row = wndw._get_data_row_from_item(sel_param_row, 0)
                        if param_row is not None and param_row["Value"] == 0:
                            return
                return
            sel_param_row = wndw._list_box1.SelectedItem
            param_row = wndw._get_data_row_from_item(
                sel_param_row, wndw._list_box1.SelectedIndex
            )
            if param_row is None:
                return
            checked_param = param_row["Value"]

            refreshed_values = get_range_values(sel_cat, checked_param, view)

            color_map = {}
            for indx in range(wndw.list_box2.Items.Count):
                try:
                    item = wndw.list_box2.Items[indx]
                    row = wndw._get_data_row_from_item(item, indx)
                    if row is None:
                        continue
                    value_item = row["Value"]
                    color_map[value_item.value] = (
                        value_item.n1,
                        value_item.n2,
                        value_item.n3,
                    )
                except (KeyError, AttributeError, IndexError) as ex:
                    logger.debug("Error accessing listbox item %d: %s", indx, str(ex))
                    continue

            with revit.Transaction("Apply colors to elements"):
                get_elementid_value = get_elementid_value_func()
                version = int(HOST_APP.version)
                if get_elementid_value(sel_cat.cat.Id) in (
                    int(DB.BuiltInCategory.OST_Rooms),
                    int(DB.BuiltInCategory.OST_MEPSpaces),
                    int(DB.BuiltInCategory.OST_Areas),
                ):
                    if version > 2021:
                        if (
                            wndw.crt_view.GetColorFillSchemeId(
                                sel_cat.cat.Id
                            ).ToString()
                            == "-1"
                        ):
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
                        from System.Windows import Visibility

                        wndw._txt_block5.Visibility = Visibility.Visible
                else:
                    from System.Windows import Visibility

                    wndw._txt_block5.Visibility = Visibility.Collapsed

                for val_info in refreshed_values:
                    if val_info.value in color_map:
                        ogs = DB.OverrideGraphicSettings()
                        r, g, b = color_map[val_info.value]
                        base_color = DB.Color(r, g, b)
                        line_color, foreground_color, background_color = (
                            get_color_shades(
                                base_color,
                                apply_line_color,
                                apply_foreground_pattern_color,
                                apply_background_pattern_color,
                            )
                        )
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        if apply_foreground_pattern_color:
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        if apply_background_pattern_color and version >= 2019:
                            ogs.SetSurfaceBackgroundPatternColor(background_color)
                            ogs.SetCutBackgroundPatternColor(background_color)
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
            if wndw._categories.SelectedItem is None:
                sel_cat = 0
            else:
                sel_cat_row = wndw._categories.SelectedItem
                if hasattr(sel_cat_row, "Row"):
                    sel_cat = sel_cat_row.Row["Value"]
                else:
                    sel_cat = wndw._categories.SelectedItem["Value"]
            if sel_cat == 0:
                task_no_cat = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                task_no_cat.MainInstruction = wndw.get_locale_string(
                    "ColorSplasher.Messages.NoCategorySelected"
                )
                wndw.Topmost = False
                task_no_cat.Show()
                wndw.Topmost = True
                return
            with revit.Transaction("Reset colors in elements"):
                try:
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
            apply_line_color = wndw._chk_line_color.IsChecked
            apply_foreground_pattern_color = wndw._chk_foreground_pattern.IsChecked
            apply_background_pattern_color = wndw._chk_background_pattern.IsChecked
            if (
                not apply_line_color
                and not apply_foreground_pattern_color
                and not apply_background_pattern_color
            ):
                apply_foreground_pattern_color = True
            collector = (
                DB.FilteredElementCollector(new_doc).OfClass(DB.View).ToElements()
            )
            legends = []
            for vw in collector:
                if vw.ViewType == DB.ViewType.Legend:
                    legends.append(vw)
                    break

            if len(legends) == 0:
                task2 = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                task2.MainInstruction = wndw.get_locale_string(
                    "ColorSplasher.Messages.NoLegendView"
                )
                wndw.Topmost = False
                task2.Show()
                wndw.Topmost = True
                return

            if wndw.list_box2.Items.Count == 0:
                task2 = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                task2.MainInstruction = wndw.get_locale_string(
                    "ColorSplasher.Messages.NoItemsForLegend"
                )
                wndw.Topmost = False
                task2.Show()
                wndw.Topmost = True
                return

            t = DB.Transaction(new_doc, "Create Legend")
            t.Start()

            try:
                new_id_legend = legends[0].Duplicate(DB.ViewDuplicateOption.Duplicate)
                new_legend = new_doc.GetElement(new_id_legend)
                sel_cat_row = wndw._categories.SelectedItem
                sel_par_row = wndw._list_box1.SelectedItem
                cat_row = wndw._get_data_row_from_item(
                    sel_cat_row, wndw._categories.SelectedIndex
                )
                par_row = wndw._get_data_row_from_item(
                    sel_par_row, wndw._list_box1.SelectedIndex
                )
                if cat_row is None or par_row is None:
                    return
                sel_cat = cat_row["Value"]
                sel_par = par_row["Value"]
                cat_name = strip_accents(sel_cat.name)
                par_name = strip_accents(sel_par.name)
                renamed = False
                legend_prefix = wndw.get_locale_string("ColorSplasher.LegendNamePrefix")
                try:
                    new_legend.Name = legend_prefix + cat_name + " - " + par_name
                    renamed = True
                except Exception:
                    external_event_trace()
                if not renamed:
                    for i in range(1000):
                        try:
                            new_legend.Name = (
                                legend_prefix
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
                solid_fill_id = (
                    solid_fill_pattern_id() if apply_foreground_pattern_color else None
                )
                for indx, y in enumerate(list_y):
                    try:
                        vw_item = wndw.list_box2.Items[indx]
                        row = wndw._get_data_row_from_item(vw_item, indx)
                        if row is None:
                            continue
                        item = row["Value"]
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
                        line_color, foreground_color, background_color = (
                            get_color_shades(
                                base_color,
                                apply_line_color,
                                apply_foreground_pattern_color,
                                apply_background_pattern_color,
                            )
                        )
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        if apply_foreground_pattern_color:
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        elif apply_background_pattern_color:
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

                task2 = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                success_msg = wndw.get_locale_string(
                    "ColorSplasher.Messages.LegendCreated"
                )
                task2.MainInstruction = success_msg.replace("{0}", new_legend.Name)
                wndw.Topmost = False
                task2.Show()
                wndw.Topmost = True

            except Exception as e:
                if t.HasStarted() and not t.HasEnded():
                    t.RollBack()

                logger.debug("Legend creation failed: %s", str(e))
                task2 = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                error_msg = wndw.get_locale_string(
                    "ColorSplasher.Messages.LegendFailed"
                )
                task2.MainInstruction = error_msg.replace("{0}", str(e))
                wndw.Topmost = False
                task2.Show()
                wndw.Topmost = True
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
                apply_line_color = wndw._chk_line_color.IsChecked
                apply_foreground_pattern_color = wndw._chk_foreground_pattern.IsChecked
                apply_background_pattern_color = wndw._chk_background_pattern.IsChecked
                if (
                    not apply_line_color
                    and not apply_foreground_pattern_color
                    and not apply_background_pattern_color
                ):
                    apply_foreground_pattern_color = True
                dict_filters = {}
                for filt_id in view.GetFilters():
                    filter_ele = new_doc.GetElement(filt_id)
                    dict_filters[filter_ele.Name] = filt_id
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
                    sel_cat_row = wndw._categories.SelectedItem
                    sel_par_row = wndw._list_box1.SelectedItem
                    cat_row = wndw._get_data_row_from_item(
                        sel_cat_row, wndw._categories.SelectedIndex
                    )
                    par_row = wndw._get_data_row_from_item(
                        sel_par_row, wndw._list_box1.SelectedIndex
                    )
                    if cat_row is None or par_row is None:
                        return
                    sel_cat = cat_row["Value"]
                    sel_par = par_row["Value"]
                    parameter_id = sel_par.rl_par.Id
                    param_storage_type = sel_par.rl_par.StorageType
                    categories = List[DB.ElementId]()
                    categories.Add(sel_cat.cat.Id)
                    solid_fill_id = solid_fill_pattern_id()
                    version = int(HOST_APP.version)
                    items_listbox = wndw.list_box2.Items
                    for i in range(items_listbox.Count):
                        vw_item = wndw.list_box2.Items[i]
                        row = wndw._get_data_row_from_item(vw_item, i)
                        if row is None:
                            continue
                        item = row["Value"]
                        ogs = DB.OverrideGraphicSettings()
                        base_color = DB.Color(item.n1, item.n2, item.n3)
                        line_color, foreground_color, background_color = (
                            get_color_shades(
                                base_color,
                                apply_line_color,
                                apply_foreground_pattern_color,
                                apply_background_pattern_color,
                            )
                        )
                        if apply_line_color:
                            ogs.SetProjectionLineColor(line_color)
                            ogs.SetCutLineColor(line_color)
                        if apply_foreground_pattern_color:
                            ogs.SetSurfaceForegroundPatternColor(foreground_color)
                            ogs.SetCutForegroundPatternColor(foreground_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                                ogs.SetCutForegroundPatternId(solid_fill_id)
                        if apply_background_pattern_color and version >= 2019:
                            ogs.SetSurfaceBackgroundPatternColor(background_color)
                            ogs.SetCutBackgroundPatternColor(background_color)
                            if solid_fill_id is not None:
                                ogs.SetSurfaceBackgroundPatternId(solid_fill_id)
                                ogs.SetCutBackgroundPatternId(solid_fill_id)
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
                                view.SetFilterOverrides(dict_filters[filter_name], ogs)
                        else:
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
                                task2 = UI.TaskDialog(
                                    wndw.get_locale_string(
                                        "ColorSplasher.TaskDialog.Title"
                                    )
                                )
                                task2.MainInstruction = wndw.get_locale_string(
                                    "ColorSplasher.Messages.FilterNotSupported"
                                )
                                wndw.Topmost = False
                                task2.Show()
                                wndw.Topmost = True
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
                                task2 = UI.TaskDialog(
                                    wndw.get_locale_string(
                                        "ColorSplasher.TaskDialog.Title"
                                    )
                                )
                                task2.MainInstruction = wndw.get_locale_string(
                                    "ColorSplasher.Messages.FilterCreationFailed"
                                )
                                wndw.Topmost = False
                                task2.Show()
                                wndw.Topmost = True
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


class ColorSplasherWindow(forms.WPFWindow):
    def __init__(
        self,
        xaml_file_name,
        categories,
        ext_ev,
        uns_ev,
        s_view,
        reset_event,
        ev_legend,
        ev_filters,
    ):
        forms.WPFWindow.__init__(self, xaml_file_name)
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
        select_category_text = self.get_locale_string(
            "ColorSplasher.Messages.SelectCategory"
        )
        self.table_data.Rows.Add(select_category_text, 0)
        for key_, value_ in zip(names, self.categs):
            self.table_data.Rows.Add(key_, value_)
        self.out = []
        self._filtered_parameters = []
        self._all_parameters = []
        self._config = pyrevit_script.get_config()

        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)

        self.Closed += self.closed
        pyrevit_script.restore_window_position(self)

        self._setup_ui()

    def closed(self, sender, args):
        pyrevit_script.save_window_position(self)

    def _get_data_row_from_item(self, item, item_index=None):
        """Get DataRow from ListBox item consistently.

        Args:
            item: ListBox item (DataRowView or other)
            item_index: Optional index for fallback access

        Returns:
            DataRow or None if not accessible
        """
        from System.Data import DataRowView

        if isinstance(item, DataRowView):
            return item.Row
        elif hasattr(item, "Row"):
            return item.Row
        elif (
            item_index is not None
            and hasattr(self, "_table_data_3")
            and self._table_data_3 is not None
        ):
            if item_index < self._table_data_3.Rows.Count:
                return self._table_data_3.Rows[item_index]
        return None

    def _update_placeholder_visibility(self):
        """Update placeholder text visibility based on list_box2 item count."""
        from System.Windows import Visibility

        if self.list_box2.ItemsSource is None or self.list_box2.Items.Count == 0:
            self._txt_placeholder_values.Visibility = Visibility.Visible
        else:
            self._txt_placeholder_values.Visibility = Visibility.Collapsed

    def _setup_ui(self):
        """Initialize UI controls after XAML is loaded."""
        placeholder_text = self.get_locale_string(
            "ColorSplasher.Placeholders.SearchParameters"
        )
        self._search_box.Text = placeholder_text
        from System.Windows.Media import Brushes

        self._search_box.Foreground = Brushes.Gray

        self._categories.ItemsSource = self.table_data.DefaultView
        self._categories.SelectionChanged += self.update_filter
        self._categories.SelectedIndex = 0

        self._chk_line_color.IsChecked = self._config.get_option(
            "apply_line_color", False
        )
        self._chk_foreground_pattern.IsChecked = self._config.get_option(
            "apply_foreground_pattern_color", True
        )

        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._chk_background_pattern.IsChecked = self._config.get_option(
                "apply_background_pattern_color", False
            )
            self._chk_background_pattern.IsEnabled = True
        else:
            self._chk_background_pattern.IsChecked = False
            self._chk_background_pattern.IsEnabled = False
            bg_pattern_text = self.get_locale_string(
                "ColorSplasher.Checkboxes.ApplyBackgroundPattern.RequiresRevit2019"
            )
            self._chk_background_pattern.Content = bg_pattern_text

        self.list_box2.SelectionChanged += self.list_selected_index_changed
        self.list_box2.MouseDown += self.list_box2_mouse_down
        self._shift_pressed_on_click = False

        self.list_box2.ItemsSource = self._table_data_3.DefaultView
        self._update_placeholder_visibility()

        if not hasattr(self, "_table_data_2") or self._table_data_2 is None:
            self._table_data_2 = DataTable("Data")
            self._table_data_2.Columns.Add("Key", System.String)
            self._table_data_2.Columns.Add("Value", System.Object)
            select_parameter_text = self.get_locale_string(
                "ColorSplasher.Messages.SelectParameter"
            )
            self._table_data_2.Rows.Add(select_parameter_text, 0)
            self._list_box1.ItemsSource = self._table_data_2.DefaultView
            self._list_box1.SelectedIndex = 0

        try:
            from System.Windows.Controls import ScrollViewer

            ScrollViewer.SetHorizontalScrollBarVisibility(
                self.list_box2, System.Windows.Controls.ScrollBarVisibility.Auto
            )
        except Exception as exc:
            # Best-effort: if scrollbar configuration fails, continue without breaking the UI  
            get_logger(__name__).debug(  
                "Failed to set horizontal scrollbar visibility for ColorSplasher list_box2.",  
                exc_info=exc,  
            )
            pass

        self.Closing += self.closing_event

        icon_filename = __file__.replace("script.py", "color_splasher.ico")
        if exists(icon_filename):
            try:
                self.Icon = Drawing.Icon(icon_filename)
            except Exception:
                # Icon loading is optional, continue if it fails
                pass

    def search_box_enter(self, sender, e):
        """Clear placeholder text when search box gets focus"""
        from System.Windows.Media import Brushes

        placeholder_text = self.get_locale_string(
            "ColorSplasher.Placeholders.SearchParameters"
        )
        if self._search_box.Text == placeholder_text:
            self._search_box.Text = ""
            self._search_box.Foreground = Brushes.Black

    def search_box_leave(self, sender, e):
        """Restore placeholder text if search box is empty"""
        from System.Windows.Media import Brushes

        placeholder_text = self.get_locale_string(
            "ColorSplasher.Placeholders.SearchParameters"
        )
        if self._search_box.Text == "":
            self._search_box.Text = placeholder_text
            self._search_box.Foreground = Brushes.Gray

    def checkbox_changed(self, sender, e):
        """Handle checkbox state changes"""
        self._config.set_option("apply_line_color", self._chk_line_color.IsChecked)
        self._config.set_option(
            "apply_foreground_pattern_color", self._chk_foreground_pattern.IsChecked
        )
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._config.set_option(
                "apply_background_pattern_color", self._chk_background_pattern.IsChecked
            )
        pyrevit_script.save_config()

    def button_click_set_colors(self, sender, e):
        if self.list_box2.Items.Count <= 0:
            return
        else:
            self.event.Raise()

    def button_click_reset(self, sender, e):
        self.reset_ev.Raise()

    def button_click_select_all(self, sender, e):
        """Select all elements from all parameter values."""
        try:
            if self.list_box2.Items.Count <= 0:
                return

            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if uidoc is None:
                uidoc = __revit__.ActiveUIDocument

            all_element_ids = List[DB.ElementId]()

            for i in range(self.list_box2.Items.Count):
                try:
                    item = self.list_box2.Items[i]
                    row = self._get_data_row_from_item(item, i)
                    if row is None:
                        continue

                    value_item = row["Value"]
                    if hasattr(value_item, "ele_id") and value_item.ele_id is not None:
                        for ele_id in value_item.ele_id:
                            all_element_ids.Add(ele_id)
                except (KeyError, AttributeError, IndexError) as ex:
                    logger.debug(
                        "Error accessing listbox item %d in select_all: %s", i, str(ex)
                    )
                    continue

            if all_element_ids.Count > 0:
                uidoc.Selection.SetElementIds(all_element_ids)
                uidoc.RefreshActiveView()
                logger.debug(
                    "Selected %d elements via Select All", all_element_ids.Count
                )
        except Exception as ex:
            logger.debug("Error in button_click_select_all: %s", str(ex))

    def button_click_select_none(self, sender, e):
        """Clear the current selection in Revit."""
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if uidoc is None:
                uidoc = __revit__.ActiveUIDocument

            empty_list = List[DB.ElementId]()
            uidoc.Selection.SetElementIds(empty_list)
            uidoc.RefreshActiveView()
            logger.debug("Cleared selection via Select None")
        except Exception as ex:
            logger.debug("Error in button_click_select_none: %s", str(ex))

    def button_click_random_colors(self, sender, e):
        """Trigger random color assignment by reselecting parameter"""
        try:
            if self._list_box1.SelectedIndex != -1:
                sel_index = self._list_box1.SelectedIndex
                self._list_box1.SelectedIndex = -1
                self._list_box1.SelectedIndex = sel_index
        except Exception:
            external_event_trace()

    def button_click_gradient_colors(self, sender, e):
        """Apply gradient colors to all values"""
        self.list_box2.SelectionChanged -= self.list_selected_index_changed
        try:
            number_items = self.list_box2.Items.Count
            if number_items <= 2:
                return
            
            # Get first and last colors
            first_item = self.list_box2.Items[0]
            last_item = self.list_box2.Items[number_items - 1]
            first_row = self._get_data_row_from_item(first_item, 0)
            last_row = self._get_data_row_from_item(last_item, number_items - 1)
            if first_row is None or last_row is None:
                return
            start_color = first_row["Value"].colour
            end_color = last_row["Value"].colour

            # Generate gradient colors
            list_colors = self.get_gradient_colors(
                start_color, end_color, number_items
            )
            
            # Collect existing values and update their colors
            list_values = []
            for indx in range(number_items):
                item = self.list_box2.Items[indx]
                row = self._get_data_row_from_item(item, indx)
                if row is None:
                    continue
                value = row["Value"]
                # Update colors in existing ValuesInfo object (preserve all data including ele_id list)
                value.n1 = abs(list_colors[indx][1])
                value.n2 = abs(list_colors[indx][2])
                value.n3 = abs(list_colors[indx][3])
                value.colour = Drawing.Color.FromArgb(value.n1, value.n2, value.n3)
                list_values.append(value)

            # Recreate table with new ValuesInfo objects (like check_item does)
            self._table_data_3 = DataTable("Data")
            self._table_data_3.Columns.Add("Key", System.String)
            self._table_data_3.Columns.Add("Value", System.Object)
            
            vl_par = [x.value for x in list_values]
            for key_, value_ in zip(vl_par, list_values):
                self._table_data_3.Rows.Add(key_, value_)

            # Set ItemsSource and update (same pattern as check_item)
            default_view = self._table_data_3.DefaultView
            self.list_box2.ItemsSource = default_view
            self.list_box2.SelectedIndex = -1
            self._update_placeholder_visibility()
            self.list_box2.UpdateLayout()

            try:
                self.list_box2.SelectionChanged -= self.list_selected_index_changed
            except Exception:
                # Handler may not be subscribed, ignore unsubscribe errors
                pass
            self.list_box2.SelectionChanged += self.list_selected_index_changed

            # Update colors asynchronously (same as check_item)
            self._update_listbox_colors_async()
        except Exception:
            external_event_trace()
        finally:
            self.list_box2.SelectionChanged += self.list_selected_index_changed

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
        """Handle window closing"""
        self.IsOpen = 0
        self.uns_event.Raise()

    def list_box2_mouse_down(self, sender, e):
        """Capture Shift key state when mouse is pressed on list items."""
        from System.Windows.Input import (
            MouseButtonEventArgs,
            ModifierKeys,
            Keyboard,
            Key,
        )

        if isinstance(e, MouseButtonEventArgs):
            shift_from_event = (
                e.KeyboardDevice.Modifiers & ModifierKeys.Shift
            ) == ModifierKeys.Shift
            shift_from_keyboard = Keyboard.IsKeyDown(
                Key.LeftShift
            ) or Keyboard.IsKeyDown(Key.RightShift)
            self._shift_pressed_on_click = shift_from_event or shift_from_keyboard
        else:
            self._shift_pressed_on_click = False

    def list_selected_index_changed(self, sender, e):
        """Handle ListBox selection change for color picking or element selection."""
        # Reset shift flag if clicking outside (SelectedIndex == -1)
        if sender.SelectedIndex == -1:
            if hasattr(self, "_shift_pressed_on_click"):
                self._shift_pressed_on_click = False
            return

        from System.Windows.Input import Keyboard, Key

        shift_pressed = Keyboard.IsKeyDown(Key.LeftShift) or Keyboard.IsKeyDown(
            Key.RightShift
        )

        if (
            not shift_pressed
            and hasattr(self, "_shift_pressed_on_click")
            and self._shift_pressed_on_click
        ):
            shift_pressed = True

        if shift_pressed:
            try:
                selected_item = sender.SelectedItem
                if selected_item is not None:
                    # Access DataRowView in WPF
                    from System.Data import DataRowView

                    row = None
                    if isinstance(selected_item, DataRowView):
                        row = selected_item.Row
                    elif hasattr(selected_item, "Row"):
                        row = selected_item.Row
                    else:
                        # Fallback for direct DataTable access with bounds checking
                        if (
                            hasattr(self, "_table_data_3")
                            and self._table_data_3 is not None
                            and sender.SelectedIndex >= 0
                            and sender.SelectedIndex < self._table_data_3.Rows.Count
                        ):
                            row = self._table_data_3.Rows[sender.SelectedIndex]
                    
                    if row is None:
                        # Temporarily unsubscribe to prevent recursive calls
                        try:
                            self.list_box2.SelectionChanged -= self.list_selected_index_changed
                            sender.SelectedIndex = -1
                        except Exception:
                            pass
                        finally:
                            try:
                                self.list_box2.SelectionChanged += self.list_selected_index_changed
                            except Exception:
                                pass
                        self._shift_pressed_on_click = False
                        return
                    
                    value_item = row["Value"]
                    if (
                        hasattr(value_item, "ele_id")
                        and value_item.ele_id is not None
                        and value_item.ele_id.Count > 0
                    ):
                        uidoc = HOST_APP.uiapp.ActiveUIDocument
                        if uidoc is None:
                            uidoc = __revit__.ActiveUIDocument
                        element_ids = value_item.ele_id
                        uidoc.Selection.SetElementIds(element_ids)
                        uidoc.RefreshActiveView()
                        logger.debug("Selected %d elements", element_ids.Count)
                    else:
                        logger.debug("No elements found for selected value")
                
                # Temporarily unsubscribe to prevent recursive calls
                try:
                    self.list_box2.SelectionChanged -= self.list_selected_index_changed
                    sender.SelectedIndex = -1
                except Exception:
                    pass
                finally:
                    try:
                        self.list_box2.SelectionChanged += self.list_selected_index_changed
                    except Exception:
                        pass
            except Exception as ex:
                logger.debug("Error selecting elements: %s", str(ex))
                # Temporarily unsubscribe to prevent recursive calls
                try:
                    self.list_box2.SelectionChanged -= self.list_selected_index_changed
                    sender.SelectedIndex = -1
                except Exception:
                    pass
                finally:
                    try:
                        self.list_box2.SelectionChanged += self.list_selected_index_changed
                    except Exception:
                        pass
            finally:
                self._shift_pressed_on_click = False
        else:
            clr_dlg = Forms.ColorDialog()
            clr_dlg.AllowFullOpen = True
            if clr_dlg.ShowDialog() == Forms.DialogResult.OK:
                selected_item = sender.SelectedItem
                if selected_item is not None:
                    row = self._get_data_row_from_item(
                        selected_item, sender.SelectedIndex
                    )
                    if row is None:
                        # Temporarily unsubscribe to prevent recursive calls
                        try:
                            self.list_box2.SelectionChanged -= self.list_selected_index_changed
                            sender.SelectedIndex = -1
                        except Exception:
                            pass
                        finally:
                            try:
                                self.list_box2.SelectionChanged += self.list_selected_index_changed
                            except Exception:
                                pass
                        self._shift_pressed_on_click = False
                        return
                    value_item = row["Value"]
                    value_item.n1 = clr_dlg.Color.R
                    value_item.n2 = clr_dlg.Color.G
                    value_item.n3 = clr_dlg.Color.B
                    value_item.colour = Drawing.Color.FromArgb(
                        clr_dlg.Color.R, clr_dlg.Color.G, clr_dlg.Color.B
                    )
                    self._update_listbox_colors()
            # Temporarily unsubscribe to prevent recursive calls
            try:
                self.list_box2.SelectionChanged -= self.list_selected_index_changed
                sender.SelectedIndex = -1
            except Exception:
                pass
            finally:
                try:
                    self.list_box2.SelectionChanged += self.list_selected_index_changed
                except Exception:
                    pass
            self._shift_pressed_on_click = False

    def _update_listbox_colors_async(self):
        """Update listbox colors after UI is ready using timer."""
        try:
            from System.Windows.Threading import DispatcherTimer, DispatcherPriority

            timer = DispatcherTimer(DispatcherPriority.Loaded)
            timer.Interval = System.TimeSpan.FromMilliseconds(100)

            def update_colors(s, ev):
                try:
                    self._update_listbox_colors()
                except Exception as ex:
                    logger.debug("Error in update_colors timer: %s", str(ex))
                finally:
                    timer.Stop()

            timer.Tick += update_colors
            timer.Start()
        except Exception as ex:
            logger.debug("Error setting up color update timer: %s", str(ex))
            self._update_listbox_colors()

    def _update_listbox_colors(self):
        """Update ListBox item backgrounds to show colors."""
        try:
            from System.Windows.Media import SolidColorBrush, Color

            if not hasattr(self, "_table_data_3") or self._table_data_3 is None:
                return

            for i in range(self.list_box2.Items.Count):
                try:
                    item = self.list_box2.Items[i]
                    row = self._get_data_row_from_item(item, i)
                    if row is None:
                        continue

                    value_item = row["Value"]
                    if not hasattr(value_item, "colour"):
                        continue

                    color_obj = value_item.colour
                    wpf_color = Color.FromArgb(
                        color_obj.A, color_obj.R, color_obj.G, color_obj.B
                    )
                    brush = SolidColorBrush(wpf_color)

                    listbox_item = (
                        self.list_box2.ItemContainerGenerator.ContainerFromIndex(i)
                    )
                    if listbox_item is not None:
                        listbox_item.Background = brush
                        brightness = (
                            color_obj.R * 299 + color_obj.G * 587 + color_obj.B * 114
                        ) / 1000
                        if brightness > 128 or (
                            color_obj.R == 255
                            and color_obj.G == 255
                            and color_obj.B == 255
                        ):
                            listbox_item.Foreground = SolidColorBrush(
                                Color.FromRgb(0, 0, 0)
                            )
                        else:
                            listbox_item.Foreground = SolidColorBrush(
                                Color.FromRgb(255, 255, 255)
                            )
                except (KeyError, AttributeError, IndexError) as ex:
                    logger.debug(
                        "Error updating listbox color for item %d: %s", i, str(ex)
                    )
                    continue
        except Exception:
            external_event_trace()

    def check_item(self, sender, e):
        """Handle parameter selection change."""
        try:
            self.list_box2.SelectionChanged -= self.list_selected_index_changed
        except Exception:
            # Handler may not be subscribed, ignore unsubscribe errors
            pass

        # Get selected category
        if self._categories.SelectedItem is None:
            logger.debug("No category selected")
            return
        sel_cat_row = self._categories.SelectedItem
        # DataRowView from DataTable.DefaultView
        from System.Data import DataRowView

        try:
            if isinstance(sel_cat_row, DataRowView):
                sel_cat = sel_cat_row.Row["Value"]
            elif hasattr(sel_cat_row, "Row"):
                sel_cat = sel_cat_row.Row["Value"]
            elif hasattr(sel_cat_row, "Item"):
                sel_cat = sel_cat_row.Item["Value"]
            else:
                sel_cat = sel_cat_row["Value"]
        except Exception as ex:
            logger.debug("Error getting category: %s", str(ex))
            return

        if sel_cat is None or sel_cat == 0:
            return
        if (
            sender.SelectedIndex == -1
            or sender.SelectedItem is None
            or sender.SelectedIndex == 0
        ):
            if sender.SelectedIndex == 0:
                selected_item = sender.SelectedItem
                if selected_item is not None:
                    row = self._get_data_row_from_item(selected_item, 0)
                    if row is not None and row["Value"] == 0:
                        self._table_data_3 = DataTable("Data")
                        self._table_data_3.Columns.Add("Key", System.String)
                        self._table_data_3.Columns.Add("Value", System.Object)
                        self.list_box2.ItemsSource = self._table_data_3.DefaultView
                        self._update_placeholder_visibility()
                        return
            self._table_data_3 = DataTable("Data")
            self._table_data_3.Columns.Add("Key", System.String)
            self._table_data_3.Columns.Add("Value", System.Object)
            self.list_box2.ItemsSource = self._table_data_3.DefaultView
            self._update_placeholder_visibility()
            return

        sel_param_row = sender.SelectedItem
        row = self._get_data_row_from_item(sel_param_row, sender.SelectedIndex)
        if row is None:
            return
        sel_param = row["Value"]

        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)

        rng_val = get_range_values(sel_cat, sel_param, self.crt_view)
        vl_par = [x.value for x in rng_val]

        for key_, value_ in zip(vl_par, rng_val):
            self._table_data_3.Rows.Add(key_, value_)

        if self._table_data_3.Rows.Count == 0:
            self.list_box2.ItemsSource = None
            self._update_placeholder_visibility()
            return

        default_view = self._table_data_3.DefaultView
        self.list_box2.ItemsSource = default_view
        self.list_box2.SelectedIndex = -1
        self._update_placeholder_visibility()
        self.list_box2.UpdateLayout()

        try:
            self.list_box2.SelectionChanged -= self.list_selected_index_changed
        except Exception:
            # Handler may not be subscribed, ignore unsubscribe errors
            pass
        self.list_box2.SelectionChanged += self.list_selected_index_changed

        self._update_listbox_colors_async()

    def update_filter(self, sender, e):
        """Update parameter list when category selection changes."""
        if sender.SelectedItem is None:
            return

        sel_cat_row = sender.SelectedItem
        row = self._get_data_row_from_item(sel_cat_row, sender.SelectedIndex)
        if row is None:
            return
        sel_cat = row["Value"]

        self._table_data_2 = DataTable("Data")
        self._table_data_2.Columns.Add("Key", System.String)
        self._table_data_2.Columns.Add("Value", System.Object)
        self._table_data_3 = DataTable("Data")
        self._table_data_3.Columns.Add("Key", System.String)
        self._table_data_3.Columns.Add("Value", System.Object)

        select_parameter_text = self.get_locale_string(
            "ColorSplasher.Messages.SelectParameter"
        )
        self._table_data_2.Rows.Add(select_parameter_text, 0)

        if sel_cat != 0 and sender.SelectedIndex != 0:
            names_par = [x.name for x in sel_cat.par]
            for key_, value_ in zip(names_par, sel_cat.par):
                self._table_data_2.Rows.Add(key_, value_)
            self._all_parameters = [
                (key_, value_) for key_, value_ in zip(names_par, sel_cat.par)
            ]
            self._list_box1.ItemsSource = self._table_data_2.DefaultView
            self._list_box1.SelectedIndex = 0
            from System.Windows.Media import Brushes

            placeholder_text = self.get_locale_string(
                "ColorSplasher.Placeholders.SearchParameters"
            )
            self._search_box.Text = placeholder_text
            self._search_box.Foreground = Brushes.Gray
            self.list_box2.ItemsSource = self._table_data_3.DefaultView
            self._update_placeholder_visibility()
        else:
            self._all_parameters = []
            self._list_box1.ItemsSource = self._table_data_2.DefaultView
            self._list_box1.SelectedIndex = 0
            self.list_box2.ItemsSource = self._table_data_3.DefaultView
            self._update_placeholder_visibility()

    def on_search_text_changed(self, sender, e):
        """Filter parameters based on search text."""
        placeholder_text = self.get_locale_string(
            "ColorSplasher.Placeholders.SearchParameters"
        )
        if self._search_box.Text == placeholder_text:
            return
        search_text = self._search_box.Text.lower()

        filtered_table = DataTable("Data")
        filtered_table.Columns.Add("Key", System.String)
        filtered_table.Columns.Add("Value", System.Object)

        select_parameter_text = self.get_locale_string(
            "ColorSplasher.Messages.SelectParameter"
        )
        filtered_table.Rows.Add(select_parameter_text, 0)

        if len(self._all_parameters) > 0:
            for key_, value_ in self._all_parameters:
                if search_text == "" or search_text in key_.lower():
                    filtered_table.Rows.Add(key_, value_)

        selected_item_value = None
        if self._list_box1.SelectedIndex != -1 and self._list_box1.SelectedIndex < len(
            self._list_box1.Items
        ):
            sel_item = self._list_box1.SelectedItem
            row = self._get_data_row_from_item(sel_item, self._list_box1.SelectedIndex)
            if row is not None:
                selected_item_value = row["Value"]

        self._list_box1.ItemsSource = filtered_table.DefaultView

        if selected_item_value is not None:
            for indx in range(self._list_box1.Items.Count):
                item = self._list_box1.Items[indx]
                row = self._get_data_row_from_item(item, indx)
                if row is not None:
                    item_value = row["Value"]
                    if item_value == selected_item_value:
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
        with Forms.SaveFileDialog() as save_file_dialog:
            wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
            if wndw:
                save_file_dialog.Title = wndw.get_locale_string(
                    "ColorSplasher.SaveLoadDialog.SaveTitle"
                )
            else:
                save_file_dialog.Title = "Specify Path to Save Color Scheme"
            save_file_dialog.Filter = "Color Scheme (*.cschn)|*.cschn"
            save_file_dialog.RestoreDirectory = True
            save_file_dialog.OverwritePrompt = True
            save_file_dialog.InitialDirectory = System.Environment.GetFolderPath(
                System.Environment.SpecialFolder.Desktop
            )
            save_file_dialog.FileName = "Color Scheme.cschn"
            wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
            if not wndw or wndw.list_box2.Items.Count == 0:
                if wndw:
                    wndw.Hide()
                self.Hide()
                if wndw:
                    no_colors_title = wndw.get_locale_string(
                        "ColorSplasher.SaveLoadDialog.NoColorsDetected"
                    )
                    no_colors_msg = wndw.get_locale_string(
                        "ColorSplasher.SaveLoadDialog.NoColorsDetected.Message"
                    )
                    UI.TaskDialog.Show(no_colors_title, no_colors_msg)
                else:
                    UI.TaskDialog.Show(
                        "No Colors Detected",
                        "The list of values in the main window is empty. Please, select a category and parameter to add items with colors.",
                    )
                if wndw:
                    wndw.Show()
                self.Close()
            elif save_file_dialog.ShowDialog() == Forms.DialogResult.OK:
                self.save_path_to_file(save_file_dialog.FileName)
                self.Close()

    def save_path_to_file(self, new_path):
        try:
            wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
            if not wndw:
                return
            # Save location selected in save file dialog.
            with open(new_path, "w") as file:
                for i in range(wndw.list_box2.Items.Count):
                    item = wndw.list_box2.Items[i]
                    if hasattr(item, "Row"):
                        value_item = item.Row["Value"]
                        item_key = item.Row["Key"]
                    else:
                        value_item = wndw._table_data_3.Rows[i]["Value"]
                        item_key = wndw._table_data_3.Rows[i]["Key"]
                    color_inst = value_item.colour
                    file.write(
                        item_key
                        + "::R"
                        + str(color_inst.R)
                        + "G"
                        + str(color_inst.G)
                        + "B"
                        + str(color_inst.B)
                        + "\n"
                    )
        except Exception as ex:
            external_event_trace()
            wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
            if wndw:
                error_title = wndw.get_locale_string(
                    "ColorSplasher.SaveLoadDialog.ErrorSaving"
                )
                UI.TaskDialog.Show(error_title, str(ex))
            else:
                UI.TaskDialog.Show("Error Saving Scheme", str(ex))

    def specify_path_load(self, sender, e):
        with Forms.OpenFileDialog() as open_file_dialog:
            wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
            if wndw:
                open_file_dialog.Title = wndw.get_locale_string(
                    "ColorSplasher.SaveLoadDialog.LoadTitle"
                )
            else:
                open_file_dialog.Title = "Specify Path to Load Color Scheme"
            open_file_dialog.Filter = "Color Scheme (*.cschn)|*.cschn"
            open_file_dialog.RestoreDirectory = True
            open_file_dialog.InitialDirectory = System.Environment.GetFolderPath(
                System.Environment.SpecialFolder.Desktop
            )
            if not wndw or wndw.list_box2.Items.Count == 0:
                if wndw:
                    wndw.Hide()
                self.Hide()
                if wndw:
                    no_values_title = wndw.get_locale_string(
                        "ColorSplasher.SaveLoadDialog.NoValuesDetected"
                    )
                    no_values_msg = wndw.get_locale_string(
                        "ColorSplasher.SaveLoadDialog.NoValuesDetected.Message"
                    )
                    UI.TaskDialog.Show(no_values_title, no_values_msg)
                else:
                    UI.TaskDialog.Show(
                        "No Values Detected",
                        "The list of values in the main window is empty. Please, select a category and parameter to add items to apply colors.",
                    )
                if wndw:
                    wndw.Show()
                self.Close()
            elif open_file_dialog.ShowDialog() == Forms.DialogResult.OK:
                self.load_path_from_file(open_file_dialog.FileName)
                self.Close()

    def load_path_from_file(self, path):
        wndw = getattr(ColorSplasherWindow, "_current_wndw", None)
        if not isfile(path):
            if wndw:
                error_title = wndw.get_locale_string(
                    "ColorSplasher.SaveLoadDialog.ErrorLoading"
                )
                error_msg = wndw.get_locale_string(
                    "ColorSplasher.SaveLoadDialog.FileDoesNotExist"
                )
                UI.TaskDialog.Show(error_title, error_msg)
            else:
                UI.TaskDialog.Show("Error Loading Scheme", "The file does not exist.")
        else:
            if not wndw:
                return
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
                    wndw._update_listbox_colors()
            except Exception as ex:
                external_event_trace()
                if wndw:
                    error_title = wndw.get_locale_string(
                        "ColorSplasher.SaveLoadDialog.ErrorLoading"
                    )
                    UI.TaskDialog.Show(error_title, str(ex))
                else:
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
    selected_view = ac_doc.ActiveView
    if (
        selected_view.ViewType == DB.ViewType.ProjectBrowser
        or selected_view.ViewType == DB.ViewType.SystemBrowser
    ):
        selected_view = ac_doc.GetElement(uidoc.GetOpenUIViews()[0].ViewId)
    if not selected_view.CanUseTemporaryVisibilityModes():
        wndw = getattr(SubscribeView, "_wndw", None)
        task2 = None
        try:
            if wndw:
                task2 = UI.TaskDialog(
                    wndw.get_locale_string("ColorSplasher.TaskDialog.Title")
                )
                view_type_msg = wndw.get_locale_string(
                    "ColorSplasher.Messages.ViewTypeNotSupported"
                )
                task2.MainInstruction = view_type_msg.replace(
                    "{0}", str(selected_view.ViewType)
                )
                wndw.Topmost = False
            else:
                task2 = UI.TaskDialog("Color Elements by Parameter")
                task2.MainInstruction = (
                    "Visibility settings cannot be modified in "
                    + str(selected_view.ViewType)
                    + " views. Please, change your current view."
                )
        except Exception:
            external_event_trace()
            task2 = UI.TaskDialog("Color Elements by Parameter")
            task2.MainInstruction = (
                "Visibility settings cannot be modified in "
                + str(selected_view.ViewType)
                + " views. Please, change your current view."
            )
        task2.Show()
        try:
            if wndw:
                wndw.Topmost = True
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
        ele_par = (
            ele if param.param_type != 1 else doc_param.GetElement(ele.GetTypeId())
        )
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
    try:
        if doc_param is None:
            doc_param = acti_view.Document
    except (AttributeError, RuntimeError):
        doc_param = revit.DOCS.doc
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
        elementid_value_getter = get_elementid_value_func()
        current_int_cat_id = elementid_value_getter(ele.Category.Id)
        if (
            current_int_cat_id in cat_exc
            or current_int_cat_id >= -1
            or any(x.int_id == current_int_cat_id for x in list_cat)
        ):
            continue
        list_parameters = []
        for par in ele.Parameters:
            if par.Definition.BuiltInParameter not in (
                DB.BuiltInParameter.ELEM_CATEGORY_PARAM,
                DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT,
            ):
                list_parameters.append(ParameterInfo(0, par))
        typ = ele.Document.GetElement(ele.GetTypeId())
        if typ:
            for par in typ.Parameters:
                if par.Definition.BuiltInParameter not in (
                    DB.BuiltInParameter.ELEM_CATEGORY_PARAM,
                    DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT,
                ):
                    list_parameters.append(ParameterInfo(1, par))
        list_parameters = sorted(list_parameters, key=lambda x: x.name.upper())
        list_cat.append(CategoryInfo(ele.Category, list_parameters))
    list_cat = sorted(list_cat, key=lambda x: x.name)
    return list_cat


def solid_fill_pattern_id():
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
    """Generate color shades for different override types.

    Returns tuple: (line_color, foreground_color, background_color)
    Foreground and background use full base color. Line color is faded when
    used with pattern colors.
    """
    r, g, b = base_color.Red, base_color.Green, base_color.Blue
    foreground_color = base_color
    background_color = base_color

    if apply_line and (apply_foreground or apply_background):
        line_r = max(0, min(255, int(r + (255 - r) * 0.6)))
        line_g = max(0, min(255, int(g + (255 - g) * 0.6)))
        line_b = max(0, min(255, int(b + (255 - b) * 0.6)))
        gray = (line_r + line_g + line_b) / 3
        line_r = int(line_r * 0.7 + gray * 0.3)
        line_g = int(line_g * 0.7 + gray * 0.3)
        line_b = int(line_b * 0.7 + gray * 0.3)
        line_color = DB.Color(line_r, line_g, line_b)
    else:
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
        error_msg.MainContent = (
            "Please ensure you have a Revit project open and try again."
        )
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

        xaml_file = __file__.replace("script.py", "ColorSplasherWindow.xaml")
        wndw = ColorSplasherWindow(
            xaml_file,
            categ_inf_used,
            ext_event,
            ext_event_uns,
            sel_view,
            ext_event_reset,
            ext_event_legend,
            ext_event_filters,
        )
        if wndw._categories.Items.Count > 0:
            wndw._categories.SelectedIndex = 0
        wndw.show()

        SubscribeView._wndw = wndw
        ApplyColors._wndw = wndw
        ResetColors._wndw = wndw
        CreateLegend._wndw = wndw
        CreateFilters._wndw = wndw
        ColorSplasherWindow._current_wndw = wndw


if __name__ == "__main__":
    launch_color_splasher()
