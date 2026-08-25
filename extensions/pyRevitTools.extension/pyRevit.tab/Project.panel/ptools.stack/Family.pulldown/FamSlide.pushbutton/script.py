# -*- coding: utf-8 -*-
"""FamSlide - live parameter sliders for the Family Editor.

Gives you a modeless panel of sliders / checkboxes / textboxes bound to
the active family's parameters, so you can see how the model reacts to
parameter changes (shape changes, constraint errors, etc.) without
round-tripping through the Family Types dialog every time.
"""

from pyrevit import forms, revit, script
from pyrevit import DB
from pyrevit.revit import events
from pyrevit.framework import Media, SolidColorBrush
from pyrevit.framework import Input, Controls, Windows
from pyrevit.coreutils import applocales


import famslide_paramutils
import famslide_actions

logger = script.get_logger()

# Path to the base XAML file, used to locate this bundle's
# FamSlideWindow.ResourceDictionary.<locale>.xaml files for translation
# lookups (see applocales.get_locale_string_from_xaml).
XAML_FILE = script.get_bundle_file("FamSlideWindow.xaml")


def _t(key):
    """str: localized string for `key`, falling back to `key` itself."""
    return applocales.get_locale_string_from_xaml(XAML_FILE, key)


# group_key -> resource dictionary key for that group's header text.
GROUP_TITLE_KEYS = {
    "value": "GroupTitleValue",
    "builtin": "GroupTitleBuiltin",
    "yesno": "GroupTitleYesNo",
}
GROUP_ORDER = ["value", "builtin", "yesno"]

# ParamRow.tags() returns stable ids (never localized) so the color
# lookup keeps working regardless of the active locale. TAG_LABEL_KEYS
# maps each id to the resource key for its display text.
TAG_COLORS = {
    "in_use": "#FFB48A00",
    "used_in_formula": "#FF7A3FA0",
    "has_formula": "#FFB33A3A",
    "built_in": "#FFCC5A1E",
    "instance": "#FF2E86C1",
    "type": "#FF1E8449",
    "associated": "#FF6C757D",
    "locked": "#FF566573",
}
TAG_LABEL_KEYS = {
    "in_use": "TagInUse",
    "used_in_formula": "TagUsedInFormula",
    "has_formula": "TagHasFormula",
    "built_in": "TagBuiltIn",
    "instance": "TagInstance",
    "type": "TagType",
    "associated": "TagAssociated",
    "locked": "TagLocked",
}

# module-level handle to the single live FamSlide window, so the
# doc-changed event hook (which pyRevit binds at import time, outside
# any instance) can reach it. None while no window is open.
ui = None


