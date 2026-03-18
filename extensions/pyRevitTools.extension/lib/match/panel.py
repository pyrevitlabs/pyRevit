# -*- coding: utf-8 -*-
import re

from pyrevit import script, forms, revit, op
from pyrevit import UI
from pyrevit.revit.events import _GenericExternalEventHandler
from pyrevit.framework import ComponentModel

from match_utils import (
    match_prop,
    PropKeyValue,
    get_source_properties,
    safe_get_parameter,
    PickByCategorySelectionFilter,
)
from filter_utils import get_most_common_filter_parameter, dissect_parameter_filter

logger = script.get_logger()

MAX_HISTORY_ITEMS = 50


# ─────────────────────────────────────────────────────────────────────────────
# INotifyPropertyChanged base — required for two-way checkbox binding in WPF
# ─────────────────────────────────────────────────────────────────────────────


class _INotifyBase(ComponentModel.INotifyPropertyChanged):
    def __init__(self):
        self._handlers = []

    def add_PropertyChanged(self, handler):
        self._handlers.append(handler)

    def remove_PropertyChanged(self, handler):
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _notify(self, prop_name):
        ev_args = ComponentModel.PropertyChangedEventArgs(prop_name)
        for h in self._handlers:
            h(self, ev_args)


# ─────────────────────────────────────────────────────────────────────────────
# WPF-bindable list-view row backed by a PropKeyValue
# ─────────────────────────────────────────────────────────────────────────────


class ParameterItem(_INotifyBase):
    """One row in the history list view."""

    def __init__(self, pkv):
        _INotifyBase.__init__(self)
        self._pkv = pkv
        self._selected = False

    # -- display properties (read by WPF bindings) --

    @property
    def Name(self):
        return self._pkv.name or ""

    @property
    def DisplayValue(self):
        dv = self._pkv.display_value
        if dv is None:
            return str(self._pkv.value) if self._pkv.value is not None else ""
        return dv

    @property
    def Category(self):
        """Single category name, 'multiple', or em-dash when unknown."""
        cats = self._pkv.categories or []
        if not cats:
            return "unknown"
        if len(cats) == 1:
            c = cats[0]
            return c.Name if hasattr(c, "Name") else str(c)
        return "multiple"

    # -- checkable state with WPF change notification --

    @property
    def IsSelected(self):
        return self._selected

    @IsSelected.setter
    def IsSelected(self, value):
        if self._selected != value:
            self._selected = value
            self._notify("IsSelected")

    # -- access to the underlying PropKeyValue for paste operations --

    @property
    def source_prop(self):
        return self._pkv


# ─────────────────────────────────────────────────────────────────────────────
# Dockable pane
# ─────────────────────────────────────────────────────────────────────────────


