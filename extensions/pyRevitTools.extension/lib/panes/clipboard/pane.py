# -*- coding: utf-8 -*-
import re
import pickle

from pyrevit import forms, revit, op, script
from pyrevit import DB
from pyrevit.revit.events import execute_in_revit_context
from pyrevit.compat import get_elementid_value_func

from match.match_utils import (
    PropKeyValue,
    get_source_properties,
    paste_props,
)
from match.filter_utils import (
    dissect_parameter_filter,
    get_color_source_parameter,
    get_most_common_ogs_brush,
    get_contrasting_brush,
    get_ogs_from_prop_in_view,
)

get_elementid_value = get_elementid_value_func()

MAX_HISTORY_ITEMS = 50

_DIR = op.dirname(op.abspath(__file__))
_ICONS_XAML = op.join(_DIR, "clipboard.Icons.xaml")
_CONTENT_XAML = op.join(_DIR, "clipboard_content.xaml")
_WINDOW_XAML = op.join(_DIR, "clipboard_window.xaml")
_PAGE_XAML = op.join(_DIR, "clipboard_page.xaml")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


_CONTENT_MARKER = "@@CONTENT@@"


def _compose_xaml(root_xaml_path):
    """Return root XAML text with the shared clipboard grid injected."""
    with open(root_xaml_path, "rb") as f:
        root = f.read().decode("utf-8-sig")
    with open(_CONTENT_XAML, "rb") as f:
        content = f.read().decode("utf-8-sig")
    if _CONTENT_MARKER not in root:
        raise ValueError(
            "{} has no {} marker".format(op.basename(root_xaml_path), _CONTENT_MARKER)
        )
    return root.replace(_CONTENT_MARKER, content)


def _merge_locale(control):
    """Merge the clipboard locale ResourceDictionary into a form."""
    from pyrevit.userconfig import user_config

    base = op.join(_DIR, "clipboard_ui")
    locale_path = "{}.ResourceDictionary.{}.xaml".format(base, user_config.user_locale)
    if not op.exists(locale_path):
        locale_path = "{}.ResourceDictionary.en_us.xaml".format(base)
    if op.exists(locale_path):
        control.merge_resource_dict(locale_path)


# ─────────────────────────────────────────────────────────────────────────────
# WPF-bindable list-view row backed by a PropKeyValue
# ─────────────────────────────────────────────────────────────────────────────


class ParameterItem(forms.Reactive):
    """One row in the history list view."""

    def __init__(self, pkv):
        self._pkv = pkv
        self._selected = False

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
            self.OnPropertyChanged("IsSelected")

    @property
    def source_prop(self):
        return self._pkv


# ─────────────────────────────────────────────────────────────────────────────
# Shared clipboard logic — mixed into the panel and the recall window
# ─────────────────────────────────────────────────────────────────────────────


