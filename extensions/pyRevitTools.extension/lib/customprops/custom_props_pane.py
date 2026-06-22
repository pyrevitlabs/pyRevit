# -*- coding: utf-8 -*-
"""Element Properties dockable pane.

Generic parameter inspector/editor for any Revit element.
Always-present rows: Workset (editable) and Design Option (read-only).
All other parameters are user-configured via the config dialog.
"""

import os.path as op

from pyrevit import forms, HOST_APP, framework, revit
from pyrevit import DB, UI
from pyrevit.revit import is_yesno_parameter, query
from pyrevit.revit.events import execute_in_revit_context
from pyrevit.revit.db import create as revit_create
from pyrevit.userconfig import user_config
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales
from pyrevit.framework import SolidColorBrush, Color, Media

from match.match_utils import PropKeyValue
from match import filter_utils

get_elementid_value = get_elementid_value_func()

CONFIG_SECTION = "custom_properties_pane"

_SEL_CB_TAG = "sel_checkbox"
_RAW_INT_TAG = "_raw_int"

# LemonChiffon (#FFFACD) — dirty / pending-apply highlight
_DIRTY_BRUSH = SolidColorBrush(Color.FromArgb(255, 255, 250, 205))


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def get_additional_param_names():
    """Return list of extra parameter names from user config."""
    try:
        user_config.reload()
        if not user_config.has_section(CONFIG_SECTION):
            return []
        section = getattr(user_config, CONFIG_SECTION)
        raw = section.get_option("additional_parameters", "")
        return [p.strip() for p in raw.splitlines() if p.strip()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Revit query helpers
# ---------------------------------------------------------------------------


def _get_workset_name(doc, element):
    try:
        if not doc.IsWorkshared:
            return ""
        param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        if param:
            return param.AsValueString() or ""
    except Exception:
        pass
    return ""


def _get_design_option_name(element, main_model_label="Main Model"):
    try:
        do = element.DesignOption
        if not do:
            return main_model_label
        doc = element.Document
        try:
            option_filter = DB.ElementCategoryFilter(DB.BuiltInCategory.OST_DesignOptions)
            sets = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_DesignOptionSets)
                .WhereElementIsNotElementType()
                .ToElements()
            )
            for dos in sets:
                if do.Id in dos.GetDependentElements(option_filter):
                    return "{}: {}".format(dos.Name, do.Name)
        except Exception:
            pass
        return do.Name
    except Exception:
        pass
    return main_model_label


def _collect_worksets(doc):
    items = []
    try:
        if not doc.IsWorkshared:
            return items
        col = (
            DB.FilteredWorksetCollector(doc)
            .OfKind(DB.WorksetKind.UserWorkset)
            .ToWorksets()
        )
        for ws in col:
            items.append((ws.Name, ws.Id))
    except Exception:
        pass
    items.sort(key=lambda t: t[0])
    return items


# ---------------------------------------------------------------------------
# Apply helpers (run inside a Transaction via ExternalEvent)
# ---------------------------------------------------------------------------


def _set_workset(doc, element, workset_id):
    try:
        param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        if param and not param.IsReadOnly:
            param.Set(workset_id.IntegerValue)
            return True
    except Exception:
        pass
    return False


def _set_additional_param(doc, element, param_name, value_str):
    """Set a String/Integer/Double parameter from a string value."""
    try:
        param = element.LookupParameter(param_name)
        if param is None or param.IsReadOnly:
            return False
        st = param.StorageType
        if st == DB.StorageType.String:
            param.Set(value_str)
        elif st == DB.StorageType.Double:
            fti = param.Definition.GetDataType()
            uti = doc.GetUnits().GetFormatOptions(fti).GetUnitTypeId()
            value = DB.UnitUtils.ConvertToInternalUnits(float(value_str), uti)
            param.Set(value)
        elif st == DB.StorageType.Integer:
            param.Set(int(value_str))
        else:
            return False
        return True
    except Exception:
        return False


def _set_elementid_param(doc, element, param_name, new_val, ref_class, bic=None):
    """Set an ElementId parameter by resolving new_val as an element name."""
    try:
        param = element.LookupParameter(param_name)
        if param is None or param.IsReadOnly:
            return False

        collector = None
        if ref_class is not None:
            try:
                collector = query.get_elements_by_class(ref_class, doc=doc)
            except Exception:
                pass
        if collector is None and bic is not None:
            collector = query.get_elements_by_categories([bic], doc=doc)
        if collector is None:
            return False

        found_id = None
        for bic_el in collector:
            if hasattr(bic_el, "Name") and bic_el.Name == new_val:
                found_id = bic_el.Id
                break
        if found_id:
            param.Set(found_id)
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Other helpers
# ---------------------------------------------------------------------------


def _find_visual_child(parent, child_type, name=None):
    """Return the first descendant of child_type in the visual tree.

    If name is given, only matches elements whose Name property equals it.
    """
    count = Media.VisualTreeHelper.GetChildrenCount(parent)
    for i in range(count):
        child = Media.VisualTreeHelper.GetChild(parent, i)
        if isinstance(child, child_type):
            if name is None or getattr(child, "Name", "") == name:
                return child
        result = _find_visual_child(child, child_type, name)
        if result is not None:
            return result
    return None


# ---------------------------------------------------------------------------
# Dockable panel
# ---------------------------------------------------------------------------