class FamSlideWindow(forms.WPFWindow):
    """Modeless FamSlide panel."""

    def __init__(self, xaml_file):
        forms.WPFWindow.__init__(self, xaml_file)

        self._rows = []
        self._show_editable_only = False
        self._show_labels = True
        self._expanded_state = {"value": True, "builtin": True, "yesno": True}
        # doc.Title -> {param_elementid: raw_value}. Keyed per family
        # document (not globally) so switching between open families
        # can't accidentally apply one family's preset to another.
        self._presets = {}

        self._apply_locale()

        self.RefreshButton.Click += self.on_refresh_click
        self.ShuffleButton.Click += self.on_shuffle_click
        self.DeleteUnusedButton.Click += self.on_delete_unused_click
        self.ToggleEditableButton.Click += self.on_toggle_editable_click
        self.ToggleLabelsButton.Click += self.on_toggle_labels_click
        self.SavePresetButton.Click += self.on_save_preset_click
        self.RestorePresetButton.Click += self.on_restore_preset_click
        self.CloseButton.Click += self.on_close_click
        self.Closed += self.on_closed

        script.restore_window_position(self)

        self.refresh_from_document()

    def _apply_locale(self):
        """Push localized text into the XAML-defined controls.

        The XAML ships with English text as a design-time fallback;
        this overwrites it with the resource-dictionary string for the
        active locale (or leaves the English fallback untouched if no
        matching key is found - see get_locale_string_from_xaml).
        """
        self.RefreshButton.Content = _t("BtnRefresh")
        self.RefreshButton.ToolTip = _t("TooltipRefresh")
        self.ShuffleButton.ToolTip = _t("TooltipShuffle")
        self.DeleteUnusedButton.ToolTip = _t("TooltipDeleteUnused")
        self.ToggleEditableButton.ToolTip = _t("TooltipToggleEditable")
        self.ToggleLabelsButton.ToolTip = _t("TooltipToggleLabels")
        self.SavePresetButton.ToolTip = _t("TooltipSavePreset")
        self.RestorePresetButton.ToolTip = _t("TooltipRestorePreset")
        self.CloseButton.Content = _t("BtnClose")
        self.CloseButton.ToolTip = _t("TooltipClose")
        self.FamilyNameLabel.Text = _t("NoFamilyLoaded")

    # ------------------------------------------------------------------
    # document (re)loading - only ever called from a valid API context
    # (window construction, the doc-changed/view-activated hook, or
    # from inside a bridged callable)
    # ------------------------------------------------------------------
    def refresh_from_document(self):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument:
            self.FamilyNameLabel.Text = _t("NoFamilyDocument")
            self.GroupsHost.Children.Clear()
            self._rows = []
            return

        self.FamilyNameLabel.Text = doc.Title
        fm = doc.FamilyManager
        self._rows = famslide_paramutils.classify_parameters(doc, fm)
        self._build_ui(fm)
        if doc.Title not in self._presets:
            self._presets[doc.Title] = self._capture_preset(doc)

    def _build_ui(self, fm):
        self.GroupsHost.Children.Clear()
        rows_by_group = dict((g, []) for g in GROUP_ORDER)
        for row in self._rows:
            rows_by_group[row.group].append(row)

        for group_key in GROUP_ORDER:
            group_rows = rows_by_group[group_key]
            if not group_rows:
                continue

            visible_rows = [
                r
                for r in group_rows
                if not (self._show_editable_only and not r.is_editable)
            ]
            if not visible_rows:
                continue

            expander = Controls.Expander()
            expander.Header = "{} ({})".format(
                _t(GROUP_TITLE_KEYS[group_key]), len(visible_rows)
            )
            expander.IsExpanded = self._expanded_state.get(group_key, True)
            expander.Margin = Windows.Thickness(0, 6, 0, 6)
            expander.Tag = group_key
            expander.Expanded += self.on_group_toggled
            expander.Collapsed += self.on_group_toggled

            body = Controls.StackPanel()
            for row in visible_rows:
                body.Children.Add(self._build_row(fm, row))
            expander.Content = body
            self.GroupsHost.Children.Add(expander)

    def _build_row(self, fm, row):
        outer = Controls.Border()
        outer.CornerRadius = Windows.CornerRadius(16)
        outer.Background = Media.Brushes.White
        outer.Margin = Windows.Thickness(0, 3, 0, 3)
        outer.Padding = Windows.Thickness(10, 6, 10, 6)

        # Built-in parameters can't be renamed or converted between
        # Instance/Type via the API, so there's nothing useful to put
        # in a context menu for them.
        if not row.is_builtin:
            outer.ContextMenu = self._build_context_menu(row)

        grid = Controls.Grid()
        col_name = Controls.ColumnDefinition()
        col_name.Width = Windows.GridLength(150)
        col_slider = Controls.ColumnDefinition()
        col_slider.Width = Windows.GridLength(1, Windows.GridUnitType.Star)
        col_value = Controls.ColumnDefinition()
        col_value.Width = Windows.GridLength(84)
        grid.ColumnDefinitions.Add(col_name)
        grid.ColumnDefinitions.Add(col_slider)
        grid.ColumnDefinitions.Add(col_value)

        # --- name + tag pills -------------------------------------------------
        name_panel = Controls.StackPanel()
        name_panel.VerticalAlignment = Windows.VerticalAlignment.Center
        name_text = Controls.TextBlock()
        name_text.Text = row.name
        name_text.FontWeight = Windows.FontWeights.SemiBold
        name_text.TextWrapping = Windows.TextWrapping.Wrap
        name_panel.Children.Add(name_text)

        tags = row.tags()
        if self._show_labels and tags:
            tag_wrap = Controls.WrapPanel()
            tag_wrap.Margin = Windows.Thickness(0, 3, 0, 0)
            for tag in tags:
                tag_wrap.Children.Add(self._build_tag_pill(tag))
            name_panel.Children.Add(tag_wrap)

        Controls.Grid.SetColumn(name_panel, 0)
        grid.Children.Add(name_panel)

        # --- control: slider / checkbox ---------------------------------------
        if row.group == "yesno":
            raw = fm.CurrentType.AsInteger(row.param)
            checkbox = Controls.CheckBox()
            checkbox.VerticalAlignment = Windows.VerticalAlignment.Center
            checkbox.HorizontalAlignment = Windows.HorizontalAlignment.Left
            checkbox.IsEnabled = row.is_editable
            checkbox.IsChecked = bool(raw)
            checkbox.Tag = row
            checkbox.Click += self.on_checkbox_click
            Controls.Grid.SetColumn(checkbox, 1)
            grid.Children.Add(checkbox)
            value_display = _t("ValueYes") if raw else _t("ValueNo")

        elif row.storage_type in (DB.StorageType.Double, DB.StorageType.Integer):
            if row.storage_type == DB.StorageType.Double:
                current_raw = fm.CurrentType.AsDouble(row.param)
            else:
                current_raw = fm.CurrentType.AsInteger(row.param)

            lo, hi = famslide_paramutils.default_range(row, current_raw)

            slider = Controls.Slider()
            slider.Minimum = lo
            slider.Maximum = hi
            slider.Value = current_raw if current_raw is not None else lo
            slider.IsEnabled = row.is_editable
            slider.VerticalAlignment = Windows.VerticalAlignment.Center
            slider.Margin = Windows.Thickness(8, 0, 8, 0)
            slider.IsMoveToPointEnabled = True
            slider.AutoToolTipPlacement = (
                Controls.Primitives.AutoToolTipPlacement.TopLeft
            )
            slider.Tag = row
            slider.PreviewMouseUp += self.on_slider_mouse_up
            slider.KeyUp += self.on_slider_key_up
            Controls.Grid.SetColumn(slider, 1)
            grid.Children.Add(slider)
            value_display = fm.CurrentType.AsValueString(row.param)

        else:
            # String / ElementId user parameters: no meaningful slider.
            spacer = Controls.TextBlock()
            Controls.Grid.SetColumn(spacer, 1)
            grid.Children.Add(spacer)
            # AsValueString does not work for familyparameters
            # see https://jeremytammik.github.io/tbc/a/0245_family_param_value.htm
            value_display = None
            if row.storage_type == DB.StorageType.String:
                value_display = fm.CurrentType.AsString(row.param)
            elif row.storage_type == DB.StorageType.ElementId:
                try:
                    doc = revit.doc
                    value_elid = fm.CurrentType.AsElementId(row.param)
                    value_el = doc.GetElement(value_elid)
                    if value_el:
                        value_display = value_el.Name
                except Exception:
                    pass

        # --- value cell -----------------------------------------------------
        # Border doesn't clip its Child to CornerRadius, so a control with
        # its own opaque background (TextBox) paints square corners right
        # over the rounded border. For editable rows we still need a real
        # TextBox to type into, so we make its background transparent and
        # zero out MinWidth (some base styles set a MinWidth that's wider
        # than this column, which is what pushed text past the rounded
        # edge). Read-only rows never need editing, so they get a
        # TextBlock instead - TextBlock supports real ellipsis trimming,
        # which a TextBox does not.
        value_border = Controls.Border()
        value_border.CornerRadius = Windows.CornerRadius(14)
        value_border.Background = Media.Brushes.White
        value_border.BorderBrush = Media.Brushes.LightGray
        value_border.BorderThickness = Windows.Thickness(1)
        value_border.VerticalAlignment = Windows.VerticalAlignment.Center

        if row.is_editable:
            value_box = Controls.TextBox()
            value_box.Text = value_display
            value_box.Background = Media.Brushes.Transparent
            value_box.BorderThickness = Windows.Thickness(0)
            value_box.Padding = Windows.Thickness(6, 4, 6, 4)
            value_box.TextAlignment = Windows.TextAlignment.Center
            value_box.MinWidth = 0.0
            value_box.Tag = row
            value_box.KeyDown += self.on_value_box_key_down
            value_box.LostFocus += self.on_value_box_lost_focus
            value_border.Child = value_box
        else:
            value_text = Controls.TextBlock()
            value_text.Text = value_display
            value_text.Padding = Windows.Thickness(6, 4, 6, 4)
            value_text.TextAlignment = Windows.TextAlignment.Center
            value_text.TextTrimming = Windows.TextTrimming.CharacterEllipsis
            value_text.VerticalAlignment = Windows.VerticalAlignment.Center
            if value_display:
                value_text.ToolTip = value_display
            value_border.Child = value_text

        Controls.Grid.SetColumn(value_border, 2)
        grid.Children.Add(value_border)

        outer.Child = grid
        return outer

    def _build_tag_pill(self, tag_id):
        pill = Controls.Border()
        pill.CornerRadius = Windows.CornerRadius(9)
        pill.Padding = Windows.Thickness(6, 1, 6, 1)
        pill.Margin = Windows.Thickness(0, 0, 3, 3)
        pill.Background = SolidColorBrush(
            Media.ColorConverter.ConvertFromString(TAG_COLORS.get(tag_id, "#FF8A8A8A"))
        )
        text = Controls.TextBlock()
        text.Text = _t(TAG_LABEL_KEYS.get(tag_id, tag_id))
        text.Foreground = Media.Brushes.White
        text.FontSize = 10.0
        pill.Child = text
        return pill

    def _build_context_menu(self, row):
        """ContextMenu: right-click actions for a single parameter row.

        Only offered for non-built-in parameters (see _build_row).
        """
        menu = Controls.ContextMenu()

        rename_item = Controls.MenuItem()
        rename_item.Header = _t("MenuRename")
        rename_item.Tag = row
        rename_item.Click += self.on_rename_click
        menu.Items.Add(rename_item)

        # Formula-driven parameters are forced to be Type parameters by
        # Revit itself, so offering to flip them to Instance would only
        # fail - disable the item instead of letting the user hit an
        # avoidable error.
        toggle_item = Controls.MenuItem()
        toggle_item.Header = (
            _t("MenuMakeType") if row.is_instance else _t("MenuMakeInstance")
        )
        toggle_item.Tag = row
        toggle_item.IsEnabled = not row.has_formula
        toggle_item.Click += self.on_toggle_instance_type_click
        menu.Items.Add(toggle_item)

        return menu

    # ------------------------------------------------------------------
    # UI-thread-only handlers (no Revit API access here directly)
    # ------------------------------------------------------------------
    def on_group_toggled(self, sender, args):
        self._expanded_state[sender.Tag] = sender.IsExpanded

    def on_toggle_editable_click(self, sender, args):
        self._show_editable_only = not self._show_editable_only
        doc = revit.doc
        if doc is not None and doc.IsFamilyDocument:
            self._build_ui(doc.FamilyManager)

    def on_toggle_labels_click(self, sender, args):
        self._show_labels = not self._show_labels
        doc = revit.doc
        if doc is not None and doc.IsFamilyDocument:
            self._build_ui(doc.FamilyManager)

    def on_close_click(self, sender, args):
        self.Close()

    def on_closed(self, sender, args):
        global ui
        events.stop_events()
        script.save_window_position(self)
        ui = None

    # --- controls that must hand off to Revit --------------------------------
    def on_rename_click(self, sender, args):
        row = sender.Tag
        new_name = forms.ask_for_string(
            default=row.name,
            prompt=_t("PromptRenameParameter"),
            title=_t("DialogRenameTitle"),
        )
        if not new_name or new_name == row.name:
            return
        events.execute_in_revit_context(self._commit_rename, row, new_name)

    def on_toggle_instance_type_click(self, sender, args):
        row = sender.Tag
        events.execute_in_revit_context(self._commit_toggle_instance_type, row)

    def on_save_preset_click(self, sender, args):
        events.execute_in_revit_context(self._do_save_preset)

    def on_restore_preset_click(self, sender, args):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument or doc.Title not in self._presets:
            forms.alert(_t("AlertNoPresetSaved"))
            return
        if not forms.alert(
            _t("ConfirmRestorePresetMessage"),
            yes=True,
            no=True,
        ):
            return
        events.execute_in_revit_context(self._do_restore_preset)

    def on_slider_mouse_up(self, sender, args):
        row = sender.Tag
        value = sender.Value
        events.execute_in_revit_context(self._commit_numeric, row, value)

    def on_slider_key_up(self, sender, args):
        # arrow-key nudges also count as a "release"
        if args.Key in (
            Input.Key.Left,
            Input.Key.Right,
            Input.Key.Up,
            Input.Key.Down,
            Input.Key.Home,
            Input.Key.End,
        ):
            row = sender.Tag
            value = sender.Value
            events.execute_in_revit_context(self._commit_numeric, row, value)

    def on_checkbox_click(self, sender, args):
        row = sender.Tag
        new_value = 1 if sender.IsChecked else 0
        events.execute_in_revit_context(self._commit_numeric, row, new_value)

    def on_value_box_key_down(self, sender, args):
        row = sender.Tag
        if not row.is_editable:
            return
        if args.Key == Input.Key.Enter:
            text = sender.Text
            events.execute_in_revit_context(self._commit_text, row, text)

    def on_value_box_lost_focus(self, sender, args):
        row = sender.Tag
        if not row.is_editable:
            return
        text = sender.Text
        events.execute_in_revit_context(self._commit_text, row, text)

    def on_refresh_click(self, sender, args):
        events.execute_in_revit_context(self.refresh_from_document)

    def on_shuffle_click(self, sender, args):
        if not forms.alert(
            _t("ConfirmShuffleMessage"),
            yes=True,
            no=True,
        ):
            return
        events.execute_in_revit_context(self._do_shuffle)

    def on_delete_unused_click(self, sender, args):
        if not forms.alert(
            _t("ConfirmDeleteUnusedMessage"),
            yes=True,
            no=True,
        ):
            return
        events.execute_in_revit_context(self._do_delete_unused)

    # ------------------------------------------------------------------
    # bridged callables - these run inside a valid Revit API context
    # ------------------------------------------------------------------
    def _commit_numeric(self, row, value):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument or not row.is_editable:
            return
        fm = doc.FamilyManager
        with revit.Transaction("FamSlide: Set {}".format(row.name), doc=doc):
            if row.group == "yesno" or row.storage_type == DB.StorageType.Integer:
                fm.Set(row.param, int(round(value)))
            else:
                fm.Set(row.param, float(value))

    def _commit_text(self, row, text):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument or not row.is_editable:
            return
        fm = doc.FamilyManager
        with revit.Transaction("FamSlide: Set {}".format(row.name), doc=doc):
            if row.storage_type in (DB.StorageType.Double, DB.StorageType.Integer):
                fm.SetValueString(row.param, text)
            elif row.storage_type == DB.StorageType.String:
                fm.Set(row.param, str(text))

    def _do_shuffle(self):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument:
            return
        famslide_actions.shuffle_parameter_values(doc, doc.FamilyManager, self._rows)

    def _do_delete_unused(self):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument:
            return
        famslide_actions.delete_unused_parameters(doc, doc.FamilyManager, self._rows)

    def _commit_rename(self, row, new_name):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument or row.is_builtin:
            return
        fm = doc.FamilyManager
        with revit.Transaction("FamSlide: Rename {}".format(row.name), doc=doc):
            try:
                fm.RenameParameter(row.param, new_name)
            except Exception:
                # most likely a duplicate name - nothing was changed,
                # so just let the transaction commit as a no-op.
                logger.exception(
                    "FamSlide: could not rename parameter '{}'".format(row.name)
                )
                forms.alert(_t("AlertRenameFailed").format(row.name))

    def _commit_toggle_instance_type(self, row):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument or row.is_builtin:
            return
        fm = doc.FamilyManager
        with revit.Transaction(
            "FamSlide: Toggle Instance/Type {}".format(row.name), doc=doc
        ):
            try:
                if row.is_instance:
                    fm.MakeType(row.param)
                else:
                    fm.MakeInstance(row.param)
            except Exception:
                # e.g. formula-driven parameters must stay Type - the
                # menu item is disabled for those, but guard here too
                # in case classification is stale after a quick edit.
                logger.exception(
                    "FamSlide: could not toggle instance/type for '{}'".format(row.name)
                )
                forms.alert(_t("AlertToggleInstanceTypeFailed").format(row.name))

    def _capture_preset(self, doc):
        fm = doc.FamilyManager
        preset = {}
        for row in self._rows:
            if not row.is_editable:
                continue
            param_id = famslide_paramutils.get_elementid_value(row.param.Id)
            if row.group == "yesno" or row.storage_type == DB.StorageType.Integer:
                preset[param_id] = fm.CurrentType.AsInteger(row.param)
            elif row.storage_type == DB.StorageType.Double:
                preset[param_id] = fm.CurrentType.AsDouble(row.param)
            elif row.storage_type == DB.StorageType.String:
                preset[param_id] = fm.CurrentType.AsString(row.param)
        return preset

    def _do_save_preset(self):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument:
            return
        preset = self._capture_preset(doc)
        self._presets[doc.Title] = preset
        forms.alert(_t("AlertPresetSaved").format(len(preset)))

    def _do_restore_preset(self):
        doc = revit.doc
        if doc is None or not doc.IsFamilyDocument:
            return
        preset = self._presets.get(doc.Title)
        if not preset:
            return
        fm = doc.FamilyManager
        with revit.Transaction("FamSlide: Restore Preset", doc=doc):
            for row in self._rows:
                if not row.is_editable:
                    continue
                param_id = famslide_paramutils.get_elementid_value(row.param.Id)
                if param_id not in preset:
                    continue
                value = preset[param_id]
                try:
                    if (
                        row.group == "yesno"
                        or row.storage_type == DB.StorageType.Integer
                    ):
                        fm.Set(row.param, int(value))
                    elif row.storage_type == DB.StorageType.Double:
                        fm.Set(row.param, float(value))
                    elif row.storage_type == DB.StorageType.String:
                        fm.Set(row.param, value)
                except Exception:
                    logger.exception(
                        "FamSlide: could not restore preset value for '{}'".format(
                            row.name
                        )
                    )
                    continue
        revit.uidoc.RefreshActiveView()


# ---------------------------------------------------------------------
# Reactive refresh: fires on parameter edits, undo/redo, and switching
# between open family documents (view-activated covers window
# switches). Runs in a valid Revit API context, so it is safe for
# ui.refresh_from_document() to touch Revit data here.
# ---------------------------------------------------------------------
@events.handle("doc-changed", "view-activated", "doc-opened")
def famslide_on_revit_event(sender, args):
    if ui is not None:
        ui.refresh_from_document()


def _gate_family_editor():
    doc = revit.doc
    if doc is None:
        forms.alert(_t("AlertNoActiveDocument"), exitscript=True)
    if not doc.IsFamilyDocument:
        forms.alert(_t("AlertFamilyEditorOnly"), exitscript=True)


if __name__ == "__main__":
    if ui is not None:
        # already open from a previous click under the persistent
        # engine - just bring it forward instead of opening a second
        # copy (which would double-subscribe the doc-changed hook).
        ui.Activate()
    else:
        _gate_family_editor()
        ui = FamSlideWindow("FamSlideWindow.xaml")
        ui.show(modal=False)