class _ClipboardLogic(object):
    """Behaviour of the clipboard parameter UI, mixed into a WPF form.

    The host form loads XAML composed from clipboard_content.xaml. It calls
    `_init_clipboard` before loading, because handlers can fire during load,
    and `_finish_clipboard` after.

    Important:
        Must not derive from a WPF type: CPython forms cannot subclass them.
    """

    def _init_clipboard(self, is_recall=False, target_type=None, memfile=None):
        """Set the state the XAML handlers read.

        Args:
            is_recall (bool): False = full panel mode; True = recall mode.
                In recall mode the view-filter and filter-element load buttons
                are hidden and load_from_element opens select_parameters with
                preselect.
            target_type (str): "Elements" or "Views"; recall mode only, saved
                back to the memory file on close.
            memfile (str): absolute path to the pickle memory file; recall
                mode only.
        """
        self._is_recall = is_recall
        self._recall_target_type = target_type
        self._memfile = memfile
        self._items = []
        self._visible_items = []

    def _finish_clipboard(self):
        """Merge icon and locale dictionaries and apply recall-mode layout."""
        if not hasattr(self, "_is_recall"):
            raise RuntimeError("_init_clipboard must run before the form loads")
        self.merge_resource_dict(_ICONS_XAML)
        _merge_locale(self)

        if self._is_recall:
            self.loadViewFiltersBtn.Visibility = forms.WPF_COLLAPSED
            self.loadFilterElemBtn.Visibility = forms.WPF_COLLAPSED
            self.categoryFilterCheck.Visibility = forms.WPF_COLLAPSED
            self.categoryColumn.Width = 0

    # ── public API ───────────────────────────────────────────────────────────

    def populate(self, props, all_selected=True):
        """Fill the list with PropKeyValue items, optionally all selected."""
        self._items = [ParameterItem(p) for p in props]
        for item in self._items:
            item.IsSelected = all_selected
        self._refresh_list()
        self._update_ui_state()

    # ── history management (panel mode) ─────────────────────────────────────

    def _add_to_history(self, props):
        """
        Prepend props to history, uncheck everything, enforce MAX_HISTORY_ITEMS.
        Called after any of the three load-source actions.
        """
        if not props:
            return
        new_items = [ParameterItem(p) for p in props]
        new_props = [ni.source_prop for ni in new_items]
        filtered_old = [
            item for item in self._items if item.source_prop not in new_props
        ]
        self._items = (new_items + filtered_old)[:MAX_HISTORY_ITEMS]
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
            self._visible_items = list(self._items)
            self.paramListView.ItemsSource = self._visible_items
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

        self._visible_items = items
        self.paramListView.ItemsSource = items

    def _set_check_states(self, state=None, flip=False):
        """
        Apply a uniform check state to all visible rows.
        Deduplication: only the first occurrence of each parameter name
        is checked; later duplicates are forced unchecked.
        """
        visible = self._visible_items
        if state is True:
            # build set of already-selected names from ALL items
            seen = set()
            for item in self._items:
                if item.IsSelected:
                    seen.add(item.Name)
            for item in visible:
                if item.Name in seen and not item.IsSelected:
                    item.IsSelected = False
                else:
                    item.IsSelected = (not item.IsSelected) if flip else state
                    if item.IsSelected:
                        seen.add(item.Name)
        else:
            for item in visible:
                item.IsSelected = (not item.IsSelected) if flip else state
        # Enforce deduplication across all items (e.g. after toggle_all while searching)
        seen = set()
        for item in self._items:
            if item.IsSelected:
                if item.Name in seen:
                    item.IsSelected = False
                else:
                    seen.add(item.Name)
        self._update_ui_state()

    def _update_ui_state(self):
        """Enable paste buttons only when at least one row is checked."""
        has_checked = any(i.IsSelected for i in self._items)
        self.pasteSingleBtn.IsEnabled = has_checked
        self.pasteRectBtn.IsEnabled = has_checked
        self.pasteSelBtn.IsEnabled = has_checked

    # ── load-source handlers ─────────────────────────────────────────────────
    # NOTE: pick_element / get_source_properties are called directly here
    # (not via execute_in_revit_context) because pyrevit's WPFPanel allows Revit picks
    # from WPF event handlers.  Only write-operations (Transactions) require
    # the ExternalEvent mechanism.

    def load_from_element(self, sender, args):
        sel = revit.get_selection()
        elem = sel[0] if len(sel) == 1 else revit.pick_element()
        if not elem:
            return

        if self._is_recall:
            # Open parameter picker with current recall params pre-checked.
            # The returned selection replaces the current list.
            preselect = [i.source_prop.name for i in self._items]
            props = get_source_properties(elem, preselect=preselect)
            if props:
                self._items = [ParameterItem(p) for p in props]
                for item in self._items:
                    item.IsSelected = True
                self._refresh_list()
                self._update_ui_state()
        else:
            props = get_source_properties(elem)
            count = len(props)
            self._add_to_history(props)
            for i in range(min(count, len(self._items))):
                self._items[i].IsSelected = True
            self._update_ui_state()

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
        sel = revit.get_selection()
        elem = sel[0] if len(sel) == 1 else revit.pick_element()
        if not elem:
            return
        param_id, _ = get_color_source_parameter(revit.doc, revit.active_view, elem)
        if not param_id:
            return
        try:
            tparam = revit.query.get_param(elem, param_id)
            if not tparam:
                return
            value = revit.query.get_param_value(tparam)
            props = [
                PropKeyValue(
                    name=tparam.Definition.Name,
                    datatype=tparam.StorageType,
                    value=get_elementid_value(value)
                    if isinstance(value, DB.ElementId)
                    else value,
                    istype=False,
                    display_value=tparam.AsValueString() or str(value),
                    categories=[elem.Category],
                )
            ]
            self._add_to_history(props)
            self._items[0].IsSelected = True
            self._update_ui_state()
        except Exception:
            pass

    # ── paste handlers ───────────────────────────────────────────────────────

    def paste_single(self, sender, args):
        """Paste checked parameters by picking elements one at a time (loops)."""
        props = self._selected_props()
        bg, fg = None, None
        if len(props) == 1:
            ogs = get_ogs_from_prop_in_view(revit.doc, revit.active_view, props[0])
            if ogs:
                bg = get_most_common_ogs_brush(ogs)
                fg = get_contrasting_brush(bg)
        if props:
            execute_in_revit_context(
                paste_props,
                props,
                "single",
                bool(self.categoryFilterCheck.IsChecked),
                background=bg,
                foreground=fg,
            )

    def paste_rectangle(self, sender, args):
        props = self._selected_props()
        bg, fg = None, None
        if len(props) == 1:
            ogs = get_ogs_from_prop_in_view(revit.doc, revit.active_view, props[0])
            if ogs:
                bg = get_most_common_ogs_brush(ogs)
                fg = get_contrasting_brush(bg)
        if props:
            execute_in_revit_context(
                paste_props,
                props,
                "rectangle",
                bool(self.categoryFilterCheck.IsChecked),
                background=bg,
                foreground=fg,
            )

    def paste_selection(self, sender, args):
        props = self._selected_props()
        if props:
            execute_in_revit_context(
                paste_props,
                props,
                "selection",
                bool(self.categoryFilterCheck.IsChecked),
            )

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
            self.regexToggle_b.Content = self.FindResource("regexIcon")
        else:
            self.regexToggle_b.Content = self.FindResource("filterIcon")
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
            self.clrsearch_b.Visibility = forms.WPF_VISIBLE
        else:
            self.clrsearch_b.Visibility = forms.WPF_COLLAPSED
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