class CustomPropertiesPanel(forms.WPFPanel):
    panel_title = applocales.get_locale_string({
        "en_us": "Custom Properties",
        "de_de": "Benutzerdefinierte Eigenschaften",
        "fr_fr": "Propriétés personnalisées",
        "es_es": "Propiedades personalizadas",
        "pt_br": "Propriedades personalizadas",
        "ru": "Свойства элемента",
        "chinese_s": "自定义属性",
    })
    panel_id = "d3a7f2c1-8e45-4b9a-a312-0f6b7c8d9e10"
    panel_source = op.join(op.dirname(__file__), "pane_ui.xaml")

    def __init__(self):
        forms.WPFPanel.__init__(self)

        self._elements = []
        self._doc = None
        self._worksets = []  # [(name, WorksetId)]

        self._copy_clipboard = []  # list of PropKeyValue
        self._suppress_dirty = False

        try:
            self._varies = self.get_locale_string("Varies")
        except Exception:
            self._varies = "Varies"
        try:
            self._main_model = self.get_locale_string("MainModel")
        except Exception:
            self._main_model = "Main Model"
        try:
            label = DB.LabelUtils.GetLabelForBuiltInParameter(
                DB.BuiltInParameter.ELEM_PARTITION_PARAM
            )
            if label:
                self.Resources["LblWorkset"] = label
        except Exception:
            pass

        self._setup_events()
        self._wire_fixed_param_events()
        self._set_status(self.get_locale_string("StatusNoSelection"))

    # ── event wiring ─────────────────────────────────────────────────────────

    def _setup_events(self):
        try:
            self._sel_handler = framework.EventHandler[
                UI.Events.SelectionChangedEventArgs
            ](self._on_selection_changed)
            self._doc_handler = framework.EventHandler[
                DB.Events.DocumentChangedEventArgs
            ](self._on_doc_changed)
            self._view_handler = framework.EventHandler[
                UI.Events.ViewActivatedEventArgs
            ](self._on_view_activated)

            HOST_APP.uiapp.SelectionChanged += self._sel_handler
            HOST_APP.app.DocumentChanged += self._doc_handler
            HOST_APP.uiapp.ViewActivated += self._view_handler
        except Exception as ex:
            self.logger.warning("Event wiring failed: {}".format(ex))

        self.Unloaded += framework.Windows.RoutedEventHandler(self._on_unloaded)

    def _wire_fixed_param_events(self):
        """Wire selection-checkbox and dirty events for the XAML-defined fixed rows."""
        try:
            self.workset_cb.Checked += framework.Windows.RoutedEventHandler(
                lambda s, e: self._on_sel_cb_changed()
            )
            self.workset_cb.Unchecked += framework.Windows.RoutedEventHandler(
                lambda s, e: self._on_sel_cb_changed()
            )
            self.workset_combo.SelectionChanged += self._on_workset_combo_changed
            self.workset_undo_btn.Click += framework.Windows.RoutedEventHandler(
                self._on_workset_undo_clicked
            )
        except Exception as ex:
            self.logger.warning("Fixed param event wiring failed: {}".format(ex))

    def _on_workset_combo_changed(self, sender, args):
        if not self._suppress_dirty:
            self._mark_field_dirty(sender)

    def _on_unloaded(self, sender, args):
        try:
            HOST_APP.uiapp.SelectionChanged -= self._sel_handler
            HOST_APP.app.DocumentChanged -= self._doc_handler
            HOST_APP.uiapp.ViewActivated -= self._view_handler
        except Exception:
            pass

    def _on_selection_changed(self, sender, args):
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if not uidoc:
                self._safe_ui(self._update_display, [])
                return
            doc = uidoc.Document
            ids = list(uidoc.Selection.GetElementIds())
            elements = [doc.GetElement(eid) for eid in ids]
            elements = [e for e in elements if e is not None]
            self._safe_ui(self._refresh_worksets_if_needed, doc)
            self._safe_ui(self._update_display, elements, doc)
        except Exception as ex:
            self.logger.warning("SelectionChanged handler error: {}".format(ex))

    def _safe_ui(self, func, *args):
        self.Dispatcher.BeginInvoke(
            framework.Threading.DispatcherPriority.Background,
            framework.System.Action(lambda: func(*args)),
        )

    def _on_doc_changed(self, sender, args):
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if not uidoc:
                return
            doc = uidoc.Document
            self._safe_ui(self._refresh_worksets_if_needed, doc)
            if not self._elements:
                return
            modified = set(args.GetModifiedElementIds())
            deleted = set(args.GetDeletedElementIds())
            current_ids = set(e.Id for e in self._elements)
            if current_ids & (modified | deleted):
                live_ids = current_ids - deleted
                live_elements = [doc.GetElement(eid) for eid in live_ids]
                live_elements = [e for e in live_elements if e is not None]
                self._safe_ui(self._update_display, live_elements, doc)
        except Exception:
            pass

    def _on_view_activated(self, sender, args):
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if uidoc:
                self._safe_ui(self._refresh_worksets_if_needed, uidoc.Document)
                self._safe_ui(self._update_display, [], uidoc.Document)
        except Exception:
            pass

    # ── workset refresh ───────────────────────────────────────────────────────

    def _refresh_worksets_if_needed(self, doc):
        if doc is None or doc is self._doc:
            return
        self._doc = doc
        self._worksets = _collect_worksets(doc)
        self._fill_combo(self.workset_combo, [n for n, _ in self._worksets])

    def _fill_combo(self, combo, names):
        self._suppress_dirty = True
        try:
            combo.Items.Clear()
            for n in names:
                combo.Items.Add(n)
        finally:
            self._suppress_dirty = False

    # ── display update ────────────────────────────────────────────────────────

    def _update_display(self, elements, doc=None):
        self._suppress_dirty = True
        try:
            self._elements = list(elements)
            if doc is None and elements:
                try:
                    self._doc = HOST_APP.uiapp.ActiveUIDocument.Document
                except Exception:
                    pass
            elif doc is not None:
                self._doc = doc

            count = len(self._elements)
            if count == 0:
                self._set_status(self.get_locale_string("StatusNoSelection"))
                self._clear_fields()
            else:
                self._set_status(
                    self.get_locale_string("StatusOneElement") if count == 1
                    else self.get_locale_string("StatusElements").format(count)
                )
                self._show_fixed()
                self._show_params()
        finally:
            self._suppress_dirty = False

        self._update_button_states()

    def _clear_fields(self):
        self._suppress_dirty = True
        try:
            self.workset_combo.Text = ""
            self.design_option_tb.Text = ""
            self.additional_panel.Children.Clear()
        finally:
            self._suppress_dirty = False
        try:
            self._clear_background(self.workset_combo)
            self.workset_undo_btn.Visibility = forms.WPF_COLLAPSED
        except Exception:
            pass

    def _show_fixed(self):
        doc = self._doc

        ws_names = [_get_workset_name(doc, e) for e in self._elements]
        self._set_combo_value(self.workset_combo, ws_names)
        try:
            self._clear_background(self.workset_combo)
            unique_ws = list(set(ws_names))
            self.workset_undo_btn.Tag = unique_ws[0] if len(unique_ws) == 1 else self._varies
            self.workset_undo_btn.Visibility = forms.WPF_COLLAPSED
        except Exception:
            pass

        do_names = [_get_design_option_name(e, self._main_model) for e in self._elements]
        unique = list(set(do_names))
        self.design_option_tb.Text = unique[0] if len(unique) == 1 else self._varies

    def _set_combo_value(self, combo, values):
        self._suppress_dirty = True
        try:
            unique = list(set(values))
            text = unique[0] if len(unique) == 1 else self._varies
            idx = combo.Items.IndexOf(text)
            if idx >= 0:
                combo.SelectedIndex = idx
            else:
                combo.SelectedIndex = -1
                combo.Text = text
        finally:
            self._suppress_dirty = False

    # ── parameters section ────────────────────────────────────────────────────

    def _show_params(self):
        self.additional_panel.Children.Clear()
        param_names = get_additional_param_names()
        if not param_names:
            return
        doc = self._doc
        for pname in param_names:
            row = self._make_param_row(pname, doc)
            if row is not None:
                self.additional_panel.Children.Add(row)

    def _make_param_row(self, param_name, doc):
        storage_type = None
        for e in self._elements:
            p = e.LookupParameter(param_name)
            if p:
                storage_type = p.StorageType
                break

        if storage_type is None:
            return self._build_text_row(
                param_name,
                "",
                readonly=True,
                tooltip=self.get_locale_string("TooltipParamNotFound"),
            )

        if storage_type == DB.StorageType.ElementId:
            return self._make_elementid_row(param_name, doc)

        return self._make_text_row(param_name, doc)

    def _make_text_row(self, param_name, doc):
        vals = []
        missing_param = False
        readonly_param = False
        opaque_int_param = False
        yesno_param = False

        for e in self._elements:
            try:
                p = e.LookupParameter(param_name)
                if not p:
                    missing_param = True
                    continue
                if p.IsReadOnly:
                    readonly_param = True
                st = p.StorageType
                if st == DB.StorageType.String:
                    vals.append(p.AsString() or "")
                elif st == DB.StorageType.Double:
                    fti = p.Definition.GetDataType()
                    uti = doc.GetUnits().GetFormatOptions(fti).GetUnitTypeId()
                    val = DB.UnitUtils.ConvertFromInternalUnits(p.AsDouble(), uti)
                    vals.append(str(round(val, 6)))
                elif st == DB.StorageType.Integer:
                    if not yesno_param:
                        yesno_param = is_yesno_parameter(p.Definition)
                    if yesno_param:
                        vals.append(str(p.AsInteger()))
                    else:
                        val_str = p.AsValueString() or str(p.AsInteger())
                        vals.append(val_str)
                        if not opaque_int_param:
                            try:
                                int(val_str)
                            except (ValueError, TypeError):
                                opaque_int_param = True
            except Exception:
                vals.append("")

        if yesno_param and not missing_param:
            return self._make_yesno_row(param_name, vals, readonly_param)

        readonly = readonly_param or opaque_int_param or missing_param
        tooltip = None
        if missing_param:
            tooltip = self.get_locale_string("TooltipParamMissing")
        elif readonly_param:
            tooltip = self.get_locale_string("TooltipParamReadOnly")
        elif opaque_int_param:
            tooltip = self.get_locale_string("TooltipParamOpaque")

        text = "" if missing_param else (vals[0] if len(set(vals)) == 1 else self._varies)
        sel_readonly = readonly_param or missing_param
        return self._build_text_row(
            param_name, text, readonly=readonly, tooltip=tooltip, sel_readonly=sel_readonly
        )

    def _make_yesno_row(self, param_name, int_vals, readonly):
        grid, _, sel_cb, undo_btn = self._make_row_grid(param_name, readonly=readonly)
        cb = framework.Controls.CheckBox()
        cb.VerticalAlignment = framework.Windows.VerticalAlignment.Center
        unique = list(set(int_vals))
        mixed = len(unique) != 1
        original_checked = False if mixed else unique[0] == "1"
        cb.IsChecked = original_checked
        cb.IsEnabled = not readonly and not mixed
        cb.ToolTip = (
            self.get_locale_string("TooltipParamReadOnly") if readonly
            else self.get_locale_string("TooltipMixedValues") if mixed
            else None
        )

        cb.Checked += self._on_field_yesno_changed
        cb.Unchecked += self._on_field_yesno_changed

        framework.Controls.Grid.SetColumn(cb, 2)
        grid.Children.Add(cb)
        undo_btn.Tag = original_checked
        return grid

    def _on_field_yesno_changed(self, sender, args):
        if not self._suppress_dirty:
            self._mark_field_dirty(sender)

    def _make_elementid_row(self, param_name, doc):
        current_names = []
        ref_class = None
        ref_bic = None

        for e in self._elements:
            try:
                p = e.LookupParameter(param_name)
                if not p:
                    continue

                eid = p.AsElementId()
                if eid == DB.ElementId.InvalidElementId:
                    continue

                ref_el = doc.GetElement(eid)
                if ref_el is None:
                    continue

                if ref_class is None:
                    ref_class = ref_el.GetType()

                if ref_bic is None:
                    try:
                        cat = ref_el.Category
                        if cat:
                            ref_bic = cat.BuiltInCategory
                    except Exception:
                        pass

                current_names.append(
                    ref_el.Name if hasattr(ref_el, "Name") else str(eid)
                )

            except Exception:
                pass

        if not current_names:
            return None

        options = []

        if ref_class is not None:
            try:
                collector = query.get_elements_by_class(ref_class, doc=doc)
                options = sorted(
                    set(el.Name for el in collector if hasattr(el, "Name") and el.Name)
                )
            except Exception:
                pass

        if not options and ref_bic is not None:
            try:
                collector = query.get_elements_by_categories([ref_bic], doc=doc)
                options = sorted(
                    set(el.Name for el in collector if hasattr(el, "Name") and el.Name)
                )
            except Exception:
                pass

        grid, _, sel_cb, undo_btn = self._make_row_grid(param_name, readonly=False)
        combo = framework.Controls.ComboBox()
        combo.Height = 22
        combo.FontSize = 11
        combo.IsEditable = True
        combo.Margin = framework.Windows.Thickness(0, 2, 0, 2)
        combo.VerticalContentAlignment = framework.Windows.VerticalAlignment.Center
        combo.Tag = (ref_class, ref_bic)

        for opt in options:
            combo.Items.Add(opt)

        unique = list(set(current_names))
        original_text = unique[0] if len(unique) == 1 else self._varies
        self._suppress_dirty = True
        try:
            if len(unique) == 1:
                idx = combo.Items.IndexOf(unique[0])
                if idx >= 0:
                    combo.SelectedIndex = idx
                else:
                    combo.Text = unique[0]
            else:
                combo.SelectedIndex = -1
                combo.Text = self._varies
        finally:
            self._suppress_dirty = False

        combo.SelectionChanged += self._on_field_combo_changed

        framework.Controls.Grid.SetColumn(combo, 2)
        grid.Children.Add(combo)
        undo_btn.Tag = original_text
        return grid

    def _on_field_combo_changed(self, sender, args):
        if not self._suppress_dirty:
            self._mark_field_dirty(sender)

    # ── row / grid builders ───────────────────────────────────────────────────

    def _make_row_grid(self, param_name, readonly=False, sel_readonly=None):
        """Return (grid, label, sel_checkbox, undo_button). Caller puts field in col 2."""
        grid = framework.Controls.Grid()
        col0 = framework.Controls.ColumnDefinition()
        col1 = framework.Controls.ColumnDefinition()
        col2 = framework.Controls.ColumnDefinition()
        col3 = framework.Controls.ColumnDefinition()
        col0.Width = framework.Windows.GridLength(20)
        col1.Width = framework.Windows.GridLength(
            1, framework.Windows.GridUnitType.Star
        )
        col2.Width = framework.Windows.GridLength(
            1, framework.Windows.GridUnitType.Star
        )
        col3.Width = framework.Windows.GridLength(20)
        grid.ColumnDefinitions.Add(col0)
        grid.ColumnDefinitions.Add(col1)
        grid.ColumnDefinitions.Add(col2)
        grid.ColumnDefinitions.Add(col3)
        grid.Margin = framework.Windows.Thickness(0, 2, 0, 2)

        sel_cb = framework.Controls.CheckBox()
        sel_cb.VerticalAlignment = framework.Windows.VerticalAlignment.Center
        sel_cb.IsEnabled = not (sel_readonly if sel_readonly is not None else readonly)
        sel_cb.Tag = _SEL_CB_TAG
        sel_cb.Checked += framework.Windows.RoutedEventHandler(
            lambda s, e: self._on_sel_cb_changed()
        )
        sel_cb.Unchecked += framework.Windows.RoutedEventHandler(
            lambda s, e: self._on_sel_cb_changed()
        )
        framework.Controls.Grid.SetColumn(sel_cb, 0)
        grid.Children.Add(sel_cb)

        lbl = framework.Controls.TextBlock()
        lbl.Text = param_name
        lbl.VerticalAlignment = framework.Windows.VerticalAlignment.Center
        lbl.FontSize = 11
        framework.Controls.Grid.SetColumn(lbl, 1)
        grid.Children.Add(lbl)

        undo_btn = framework.Controls.Button()
        undo_btn.Content = "↺"
        undo_btn.Width = 18
        undo_btn.Height = 18
        undo_btn.FontSize = 12
        undo_btn.Padding = framework.Windows.Thickness(0)
        undo_btn.VerticalAlignment = framework.Windows.VerticalAlignment.Center
        undo_btn.Visibility = forms.WPF_COLLAPSED
        undo_btn.ToolTip = self.get_locale_string("TooltipUndo")
        undo_btn.Click += self._on_undo_clicked
        framework.Controls.Grid.SetColumn(undo_btn, 3)
        grid.Children.Add(undo_btn)

        return grid, lbl, sel_cb, undo_btn

    def _build_text_row(self, param_name, text, readonly=False, tooltip=None, sel_readonly=None):
        grid, _, sel_cb, undo_btn = self._make_row_grid(param_name, readonly=readonly, sel_readonly=sel_readonly)
        tb = framework.Controls.TextBox()
        tb.Height = 22
        tb.FontSize = 11
        tb.VerticalContentAlignment = framework.Windows.VerticalAlignment.Center
        tb.Padding = framework.Windows.Thickness(4, 2, 4, 2)
        tb.Text = text
        tb.IsReadOnly = readonly
        if tooltip:
            tb.ToolTip = tooltip

        tb.TextChanged += self._on_field_text_changed

        framework.Controls.Grid.SetColumn(tb, 2)
        grid.Children.Add(tb)
        undo_btn.Tag = text
        return grid

    def _on_field_text_changed(self, sender, args):
        if not self._suppress_dirty:
            self._mark_field_dirty(sender)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _set_status(self, text):
        self.status_tb.Text = text

    def _mark_field_dirty(self, field):
        if not self._is_field_changed(field):
            self._clear_field_dirty(field)
            return
        self._set_background(field, _DIRTY_BRUSH)
        try:
            if field is self.workset_combo:
                self.workset_undo_btn.Visibility = framework.Windows.Visibility.Visible
            else:
                parent = getattr(field, "Parent", None)
                if parent is not None:
                    for child in parent.Children:
                        if isinstance(child, framework.Controls.Button):
                            child.Visibility = framework.Windows.Visibility.Visible
                            break
        except Exception:
            pass

    def _get_field_original(self, field):
        try:
            if field is self.workset_combo:
                return getattr(self.workset_undo_btn, "Tag", None)
            parent = getattr(field, "Parent", None)
            if parent is not None:
                for child in parent.Children:
                    if isinstance(child, framework.Controls.Button):
                        return child.Tag
        except Exception:
            pass
        return None

    def _is_field_changed(self, field):
        try:
            original = self._get_field_original(field)
            if isinstance(field, framework.Controls.TextBox):
                return field.Text != (original if original is not None else "")
            elif isinstance(field, framework.Controls.CheckBox):
                return bool(field.IsChecked) != bool(original)
            elif isinstance(field, framework.Controls.ComboBox):
                if field.SelectedItem is not None:
                    current = str(field.SelectedItem)
                else:
                    current = field.Text or ""
                return current != (original if original is not None else "")
        except Exception:
            return True
        return True

    def _set_background(self, control, brush):
        try:
            control.Background = brush
        except Exception:
            pass
        if isinstance(control, framework.Controls.ComboBox) and control.IsEditable:
            try:
                border = _find_visual_child(
                    control, framework.Controls.Border, name="Border"
                )
                if border is not None:
                    border.Background = brush
            except Exception:
                pass

    def _clear_background(self, control):
        self._set_background(control, None)

    def _clear_field_dirty(self, field):
        self._clear_background(field)
        try:
            if field is self.workset_combo:
                self.workset_undo_btn.Visibility = forms.WPF_COLLAPSED
            else:
                parent = getattr(field, "Parent", None)
                if parent is not None:
                    for child in parent.Children:
                        if isinstance(child, framework.Controls.Button):
                            child.Visibility = forms.WPF_COLLAPSED
                            break
        except Exception:
            pass

    def _on_undo_clicked(self, sender, args):
        original_value = getattr(sender, "Tag", None)
        parent = getattr(sender, "Parent", None)
        if parent is None:
            return
        field = None
        for child in parent.Children:
            if framework.Controls.Grid.GetColumn(child) == 2:
                field = child
                break
        if field is None:
            return
        self._suppress_dirty = True
        try:
            if isinstance(field, framework.Controls.TextBox):
                field.Text = original_value if original_value is not None else ""
                field.Tag = None
            elif isinstance(field, framework.Controls.ComboBox):
                text = original_value if original_value is not None else ""
                idx = field.Items.IndexOf(text)
                if idx >= 0:
                    field.SelectedIndex = idx
                else:
                    field.SelectedIndex = -1
                    field.Text = text
            elif isinstance(field, framework.Controls.CheckBox):
                field.IsChecked = bool(original_value)
        finally:
            self._suppress_dirty = False
        self._clear_background(field)
        sender.Visibility = forms.WPF_COLLAPSED

    def _on_workset_undo_clicked(self, sender, args):
        original_text = getattr(sender, "Tag", None)
        if original_text is None:
            return
        self._suppress_dirty = True
        try:
            idx = self.workset_combo.Items.IndexOf(original_text)
            if idx >= 0:
                self.workset_combo.SelectedIndex = idx
            else:
                self.workset_combo.SelectedIndex = -1
                self.workset_combo.Text = original_text
        finally:
            self._suppress_dirty = False
        self._clear_background(self.workset_combo)
        sender.Visibility = forms.WPF_COLLAPSED

    # ── Button state management ───────────────────────────────────────────────

    def _on_sel_cb_changed(self):
        self._update_button_states()

    def _update_button_states(self):
        has_elements = bool(self._elements)
        checked_names = self._get_checked_param_names()
        workset_checked = False
        try:
            workset_checked = bool(self.workset_cb.IsChecked) and has_elements
        except Exception:
            pass
        has_checked = bool(checked_names) or workset_checked

        self.copy_btn.IsEnabled = has_elements and has_checked
        self.filter_btn.IsEnabled = (
            has_elements and has_checked
            and self._all_checked_filterable(checked_names, workset_checked)
        )
        self.paste_btn.IsEnabled = bool(self._copy_clipboard)

    def _all_checked_filterable(self, checked_names, workset_checked):
        """Return True only if every checked parameter is filterable for the current categories."""
        if not self._elements or not self._doc:
            return True
        doc = self._doc
        try:
            cat_ids = list(set(e.Category.Id for e in self._elements if e.Category))
            if not cat_ids:
                return True
            filterable_vals = set(
                get_elementid_value(fid)
                for fid in DB.ParameterFilterUtilities.GetFilterableParametersInCommon(
                    doc, framework.List[DB.ElementId](cat_ids)
                )
            )
        except AttributeError:
            return True  # API not available in this Revit version
        except Exception:
            return True

        def _pid(param_name):
            try:
                if param_name == "Workset":
                    return get_elementid_value(
                        DB.ElementId(int(DB.BuiltInParameter.ELEM_PARTITION_PARAM))
                    )
                p = self._elements[0].LookupParameter(param_name)
                return get_elementid_value(p.Definition.Id) if p else None
            except Exception:
                return None

        if workset_checked:
            pid = _pid("Workset")
            if pid is not None and pid not in filterable_vals:
                return False
        for name in checked_names:
            pid = _pid(name)
            if pid is not None and pid not in filterable_vals:
                return False
        return True

    # ── Copy ──────────────────────────────────────────────────────────────────

    def copy_clicked(self, sender, args):
        if not self._elements or not self._doc:
            return
        doc = self._doc
        props = []

        # Fixed: workset
        try:
            if self.workset_cb.IsChecked:
                pkv = self._build_workset_pkv(doc)
                if pkv:
                    props.append(pkv)
        except Exception:
            pass

        # Additional params
        for name in self._get_checked_param_names():
            pkv = self._build_pkv_for_param(name, doc)
            if pkv:
                props.append(pkv)

        if props:
            self._copy_clipboard = props
            self._set_status(self.get_locale_string("StatusCopied").format(len(props)))
            self._update_button_states()

    def _build_workset_pkv(self, doc):
        if not self._elements:
            return None
        try:
            element = self._elements[0]
            param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
            if not param:
                return None
            ws_id_int = param.AsInteger()
            ws_name = param.AsValueString() or str(ws_id_int)
            return PropKeyValue(
                name="Workset",
                datatype=DB.StorageType.Integer,
                value=ws_id_int,
                istype=False,
                display_value=ws_name,
                categories=[element.Category] if element.Category else [],
            )
        except Exception:
            return None

    def _build_pkv_for_param(self, param_name, doc):
        """Build a PropKeyValue by reading the raw value from the first element."""
        if not self._elements:
            return None
        element = self._elements[0]
        param = element.LookupParameter(param_name)
        if not param:
            return None

        st = param.StorageType
        try:
            if st == DB.StorageType.String:
                raw_value = param.AsString() or ""
                ui_text = raw_value
            elif st == DB.StorageType.Double:
                fti = param.Definition.GetDataType()
                uti = doc.GetUnits().GetFormatOptions(fti).GetUnitTypeId()
                raw_value = param.AsDouble()
                display_val = DB.UnitUtils.ConvertFromInternalUnits(raw_value, uti)
                ui_text = str(round(display_val, 6))
            elif st == DB.StorageType.Integer:
                raw_value = param.AsInteger()
                if is_yesno_parameter(param.Definition):
                    ui_text = str(raw_value)
                else:
                    ui_text = param.AsValueString() or str(raw_value)
            elif st == DB.StorageType.ElementId:
                eid = param.AsElementId()
                raw_value = get_elementid_value(eid)
                ref_el = doc.GetElement(eid)
                ui_text = (
                    ref_el.Name
                    if ref_el and hasattr(ref_el, "Name")
                    else str(raw_value)
                )
            else:
                return None
        except Exception:
            return None

        return PropKeyValue(
            name=param_name,
            datatype=st,
            value=raw_value,
            istype=False,
            display_value=ui_text,
            categories=[element.Category] if element.Category else [],
        )

    def _get_checked_param_names(self):
        """Return names of additional-panel rows whose selection checkbox is ticked."""
        names = []
        for child in self.additional_panel.Children:
            try:
                sel_cb = None
                lbl = None
                for cc in child.Children:
                    if getattr(cc, "Tag", None) == _SEL_CB_TAG:
                        sel_cb = cc
                    elif isinstance(cc, framework.Controls.TextBlock):
                        lbl = cc
                if sel_cb and lbl and sel_cb.IsChecked:
                    names.append(lbl.Text)
            except Exception:
                pass
        return names

    # ── Paste ─────────────────────────────────────────────────────────────────

    def paste_clicked(self, sender, args):
        if not self._copy_clipboard:
            return

        self._suppress_dirty = True
        try:
            for pkv in self._copy_clipboard:
                if pkv.name == "Workset":
                    try:
                        idx = self.workset_combo.Items.IndexOf(pkv.display_value)
                        if idx >= 0:
                            self.workset_combo.SelectedIndex = idx
                        else:
                            self.workset_combo.Text = pkv.display_value
                    except Exception:
                        pass
                    continue

                field = self._find_field_for_param(pkv.name)
                if field is None:
                    continue

                if isinstance(field, framework.Controls.TextBox):
                    if not field.IsReadOnly:
                        field.Text = pkv.display_value
                    elif pkv.datatype == DB.StorageType.Integer:
                        field.Text = pkv.display_value
                        field.Tag = (_RAW_INT_TAG, pkv.value)
                elif isinstance(field, framework.Controls.ComboBox):
                    idx = field.Items.IndexOf(pkv.display_value)
                    if idx >= 0:
                        field.SelectedIndex = idx
                    else:
                        field.Text = pkv.display_value
                elif isinstance(field, framework.Controls.CheckBox):
                    if field.IsEnabled:
                        field.IsChecked = pkv.value == 1
        finally:
            self._suppress_dirty = False

        # Mark dirty after suppress is lifted
        try:
            for pkv in self._copy_clipboard:
                if pkv.name == "Workset":
                    self._mark_field_dirty(self.workset_combo)
                    continue
                field = self._find_field_for_param(pkv.name)
                if field:
                    self._mark_field_dirty(field)
        except Exception:
            pass

    def _find_field_for_param(self, param_name):
        """Return the value widget (TextBox/ComboBox/CheckBox) for param_name."""
        for child in self.additional_panel.Children:
            try:
                lbl = None
                field = None
                for cc in child.Children:
                    if getattr(cc, "Tag", None) == _SEL_CB_TAG:
                        continue
                    if isinstance(cc, framework.Controls.TextBlock):
                        lbl = cc
                    elif isinstance(
                        cc,
                        (
                            framework.Controls.TextBox,
                            framework.Controls.ComboBox,
                            framework.Controls.CheckBox,
                        ),
                    ):
                        field = cc
                if lbl and field and lbl.Text == param_name:
                    return field
            except Exception:
                pass
        return None

    # ── Filter ────────────────────────────────────────────────────────────────

    def filter_clicked(self, sender, args):
        uidoc = HOST_APP.uiapp.ActiveUIDocument
        if not uidoc:
            return
        doc = uidoc.Document
        view = uidoc.ActiveView

        if not isinstance(view, DB.View):
            forms.alert("Active view is not suitable for filters.")
            return

        checked_names = self._get_checked_param_names()
        if not checked_names:
            return

        # Build PKVs and ask for colours on the UI thread (before ExternalEvent)
        work_items = []
        for name in checked_names:
            pkv = self._build_pkv_for_param(name, doc)
            if not pkv:
                continue
            if not self._is_param_filterable(doc, pkv):
                self.logger.warning(
                    "Parameter '{}' is not filterable for these categories; skipped.".format(
                        name
                    )
                )
                continue
            chosen_hex = forms.ask_for_color()
            if not chosen_hex:
                continue
            revit_color = self._hex_to_revit_color(chosen_hex)
            if revit_color is None:
                continue
            work_items.append((pkv, revit_color))

        if not work_items:
            return

        elements_snap = list(self._elements)

        def _do_filters():
            try:
                solid_fill_id = self._get_solid_fill_pattern_id(doc)
                with revit.Transaction("Custom Properties Pane - Filters", doc=doc):
                    for pkv, revit_color in work_items:
                        self._apply_one_filter(
                            doc, view, pkv, revit_color, solid_fill_id, elements_snap
                        )
            except Exception as ex:
                self.logger.error("Filter creation failed: {}".format(ex))

        execute_in_revit_context(_do_filters)

    @staticmethod
    def _hex_to_revit_color(hex_str):
        """Convert '#AARRGGBB' or '#RRGGBB' hex string to DB.Color."""
        try:
            s = hex_str.lstrip("#")
            if len(s) == 8:
                r = int(s[2:4], 16)
                g = int(s[4:6], 16)
                b = int(s[6:8], 16)
            elif len(s) == 6:
                r = int(s[0:2], 16)
                g = int(s[2:4], 16)
                b = int(s[4:6], 16)
            else:
                return None
            return DB.Color(r, g, b)
        except Exception:
            return None

    def _is_param_filterable(self, doc, pkv):
        """Return True if the parameter can be used in a filter for element categories."""
        if not self._elements:
            return False
        try:
            param_id = self._get_param_id(doc, pkv)
            if not param_id:
                return False
            cat_ids = list(set(e.Category.Id for e in self._elements if e.Category))
            if not cat_ids:
                return False
            filterable = DB.ParameterFilterUtilities.GetFilterableParametersInCommon(
                doc,
                framework.List[DB.ElementId](cat_ids),
            )
            param_id_val = get_elementid_value(param_id)
            return any(get_elementid_value(fid) == param_id_val for fid in filterable)
        except AttributeError:
            return True  # method not available in this Revit version
        except Exception:
            return True

    def _get_param_id(self, doc, pkv):
        """Return the ElementId of the parameter definition."""
        if pkv.name == "Workset":
            return DB.ElementId(int(DB.BuiltInParameter.ELEM_PARTITION_PARAM))
        if not self._elements:
            return None
        element = self._elements[0]
        param = element.LookupParameter(pkv.name)
        if not param:
            return None
        try:
            return param.Definition.Id
        except Exception:
            return None

    def _find_matching_filter(self, doc, pkv):
        """Search the document for an existing equals ParameterFilterElement matching the PKV."""
        try:
            collector = query.get_rule_filters(doc)
            for f in collector:
                info = filter_utils.dissect_parameter_filter(doc, f)
                if not info:
                    continue
                if not (
                    info["parameter_name"] == pkv.name
                    and info["storage_type"] == pkv.datatype
                    and info["value"] == pkv.value
                ):
                    continue
                # Require at least one overlapping category so filters scoped
                # to different categories (e.g. Walls vs. Doors) are not reused.
                if pkv.categories and info["categories"]:
                    pkv_cat_ids = set(
                        get_elementid_value(c.Id)
                        for c in pkv.categories
                        if c and hasattr(c, "Id")
                    )
                    filter_cat_ids = set(
                        get_elementid_value(c.Id)
                        for c in info["categories"]
                        if c and hasattr(c, "Id")
                    )
                    if filter_cat_ids and not pkv_cat_ids.intersection(filter_cat_ids):
                        continue
                return f
        except Exception:
            pass
        return None

    @staticmethod
    def _unique_filter_name(doc, base_name):
        """Return base_name, or base_name (2), (3), … if the name is already taken."""
        existing = set(f.Name for f in query.get_rule_filters(doc))
        if base_name not in existing:
            return base_name
        counter = 2
        while True:
            candidate = "{} ({})".format(base_name, counter)
            if candidate not in existing:
                return candidate
            counter += 1

    def _apply_one_filter(self, doc, view, pkv, revit_color, solid_fill_id, elements):
        """Create or reuse a ParameterFilterElement and apply colour override to view."""
        existing = self._find_matching_filter(doc, pkv)

        if existing:
            filter_id = existing.Id
        else:
            param_id = self._get_param_id(doc, pkv)
            if not param_id:
                return

            bic_list = []
            for e in elements:
                if e.Category:
                    try:
                        bic = e.Category.BuiltInCategory
                        if bic not in bic_list:
                            bic_list.append(bic)
                    except Exception:
                        pass

            base_name = "{} == {}".format(pkv.name, pkv.display_value)
            if len(base_name) > 100:
                base_name = base_name[:97] + "..."
            filter_name = self._unique_filter_name(doc, base_name)

            # Convert value to the type create_param_value_filter expects
            if pkv.datatype == DB.StorageType.ElementId:
                param_value = DB.ElementId(pkv.value)
            else:
                param_value = pkv.value

            try:
                new_filter = revit_create.create_param_value_filter(
                    filter_name=filter_name,
                    param_id=param_id,
                    param_values=[param_value],
                    evaluator="==",
                    category_list=bic_list if bic_list else None,
                    doc=doc,
                )
                filter_id = new_filter.Id
            except Exception as ex:
                self.logger.warning(
                    "Failed to create filter for '{}': {}".format(pkv.name, ex)
                )
                return

        # Apply to view
        existing_filter_ids = list(view.GetFilters())
        if filter_id not in existing_filter_ids:
            view.AddFilter(filter_id)

        ogs = DB.OverrideGraphicSettings()
        ogs.SetSurfaceForegroundPatternColor(revit_color)
        if solid_fill_id:
            ogs.SetSurfaceForegroundPatternId(solid_fill_id)
            ogs.SetSurfaceForegroundPatternVisible(True)
        view.SetFilterOverrides(filter_id, ogs)
        view.SetFilterVisibility(filter_id, True)
        view.SetIsFilterEnabled(filter_id, True)

    @staticmethod
    def _get_solid_fill_pattern_id(doc):
        """Return the ElementId of the solid-fill drafting FillPatternElement."""
        try:
            patterns = query.get_all_fillpattern_elements(
                DB.FillPatternTarget.Drafting, doc=doc
            )
            for fp in patterns:
                if fp.GetFillPattern().IsSolidFill:
                    return fp.Id
        except Exception:
            pass
        return None

    # ── Apply ─────────────────────────────────────────────────────────────────

    def apply_clicked(self, sender, args):
        if not self._elements or not self._doc:
            return
        pending = self._collect_pending()
        doc = self._doc
        elements = list(self._elements)

        def _do_apply():
            try:
                with revit.Transaction("Custom Properties Pane - Apply", doc=doc):
                    for element in elements:
                        self._apply_to_element(doc, element, pending)
            except Exception as ex:
                self.logger.error("Apply failed: {}".format(ex))

        execute_in_revit_context(_do_apply)

    def _collect_pending(self):
        p = {}

        ws_text = self.workset_combo.Text.strip()
        if ws_text and ws_text != self._varies:
            match = [wid for name, wid in self._worksets if name == ws_text]
            p["workset_id"] = match[0] if match else None

        p["additional"] = {}
        for child in self.additional_panel.Children:
            try:
                lbl = None
                field = None
                for cc in child.Children:
                    if getattr(cc, "Tag", None) == _SEL_CB_TAG:
                        continue
                    if isinstance(cc, framework.Controls.TextBlock):
                        lbl = cc
                    elif isinstance(cc, framework.Controls.TextBox):
                        field = cc
                    elif isinstance(cc, framework.Controls.ComboBox):
                        field = cc
                    elif isinstance(cc, framework.Controls.CheckBox):
                        field = cc
                if lbl and field:
                    if isinstance(field, framework.Controls.CheckBox):
                        if not field.IsEnabled:
                            continue
                        val = "1" if bool(field.IsChecked) else "0"
                        ref_class, bic = None, None
                    else:
                        tag = getattr(field, "Tag", None)
                        raw_int = (
                            tag[1]
                            if isinstance(tag, tuple)
                            and len(tag) == 2
                            and tag[0] == _RAW_INT_TAG
                            else None
                        )
                        if isinstance(field, framework.Controls.TextBox) and field.IsReadOnly:
                            if raw_int is None:
                                continue  # opaque int not pasted — nothing to apply
                            val = str(raw_int)
                            ref_class, bic = None, None
                        else:
                            val = field.Text.strip()
                            if not val or val == self._varies:
                                continue
                            if raw_int is not None:
                                val = str(raw_int)
                                ref_class, bic = None, None
                            else:
                                ref_class, bic = tag if isinstance(tag, tuple) else (None, None)
                    p["additional"][lbl.Text] = (val, ref_class, bic)
            except Exception:
                pass

        return p

    def _apply_to_element(self, doc, element, pending):
        if "workset_id" in pending and pending["workset_id"] is not None:
            _set_workset(doc, element, pending["workset_id"])

        for pname, (pval, ref_class, bic) in (pending.get("additional") or {}).items():
            if ref_class is not None or bic is not None:
                _set_elementid_param(doc, element, pname, pval, ref_class, bic)
            else:
                _set_additional_param(doc, element, pname, pval)