class MatchHistoryClipboard(forms.WPFPanel):
    panel_title = "pyRevit MatchHistory Clipboard"
    panel_id = "0f3a0866-0123-4178-9f2c-121961bd292c"
    panel_source = op.join(op.dirname(__file__), "clipboard_pane_ui.xaml")

    def __init__(self):
        forms.WPFPanel.__init__(self)
        self._handler = _GenericExternalEventHandler()
        self._ext_event = UI.ExternalEvent.Create(self._handler)
        self._items = []  # ordered list of ParameterItem (full history)

    # ── external-event plumbing ──────────────────────────────────────────────

    def _run_in_revit(self, func, *args, **kwargs):
        """Schedule func(*args, **kwargs) to run in the next Revit event loop."""
        self._handler.func = func
        self._handler.args = args
        self._handler.kwargs = kwargs
        self._ext_event.Raise()

    # ── history management ───────────────────────────────────────────────────

    def _add_to_history(self, props):
        """
        Prepend props to history, uncheck everything, enforce MAX_HISTORY_ITEMS.
        Called after any of the three load-source actions.
        """
        if not props:
            return
        new_items = [ParameterItem(p) for p in props]
        self._items = (new_items + self._items)[:MAX_HISTORY_ITEMS]
        for item in self._items:
            item.IsSelected = False
        self._refresh_list()
        self._update_ui_state()

    def _selected_props(self):
        """Return PropKeyValue objects for every checked history row."""
        return [item.source_prop for item in self._items if item.IsSelected]

    # ── list display / search filtering ─────────────────────────────────────

    def _refresh_list(self, search_text=None):
        """
        Rebuild ListView.ItemsSource.
        With no search_text the full history is shown.
        With search_text either regex or substring match is applied to
        both the parameter name and display value.
        """
        if not search_text:
            self.paramListView.ItemsSource = list(self._items)
            return

        use_regex = bool(self.regexToggle_b.IsChecked)
        if use_regex:
            try:
                pat = re.compile(search_text, re.IGNORECASE)
                items = [
                    i
                    for i in self._items
                    if pat.search(i.Name) or pat.search(i.DisplayValue)
                ]
            except re.error:
                items = list(self._items)  # invalid pattern → show all
        else:
            low = search_text.lower()
            items = [
                i
                for i in self._items
                if low in i.Name.lower() or low in i.DisplayValue.lower()
            ]

        self.paramListView.ItemsSource = items

    def _set_check_states(self, state=None, flip=False):
        """
        Apply a uniform check state to all visible rows.
        Deduplication: only the first occurrence of each parameter name
        is checked; later duplicates are forced unchecked.
        """
        seen = set()
        source = self.paramListView.ItemsSource or []
        for item in source:
            if item.Name not in seen:
                seen.add(item.Name)
                item.IsSelected = (not item.IsSelected) if flip else state
            else:
                item.IsSelected = False
        self._update_ui_state()

    def _update_ui_state(self):
        """Enable paste buttons only when at least one row is checked."""
        has_checked = any(i.IsSelected for i in self._items)
        self.pasteSingleBtn.IsEnabled = has_checked
        self.pasteRectBtn.IsEnabled = has_checked
        self.pasteSelBtn.IsEnabled = has_checked

    # ── load-source handlers (Button Click events from XAML) ─────────────────
    # NOTE: pick_element / get_source_properties are called directly here
    # (not via _run_in_revit) because pyrevit's WPFPanel allows Revit picks
    # from WPF event handlers.  Only write-operations (Transactions) require
    # the ExternalEvent mechanism.

    def load_from_element(self, sender, args):
        """Pick an element, choose parameters interactively, add to history."""
        sel = revit.get_selection()
        elem = sel[0] if len(sel) == 1 else revit.pick_element()
        if not elem:
            return
        props = get_source_properties(elem)  # opens pyrevit parameter-picker dialog
        self._add_to_history(props)

    def load_from_view_filters(self, sender, args):
        """Read all equals-filter parameter values from the active view."""
        view_filters = revit.query.get_view_filters(revit.active_view)
        props = []
        for f in view_filters:
            info = dissect_parameter_filter(revit.doc, f)
            if not info:
                continue
            props.append(
                PropKeyValue(
                    name=info["parameter_name"],
                    datatype=info["storage_type"],
                    value=info["value"],
                    istype=False,
                    display_value=info["display_value"],
                    categories=info["categories"],
                )
            )
        self._add_to_history(props)

    def load_from_filter_and_element(self, sender, args):
        """
        Read the value of the most-common filter parameter from a picked element.
        Useful for quickly setting up a match from a 'key' parameter.
        """
        param_id = get_most_common_filter_parameter(revit.doc, revit.active_view)
        sel = revit.get_selection()
        elem = sel[0] if len(sel) == 1 else revit.pick_element()
        if not elem:
            return
        try:
            tparam = safe_get_parameter(elem, param_id)
            if not tparam:
                return
            value = revit.query.get_param_value(tparam)
            props = [
                PropKeyValue(
                    name=tparam.Definition.Name,
                    datatype=tparam.StorageType,
                    value=value,
                    istype=False,
                    display_value=tparam.AsValueString() or str(value),
                    categories=[elem.Category]
                )
            ]
            self._add_to_history(props)
        except Exception as ex:
            logger.warning("load_from_filter_and_element: %s", ex)

    # ── paste handlers ───────────────────────────────────────────────────────

    def paste_single(self, sender, args):
        """Paste checked parameters by picking elements one at a time (loops)."""
        props = self._selected_props()
        if props:
            self._run_in_revit(self._do_paste, props, "single")

    def paste_rectangle(self, sender, args):
        """Paste checked parameters to elements inside a drawn rectangle (loops)."""
        props = self._selected_props()
        if props:
            self._run_in_revit(self._do_paste, props, "rectangle")

    def paste_selection(self, sender, args):
        """Paste checked parameters to the current Revit selection (one-shot)."""
        props = self._selected_props()
        if props:
            self._run_in_revit(self._do_paste, props, "selection")

    def _do_paste(self, source_props, paste_mode):
        """
        Core paste routine — runs inside an ExternalEvent (Revit API context).
        paste_mode: "single" | "rectangle" | "selection"
        """
        # Build category filter if the checkbox is ticked and categories are known
        pick_filter = None
        if bool(self.categoryFilterCheck.IsChecked):
            cat_ids = set()
            for p in source_props:
                for c in p.categories or []:
                    if hasattr(c, "Id"):
                        cat_ids.add(c.Id)
            if cat_ids:
                pick_filter = PickByCategorySelectionFilter(list(cat_ids))

        # Status-bar message shown to the user while picking
        if len(source_props) == 1:
            title = "Match: {} = {}".format(
                source_props[0].name,
                source_props[0].display_value or str(source_props[0].value),
            )
        else:
            title = "Pick elements to match {} parameter(s):".format(len(source_props))

        with forms.WarningBar(title=title):
            while True:
                dest_elements = []

                if paste_mode == "single":
                    elem = revit.pick_element()
                    if elem:
                        dest_elements = [elem]

                elif paste_mode == "rectangle":
                    dest_elements = revit.pick_rectangle(pick_filter=pick_filter)

                elif paste_mode == "selection":
                    dest_elements = list(revit.get_selection())

                if not dest_elements:
                    break  # user cancelled / nothing selected

                for dest in dest_elements:
                    dest_type = revit.query.get_type(dest)
                    with revit.Transaction("Match Properties"):
                        # type parameters first so instance params can reference them
                        match_prop(
                            dest, dest_type, [p for p in source_props if p.istype]
                        )
                        match_prop(
                            dest, dest_type, [p for p in source_props if not p.istype]
                        )

                if paste_mode == "selection":
                    break  # selection is one-shot, not a pick loop

    # ── check / search UI handlers ───────────────────────────────────────────

    def check_all(self, sender, args):
        self._set_check_states(state=True)

    def uncheck_all(self, sender, args):
        self._set_check_states(state=False)

    def toggle_all(self, sender, args):
        self._set_check_states(flip=True)

    def toggle_regex(self, sender, args):
        """Switch between substring and regex search; swap the button icon."""
        if bool(self.regexToggle_b.IsChecked):
            self.regexToggle_b.Content = self.Resources["regexIcon"]
        else:
            self.regexToggle_b.Content = self.Resources["filterIcon"]
        text = self.search_tb.Text.strip()
        self._refresh_list(search_text=text if text else None)
        self.search_tb.Focus()

    def clear_search(self, sender, args):
        self.search_tb.Text = ""
        self.search_tb.Focus()

    def search_changed(self, sender, args):
        """TextChanged handler — show/hide the clear button, refresh list."""
        text = self.search_tb.Text
        if text:
            self.show_element(self.clrsearch_b)
        else:
            self.hide_element(self.clrsearch_b)
        stripped = text.strip()
        self._refresh_list(search_text=stripped if stripped else None)

    def checkbox_click(self, sender, args):
        """
        When a row is checked, uncheck all other rows that share the same
        parameter name — prevents duplicate parameters being applied twice.
        """
        clicked = sender.DataContext
        if not clicked:
            return
        if clicked.IsSelected:
            for item in self._items:
                if item is not clicked and item.Name == clicked.Name:
                    item.IsSelected = False
        self._update_ui_state()