# ─────────────────────────────────────────────────────────────────────────────
# Dockable panel
# ─────────────────────────────────────────────────────────────────────────────


class MatchHistoryClipboard(_ClipboardLogic, forms.WPFPanel):
    """Dockable panel keeping the history of matched parameters.

    Registered by the extension startup and opened from the Match History
    Clipboard button.
    """

    panel_title = "pyRevit MatchHistory Clipboard"
    panel_id = "0f3a0866-0123-4178-9f2c-121961bd292c"
    panel_source = _PAGE_XAML
    resolve_theme = True

    def __init__(self):
        self._init_clipboard(is_recall=False)
        forms.WPFPanel.__init__(self)
        self._finish_clipboard()

    def load_xaml(self, xaml_source, literal_string=False):
        """Compose the clipboard template before loading it as a page."""
        if not literal_string and xaml_source == _PAGE_XAML:
            xaml_source = _compose_xaml(xaml_source)
            literal_string = True
        forms.WPFPanel.load_xaml(self, xaml_source, literal_string=literal_string)


# ─────────────────────────────────────────────────────────────────────────────
# Modeless recall window
# ─────────────────────────────────────────────────────────────────────────────


class RecallWindow(_ClipboardLogic, forms.WPFWindow):
    """Modeless window recalling the parameters saved by Match Properties.

    Opened by Match Properties in config mode. Closing it pickles the checked
    rows back to the memory file.
    """

    resolve_theme = True

    def __init__(self, target_type, initial_props, memfile):
        self._init_clipboard(
            is_recall=True,
            target_type=target_type,
            memfile=memfile,
        )
        forms.WPFWindow.__init__(self, _compose_xaml(_WINDOW_XAML), literal_string=True)
        self._finish_clipboard()
        self.populate(initial_props, all_selected=True)
        script.restore_window_position(self, "MatchPropertiesRecall")

    def _on_closing(self, sender, args):
        script.save_window_position(self, "MatchPropertiesRecall")
        self._save_recall()

    def _save_recall(self):
        """Persist selected props to the memory file."""
        c = self
        if not c._memfile:
            return
        selected = [i.source_prop for i in c._items if i.IsSelected]
        if not selected:
            return

        serializable = []
        for p in selected:
            serializable.append(
                PropKeyValue(
                    name=p.name,
                    datatype=p.datatype,
                    value=p.value,
                    istype=p.istype,
                    display_value=p.display_value,
                )
            )
        try:
            with open(c._memfile, "wb") as f:
                pickle.dump((c._recall_target_type, serializable), f, 2)
        except Exception as ex:
            command_logger = getattr(self, "recall_logger", None)
            (command_logger or script.get_logger()).warning(
                "Failed saving matched properties to memory | %s", ex
            )
