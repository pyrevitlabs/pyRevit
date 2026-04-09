# -*- coding: utf-8 -*-
"""Manage project keynotes — unified tree with hierarchy controls.

Features:
- Single hierarchical tree (no separate category sidebar)
- Indent / Outdent to promote or demote nodes (Tab / Shift+Tab)
- Move Up / Move Down to reorder siblings (Ctrl+Up / Ctrl+Down)
- Drag-and-drop to reparent across the tree
- Search with smart filters
- Keyboard shortcuts (F2, F5, Ctrl+N, Ctrl+D, Del, Tab, Shift+Tab)

Shift+Click:
Reset window configurations and open.
"""

# pylint: disable=E0401,W0613,C0111,C0103,C0302,W0703
# pylint: disable=raise-missing-from
import os
import os.path as op
import shutil
import math
import uuid
from collections import defaultdict, OrderedDict
from natsort import natsorted

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.framework import System, Windows
from System.Windows.Interop import WindowInteropHelper, HwndSource
from System.Diagnostics import Process as SysProcess
from System.Windows.Threading import DispatcherTimer
from System import TimeSpan

from pyrevit.runtime.types import DocumentEventUtils

from pyrevit.interop import adc

import keynotesdb as kdb

__persistentengine__ = True

logger = script.get_logger()
output = script.get_output()


# =============================================================================
# ADC MONKEY-PATCH — fix ReadOnlyList subscripting on .NET Framework
# =============================================================================
# pyRevit's adc.py uses [0] on .NET ReadOnlyList objects returned by the
# Desktop Connector API.  This works on .NET 8 (Revit 2025+) but fails on
# .NET Framework 4.x (Revit 2023/2024) because IronPython can't subscript
# ReadOnlyList[T] with [].  The fix: iterate or use .Item[0] / LINQ First().


def _safe_first(collection):
    """Safely get first element from a .NET collection that may not
    support Python [] subscripting (ReadOnlyList, IList, etc.)."""
    if collection is None:
        return None
    # Try normal indexing first (.NET 8 / CPython)
    try:
        return collection[0]
    except TypeError:
        pass
    # Try .Item[] indexer (.NET Framework generic collections)
    try:
        return collection.Item[0]
    except (TypeError, AttributeError):
        pass
    # Fall back to iteration
    try:
        for item in collection:
            return item
    except TypeError:
        pass
    return None


def _patched_get_item(adc_svc, path):
    """Patched version of adc._get_item that handles ReadOnlyList."""
    import os.path as _op

    path = adc._ensure_local_path(adc_svc, path)
    if not _op.isfile(path):
        raise Exception("Path does not point to a file")
    res = adc_svc.GetItemsByWorkspacePaths([path])
    if not res:
        raise Exception("Cannot find item in any ADC drive")
    first = _safe_first(res)
    if first is None:
        raise Exception("ADC returned empty result for path")
    return first.Item


def _patched_get_item_lockstatus(adc_svc, item):
    """Patched version of adc._get_item_lockstatus."""
    res = adc_svc.GetLockStatus([item.Id])
    if res and res.Status:
        return _safe_first(res.Status)
    return None


def _patched_get_item_property_value(adc_svc, drive, item, prop_name):
    """Patched version of adc._get_item_property_value."""
    for prop_def in adc._get_drive_properties(adc_svc, drive):
        if prop_def.DisplayName == prop_name:
            res = adc_svc.GetProperties([item.Id], [prop_def.Id])
            if res:
                return _safe_first(res.Values)
    return None


def _patched_get_item_property_id_value(adc_svc, drive, item, prop_id):
    """Patched version of adc._get_item_property_id_value."""
    for prop_def in adc._get_drive_properties(adc_svc, drive):
        if prop_def.Id == prop_id:
            res = adc_svc.GetProperties([item.Id], [prop_def.Id])
            if res:
                return _safe_first(res.Values)
    return None


# Apply patches (only on .NET Framework, only once per engine session)
if not HOST_APP.is_newer_than("2024") and not getattr(
    adc, "_readonlylist_patched", False
):
    adc._get_item = _patched_get_item
    adc._get_item_lockstatus = _patched_get_item_lockstatus
    adc._get_item_property_value = _patched_get_item_property_value
    adc._get_item_property_id_value = _patched_get_item_property_id_value
    adc._readonlylist_patched = True


# =============================================================================
# EXTERNAL EVENT HANDLER (for modeless window Revit API access)
# =============================================================================
# Modeless WPF windows cannot start Revit transactions directly.
# All write operations (transactions, PostCommand) are queued here and
# executed on Revit's main thread via ExternalEvent.


class RevitActionHandler(UI.IExternalEventHandler):
    """Queues callables and runs them inside Revit's valid API context."""

    def __init__(self):
        self._queue = []

    def queue(self, action, callback=None, window=None):
        """Add an action (and optional WPF-thread callback) to the queue."""
        self._queue.append((action, callback, window))

    def Execute(self, app):
        """Called by Revit on the main thread when the event fires."""
        while self._queue:
            action, callback, window = self._queue.pop(0)
            try:
                action()
            except Exception as ex:
                logger.error("RevitActionHandler | %s" % ex)
                try:
                    if window and window.IsLoaded:
                        window.Dispatcher.Invoke(
                            System.Action(lambda e=str(ex): forms.alert(e))
                        )
                except Exception as disp_ex:
                    logger.debug("Failed to display error in window | %s" % disp_ex)
            if callback:
                try:
                    if window and window.IsLoaded:
                        window.Dispatcher.Invoke(System.Action(callback))
                    else:
                        callback()
                except Exception as cbex:
                    logger.debug("Callback failed | %s" % cbex)

    def GetName(self):
        return "KeynoteManagerHandler"


# Module-level handler + event (persist across window open/close)
_ext_handler = RevitActionHandler()
_ext_event = UI.ExternalEvent.Create(_ext_handler)

# Singleton — only one keynote manager window at a time
_active_window = None


# =============================================================================
# HELPERS
# =============================================================================


def get_keynote_pcommands():
    return list(
        reversed(
            [
                x
                for x in coreutils.get_enum_values(UI.PostableCommand)
                if str(x).endswith("Keynote")
            ]
        )
    )


def _find_siblings(flat_keynotes, target_parent_key):
    """Return natsorted list of keynotes sharing the same parent_key."""
    return natsorted(
        [k for k in flat_keynotes if k.parent_key == target_parent_key],
        key=lambda x: x.key,
    )


def _find_parent_of(all_categories, all_keynotes, child):
    """Find the RKeynote/category object that is the parent of 'child'."""
    pkey = child.parent_key
    if not pkey:
        return None
    for cat in all_categories:
        if cat.key == pkey:
            return cat
    for kn in all_keynotes:
        if kn.key == pkey:
            return kn
    return None


# =============================================================================
# EDIT RECORD WINDOW (unchanged from pyRevit — works with EditRecord.xaml)
# =============================================================================


class EditRecordWindow(forms.WPFWindow):
    """Dialog for adding/editing a single keynote or category record."""

    def __init__(
        self, owner, conn, mode, rkeynote=None, rkey=None, text=None, pkey=None
    ):
        forms.WPFWindow.__init__(self, "EditRecord.xaml")
        self.Owner = owner
        self._res = None
        self._commited = False
        self._reserved_key = None

        self._conn = conn
        self._mode = mode
        self._cat = False
        self._rkeynote = rkeynote
        self._rkey = rkey
        self._text = text
        self._pkey = pkey

        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = "Add Group"
            self.recordKeyTitle.Text = "Create a unique group key"
            self.applyChanges.Content = "Add Group"

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = "Edit Group"
            self.recordKeyTitle.Text = "Group key (read-only)"
            self.applyChanges.Content = "Save Changes"
            self.recordKey.IsEnabled = False
            if self._rkeynote and self._rkeynote.key:
                kdb.begin_edit(self._conn, self._rkeynote.key, category=True)

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = "Add Keynote"
            self.recordKeyTitle.Text = "Create a unique keynote key"
            self.applyChanges.Content = "Add Keynote"

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = "Edit Keynote"
            self.recordKeyTitle.Text = "Keynote key (read-only)"
            self.applyChanges.Content = "Save Changes"
            self.recordKey.IsEnabled = False
            self.recordParent.IsEnabled = True
            if self._rkeynote and self._rkeynote.key:
                kdb.begin_edit(self._conn, self._rkeynote.key, category=False)

        if self._rkeynote:
            self.active_key = self._rkeynote.key
            self.active_text = self._rkeynote.text
            self.active_parent_key = self._rkeynote.parent_key
        if self._rkey:
            self.active_key = self._rkey
        if self._text:
            self.active_text = self._text
        if self._pkey:
            self.active_parent_key = self._pkey

        self.recordText.Focus()
        self.recordText.SelectAll()

    @property
    def active_key(self):
        if self.recordKey.Content and "\u25cf" not in self.recordKey.Content:
            return self.recordKey.Content

    @active_key.setter
    def active_key(self, value):
        self.recordKey.Content = value

    @property
    def active_text(self):
        return self.recordText.Text

    @active_text.setter
    def active_text(self, value):
        self.recordText.Text = value.strip()

    @property
    def active_parent_key(self):
        return self.recordParent.Content

    @active_parent_key.setter
    def active_parent_key(self, value):
        self.recordParent.Content = value

    def commit(self):
        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            if not self.active_key:
                forms.alert("Please provide a unique key.")
                return False
            if not self.active_text.strip():
                forms.alert("Please provide a title.")
                return False
            try:
                self._res = kdb.add_category(
                    self._conn, self.active_key, self.active_text
                )
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            if not self.active_text:
                forms.alert("Title cannot be empty.")
                return False
            try:
                if self.active_text != self._rkeynote.text:
                    kdb.update_category_title(
                        self._conn, self.active_key, self.active_text
                    )
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            if not self.active_key:
                forms.alert("Please provide a unique key.")
                return False
            if not self.active_text:
                forms.alert("Please provide keynote text.")
                return False
            if not self.active_parent_key:
                forms.alert("Please select a parent.")
                return False
            try:
                self._res = kdb.add_keynote(
                    self._conn,
                    self.active_key,
                    self.active_text,
                    self.active_parent_key,
                )
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            if not self.active_text:
                forms.alert("Keynote text cannot be empty.")
                return False
            try:
                if self.active_text != self._rkeynote.text:
                    kdb.update_keynote_text(
                        self._conn, self.active_key, self.active_text
                    )
                if self.active_parent_key != self._rkeynote.parent_key:
                    kdb.move_keynote(
                        self._conn, self.active_key, self.active_parent_key
                    )
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        return True

    def show(self):
        self.ShowDialog()
        return self._res

    def pick_key(self, sender, args):
        if self._reserved_key:
            try:
                kdb.release_key(self._conn, self._reserved_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
        try:
            categories = kdb.get_categories(self._conn)
            keynotes = kdb.get_keynotes(self._conn)
            locks = kdb.get_locks(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        reserved_keys = [x.key for x in categories]
        reserved_keys.extend([x.key for x in keynotes])
        reserved_keys.extend([x.LockTargetRecordKey for x in locks])
        new_key = forms.ask_for_unique_string(
            prompt="Enter a unique key:",
            title=self.Title,
            reserved_values=reserved_keys,
            owner=self,
        )
        if new_key:
            try:
                kdb.reserve_key(self._conn, new_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
            self._reserved_key = new_key
            self.active_key = new_key

    def pick_parent(self, sender, args):
        categories = kdb.get_categories(self._conn)
        keynotes = kdb.get_keynotes(self._conn)
        available = [x.key for x in categories]
        available.extend([x.key for x in keynotes])
        if self.active_key in available:
            available.remove(self.active_key)
        new_parent = forms.SelectFromList.show(
            natsorted(available), title="Select Parent", multiselect=False
        )
        if new_parent:
            try:
                kdb.reserve_key(self._conn, self.active_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
            self._reserved_key = self.active_key
            self.active_parent_key = new_parent

    def to_upper(self, sender, args):
        self.active_text = self.active_text.upper()

    def to_lower(self, sender, args):
        self.active_text = self.active_text.lower()

    def to_title(self, sender, args):
        self.active_text = self.active_text.title()

    def to_sentence(self, sender, args):
        self.active_text = self.active_text.capitalize()

    def select_template(self, sender, args):
        template = forms.SelectFromList.show(
            ["RESERVED", "DO NOT USE"], title="Select Template", owner=self
        )
        if template:
            self.active_text = template

    def translate(self, sender, args):
        forms.alert("Translation feature coming soon.")

    def apply_changes(self, sender, args):
        self._commited = self.commit()
        if self._commited:
            self.Close()

    def cancel_changes(self, sender, args):
        self.Close()

    def window_closing(self, sender, args):
        if not self._commited:
            if self._reserved_key:
                try:
                    kdb.release_key(self._conn, self._reserved_key, category=self._cat)
                except Exception:
                    pass
            try:
                kdb.end_edit(self._conn)
            except Exception:
                pass


# =============================================================================
# MAIN KEYNOTE MANAGER WINDOW
# =============================================================================


class KeynoteManagerWindow(forms.WPFWindow):
    """Keynote manager with unified tree and hierarchy controls."""

    def __init__(self, xaml_file_name, reset_config=False):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # Set Revit as the owner window — critical for modeless stability.
        # Without this, WPF's message pump collides with Revit's on focus
        # change, causing hard crashes.
        try:
            wih = WindowInteropHelper(self)
            wih.Owner = SysProcess.GetCurrentProcess().MainWindowHandle
        except Exception as ex:
            logger.debug("WindowInteropHelper failed | %s" % ex)

        # Hook WndProc to intercept WM_MOUSEACTIVATE — prevents the
        # re-entrant activation crash when clicking between Revit and
        # this modeless window.
        self._hwnd_source = None
        self._activation_pending = False
        # Pre-cache .NET types — IronPython cannot resolve System.IntPtr
        # or System.Action from inside a Win32 WndProc callback
        # (LookupGlobalInstruction crash in HwndSubclass.SubclassWndProc).
        self._INTPTR_ZERO = System.IntPtr.Zero
        self._INTPTR_MA_NOACTIVATE = System.IntPtr(self.MA_NOACTIVATE)
        self._BG_PRIORITY = Windows.Threading.DispatcherPriority.Background
        self.SourceInitialized += self._on_source_initialized

        self._kfile = None
        self._kfile_handler = None
        self._kfile_ext = None
        self._conn = None

        self._determine_kfile()
        self._connect_kfile()

        self._cache = []
        self._needs_update = False
        self._config = script.get_config()
        self._used_keysdict = self.get_used_keynote_elements()

        # drag state
        self._drag_start_point = None
        self._is_dragging = False

        # modeless close state
        self._close_pending = False

        self._search_timer = DispatcherTimer()
        # Wait 300ms after last keystroke before filtering.
        self._search_timer.Interval = TimeSpan.FromMilliseconds(300)
        self._search_timer.Tick += self._on_search_timer_tick

        self.load_config(reset_config)
        self._update_full_tree()
        self._update_status_bar()
        self.search_tb.Focus()

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def window_geom(self):
        return (self.Width, self.Height, self.Top, self.Left)

    @window_geom.setter
    def window_geom(self, geom_tuple):
        w, h, t, l = geom_tuple
        self.Width = self.Width if math.isnan(w) else w
        self.Height = self.Height if math.isnan(h) else h
        self.Top = self.Top if math.isnan(t) else t
        self.Left = self.Left if math.isnan(l) else l

    @property
    def search_term(self):
        return self.search_tb.Text

    @search_term.setter
    def search_term(self, value):
        self.search_tb.Text = value

    @property
    def postable_keynote_command(self):
        return get_keynote_pcommands()[self.postcmd_idx]

    @property
    def postcmd_options(self):
        return [self.userknote_rb, self.materialknote_rb, self.elementknote_rb]

    @property
    def postcmd_idx(self):
        for idx, rb in enumerate(self.postcmd_options):
            if rb.IsChecked:
                return idx
        return 0

    @postcmd_idx.setter
    def postcmd_idx(self, index):
        self.postcmd_options[index if index else 0].IsChecked = True

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    @property
    def current_keynotes(self):
        return self.keynotes_tv.ItemsSource

    @property
    def all_categories(self):
        try:
            return kdb.get_categories(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    @property
    def all_keynotes(self):
        try:
            return kdb.get_keynotes(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    # =========================================================================
    # STATUS BAR
    # =========================================================================

    def _update_status_bar(self):
        if self._kfile:
            fname = op.basename(self._kfile)
            handler = " ( ACC / FORMA )" if self._kfile_handler == "adc" else ""
            self.statusLeft.Text = "{}{} \u2014 {}".format(
                fname, handler, op.dirname(self._kfile)
            )
        else:
            self.statusLeft.Text = "No keynote file loaded"

        try:
            cats = self.all_categories if self._conn else []
            knotes = self.all_keynotes if self._conn else []
            used = len(self._used_keysdict)
            self.statusRight.Text = (
                "{} groups \u00b7 {} keynotes \u00b7 {} in use".format(
                    len(cats), len(knotes), used
                )
            )
        except Exception:
            self.statusRight.Text = ""

    # =========================================================================
    # REVIT THREAD DISPATCH (for modeless window)
    # =========================================================================

    def _revit_run(self, action, callback=None):
        """Queue an action to execute on Revit's main thread.
        Optional callback runs on the WPF thread after the action."""
        _ext_handler.queue(action, callback, self)
        _ext_event.Raise()

    # =========================================================================
    # MODELESS FOCUS MANAGEMENT (WndProc hook)
    # =========================================================================

    WM_MOUSEACTIVATE = 0x0021
    MA_NOACTIVATE = 3

    def _on_source_initialized(self, sender, args):
        """Hook into the Win32 message loop once the HWND exists."""
        try:
            wih = WindowInteropHelper(self)
            self._hwnd_source = HwndSource.FromHwnd(wih.Handle)
            if self._hwnd_source:
                # Cache the Action delegate — must be done after __init__
                # so self._safe_activate is bound
                self._activate_action = System.Action(self._safe_activate)
                self._hwnd_source.AddHook(self._wnd_proc)
        except Exception as ex:
            logger.debug("HwndSource hook failed | %s" % ex)

    def _wnd_proc(self, hwnd, msg, wParam, lParam, handled):
        """Win32 WndProc hook — intercept activation messages.
        CRITICAL: Do not resolve .NET types/delegates by name here
        (for example System.IntPtr or System.Action); use cached
        members/delegates instead. Callback parameters and constants
        are safe to use inside this native Win32 callback."""
        try:
            if msg == self.WM_MOUSEACTIVATE:
                handled.Value = True
                if not self._activation_pending:
                    self._activation_pending = True
                    try:
                        self.Dispatcher.BeginInvoke(
                            self._activate_action, self._BG_PRIORITY
                        )
                    except Exception:
                        self._activation_pending = False
                return self._INTPTR_MA_NOACTIVATE
        except Exception:
            pass  # WndProc must NEVER throw
        return self._INTPTR_ZERO

    def _safe_activate(self):
        """Deferred activation — runs when Revit's message loop is idle."""
        self._activation_pending = False
        try:
            if self.IsLoaded and self.IsVisible:
                self.Activate()
        except Exception as ex:
            logger.debug("Deferred activation failed | %s" % ex)

    # =========================================================================
    # TREE STATE PRESERVATION
    # =========================================================================

    def _get_scroll_viewer(self):
        """Walk the visual tree to find the ScrollViewer inside TreeView."""
        tv = self.keynotes_tv
        if not tv or Windows.Media.VisualTreeHelper.GetChildrenCount(tv) == 0:
            return None
        try:
            border = Windows.Media.VisualTreeHelper.GetChild(tv, 0)
            if border and Windows.Media.VisualTreeHelper.GetChildrenCount(border) > 0:
                sv = Windows.Media.VisualTreeHelper.GetChild(border, 0)
                if isinstance(sv, Windows.Controls.ScrollViewer):
                    return sv
        except Exception:
            pass
        return self._find_child_of_type(tv, Windows.Controls.ScrollViewer)

    def _find_child_of_type(self, parent, child_type):
        """Recursively find first child of a given type in the visual tree."""
        try:
            count = Windows.Media.VisualTreeHelper.GetChildrenCount(parent)
        except Exception:
            return None
        for i in range(count):
            child = Windows.Media.VisualTreeHelper.GetChild(parent, i)
            if isinstance(child, child_type):
                return child
            result = self._find_child_of_type(child, child_type)
            if result:
                return result
        return None

    def _get_scroll_offset(self):
        """Get the current vertical scroll offset of the TreeView."""
        sv = self._get_scroll_viewer()
        if sv:
            return sv.VerticalOffset
        return None

    def _set_scroll_offset(self, offset):
        """Restore the vertical scroll offset after a tree rebuild."""

        def _do_scroll():
            sv = self._get_scroll_viewer()
            if sv:
                sv.ScrollToVerticalOffset(offset)

        self.Dispatcher.BeginInvoke(
            System.Action(_do_scroll), Windows.Threading.DispatcherPriority.Loaded
        )

    def _select_keynote_by_key(self, key):
        """Find and select the node with the given key in the new tree."""
        path = self._find_node_path(self.keynotes_tv.ItemsSource, key)
        if not path:
            return

        def _do_select():
            container = None
            parent_container = self.keynotes_tv
            for node in path:
                if container and hasattr(container, "IsExpanded"):
                    container.IsExpanded = True
                    container.UpdateLayout()
                idx = None
                items = parent_container.ItemContainerGenerator
                src = (
                    parent_container.Items
                    if hasattr(parent_container, "Items")
                    else parent_container.ItemsSource
                )
                if src:
                    for i, item in enumerate(src):
                        if hasattr(item, "key") and item.key == node.key:
                            idx = i
                            break
                if idx is not None:
                    container = items.ContainerFromIndex(idx)
                else:
                    container = items.ContainerFromItem(node)
                if container is None:
                    if hasattr(parent_container, "UpdateLayout"):
                        parent_container.UpdateLayout()
                    if idx is not None:
                        container = items.ContainerFromIndex(idx)
                    else:
                        container = items.ContainerFromItem(node)
                if container is None:
                    return
                parent_container = container

            if container and hasattr(container, "IsSelected"):
                container.IsSelected = True
                container.BringIntoView()

        self.Dispatcher.BeginInvoke(
            System.Action(_do_select), Windows.Threading.DispatcherPriority.Loaded
        )

    def _find_node_path(self, roots, target_key):
        """Return the path [root, ..., target] from roots to the node
        matching target_key, or None if not found."""
        if not roots:
            return None
        for root in roots:
            if root.key == target_key:
                return [root]
            if root.children:
                sub = self._find_node_path(root.children, target_key)
                if sub:
                    return [root] + sub
        return None

    # =========================================================================
    # USED KEYNOTE TRACKING
    # =========================================================================

    def get_used_keynote_elements(self):
        used = defaultdict(list)
        try:
            for kn in revit.query.get_used_keynotes(doc=revit.doc):
                if kn is None:
                    continue
                p = kn.Parameter[DB.BuiltInParameter.KEY_VALUE]
                if p:
                    key = p.AsString()
                    if key:
                        used[key].append(kn.Id)
        except Exception as ex:
            logger.debug("get_used_keynotes failed | %s" % ex)
        return used

    # =========================================================================
    # CONFIG
    # =========================================================================

    def save_config(self):
        wg = {}
        for k, v in self._config.get_option("last_window_geom", {}).items():
            if op.exists(k):
                wg[k] = v
        wg[self._kfile] = self.window_geom
        self._config.set_option("last_window_geom", wg)

        pc = {}
        for k, v in self._config.get_option("last_postcmd_idx", {}).items():
            if op.exists(k):
                pc[k] = v
        pc[self._kfile] = self.postcmd_idx
        self._config.set_option("last_postcmd_idx", pc)

        st = {}
        if self.search_term:
            st[self._kfile] = self.search_term
        self._config.set_option("last_search_term", st)

        script.save_config()

    def load_config(self, reset):
        wg = {} if reset else self._config.get_option("last_window_geom", {})
        if wg and self._kfile in wg:
            w, h, t, l = wg[self._kfile]
        else:
            w, h, t, l = (None, None, None, None)
        if all([w, h, t, l]) and coreutils.is_box_visible_on_screens(l, t, w, h):
            self.window_geom = (w, h, t, l)
        else:
            self.WindowStartupLocation = (
                framework.Windows.WindowStartupLocation.CenterScreen
            )

        pc = {} if reset else self._config.get_option("last_postcmd_idx", {})
        self.postcmd_idx = pc.get(self._kfile, 0)

        st = {} if reset else self._config.get_option("last_search_term", {})
        self.search_term = st.get(self._kfile, "")

    # =========================================================================
    # KEYNOTE FILE CONNECTION
    # =========================================================================

    def _determine_kfile(self):
        """Determine the keynote file path for this project.

        Resolution order:
          1. Local keynote file (revit.query.get_local_keynote_file)
          2. External/cloud file via ADC (Autodesk Desktop Connector)
             - Resolve cloud path to local via adc.get_local_path()
             - Graceful degradation for lock/sync on Public API
          3. Alert user if ADC not available
        """
        self._kfile = revit.query.get_local_keynote_file(doc=revit.doc)
        self._kfile_handler = None
        self._kfile_ext = None

        if self._kfile:
            return

        self._kfile_ext = revit.query.get_external_keynote_file(doc=revit.doc)
        self._kfile_handler = "unknown"

        if not self._kfile_ext:
            return

        # CRITICAL: call is_available() FIRST on a clean AppDomain.
        # No legacy DLL probing before this point.
        if adc.is_available():
            self._kfile_handler = "adc"
            self._resolve_adc_keynote()
            return

        forms.alert(
            "{} is not available.\n\n"
            "Please ensure Desktop Connector is running "
            "in the system tray.".format(adc.ADC_NAME),
            exitscript=True,
        )

    def _resolve_adc_keynote(self):
        """Resolve cloud keynote path to local file via ADC."""
        try:
            local_kfile = adc.get_local_path(self._kfile_ext)

            if not local_kfile:
                forms.alert(
                    "Cannot resolve local path via {}.".format(adc.ADC_NAME),
                    exitscript=True,
                )
                return

            try:
                locked, owner = adc.is_locked(self._kfile_ext)
                if locked:
                    forms.alert("File locked by {}.".format(owner), exitscript=True)
                    return
            except Exception:
                pass

            try:
                adc.sync_file(self._kfile_ext)
                adc.lock_file(self._kfile_ext)
            except Exception:
                pass

            self._kfile = local_kfile
            self.Title += " ( ACC / FORMA )"

        except Exception as adcex:
            forms.alert("ADC communication failed.\n{}".format(adcex), exitscript=True)

    def _change_kfile(self):
        kfile = forms.pick_file("txt")
        if kfile:
            try:
                with revit.Transaction("Set Keynote File"):
                    revit.update.set_keynote_file(kfile, doc=revit.doc)
            except Exception as ex:
                forms.alert(str(ex))

    def _connect_kfile(self):
        if not self._kfile or not op.exists(self._kfile):
            self._kfile = None
            forms.alert("Keynote file not found. Select a valid file.")
            self._change_kfile()
            self._determine_kfile()
        if not self._kfile:
            raise Exception("No keynote file set for this project.")
        if not os.access(self._kfile, os.W_OK):
            raise Exception("Keynote file is read-only:\n" + self._kfile)
        try:
            self._conn = kdb.connect(self._kfile)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message, exitscript=True)
        except Exception as ex:
            logger.debug("Connection failed | %s" % ex)
            res = forms.alert(
                "Cannot connect to keynote file.\n"
                "It may need conversion to the new format.",
                options=["Convert", "Select Other", "Help"],
            )
            if res == "Convert":
                try:
                    self._convert_existing()
                    forms.alert("Converted! Please relaunch.")
                    if not self._conn:
                        forms.alert("Relaunch required.", exitscript=True)
                except Exception as convex:
                    forms.alert("Conversion failed: %s" % convex, exitscript=True)
            elif res == "Select Other":
                self._change_kfile()
                self._determine_kfile()
            elif res == "Help":
                script.open_url(
                    "https://www.notion.so/pyrevitlabs/"
                    "Manage-Keynotes-6f083d6f66fe43d68dc5d5407c8e19da"
                )
                script.exit()
            else:
                forms.alert("No valid keynote file.", exitscript=True)

    def _convert_existing(self):
        temp = script.get_data_file(op.basename(self._kfile), "bak")
        if op.exists(temp):
            script.remove_data_file(temp)
        try:
            shutil.copy(self._kfile, temp)
        except Exception:
            raise Exception("Backup failed.")
        try:
            with open(self._kfile, "w"):
                pass
        except Exception:
            raise Exception("File preparation failed.")
        try:
            self._conn = kdb.connect(self._kfile)
            kdb.import_legacy_keynotes(self._conn, temp, skip_dup=True)
        except Exception as ex:
            shutil.copy(temp, self._kfile)
            raise ex
        finally:
            script.remove_data_file(temp)

    # =========================================================================
    # TREE BUILDING — UNIFIED (categories + keynotes in one tree)
    # =========================================================================

    def _build_full_tree(self):
        """Build a single tree: categories at root, keynotes nested by
        parent_key.  Returns the root-level list of RKeynote objects
        with children populated recursively."""
        try:
            categories = kdb.get_categories(self._conn)
            all_knotes = kdb.get_keynotes(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []
        except Exception as ex:
            forms.alert("Error loading keynotes:\n%s" % ex, exitscript=True)
            return []

        # Build parent -> children map from keynotes
        cat_keys = set(c.key for c in categories)
        children_map = defaultdict(list)
        for kn in all_knotes:
            if kn.parent_key:
                children_map[kn.parent_key].append(kn)

        # Recursive child population
        def _populate(node):
            node_children = natsorted(
                children_map.get(node.key, []), key=lambda x: x.key
            )
            # Replace the children list (clear first to avoid dupes)
            while node.children:
                node.children.pop()
            for child in node_children:
                _populate(child)
                node.children.append(child)

        # Root-level: categories
        roots = natsorted(categories, key=lambda x: x.key)
        for root in roots:
            _populate(root)

        # Also find keynotes whose parent_key is a category
        # but weren't caught above (edge case: orphans)
        all_parented = set()
        for kids in children_map.values():
            for k in kids:
                all_parented.add(k.key)

        return roots

    def _update_full_tree(self, fast_filter=False):
        """Refresh the single unified tree, applying search filter."""
        # Save current state before rebuild
        saved_key = None
        saved_scroll = None
        sel = self.selected_keynote
        if sel:
            saved_key = sel.key
        saved_scroll = self._get_scroll_offset()

        keynote_filter = self.search_term if self.search_term else None

        # Update view-only filter keys
        if keynote_filter and kdb.RKeynoteFilters.ViewOnly.code in keynote_filter:
            visible_keys = [
                x.TagText for x in revit.query.get_visible_keynotes(revit.active_view)
            ]
            kdb.RKeynoteFilters.ViewOnly.set_keys(visible_keys)

        if fast_filter and keynote_filter:
            tree = list(self._cache)
        else:
            tree = self._build_full_tree()

        # Mark used
        for node in tree:
            node.update_used(self._used_keysdict)

        # Cache for fast re-filter
        self._cache = list(tree)

        # Apply search filter
        if keynote_filter:
            clean = keynote_filter.lower()
            tree = [n for n in tree if n.filter(clean)]

        self.keynotes_tv.ItemsSource = tree

        if tree:
            self.emptyStateMsg.Visibility = Windows.Visibility.Collapsed
        else:
            self.emptyStateMsg.Visibility = Windows.Visibility.Visible

        # Restore state after rebuild
        if saved_key:
            self._select_keynote_by_key(saved_key)
        if saved_scroll is not None:
            self._set_scroll_offset(saved_scroll)

    # =========================================================================
    # BUTTON STATE
    # =========================================================================

    def _update_buttons(self):
        """Enable/disable toolbar buttons based on selection."""
        sel = self.selected_keynote
        if not sel or sel.locked:
            for btn in [
                self.editKeynoteBtn,
                self.dupKeynoteBtn,
                self.rekeyBtn,
                self.removeBtn,
                self.findBtn,
                self.placeBtn,
                self.indentBtn,
                self.outdentBtn,
                self.moveUpBtn,
                self.moveDownBtn,
                self.caseBtn,
            ]:
                btn.IsEnabled = False
            return

        is_cat = sel.is_category  # top-level group (no parent_key)
        is_kn = bool(sel.parent_key)

        self.editKeynoteBtn.IsEnabled = True
        self.dupKeynoteBtn.IsEnabled = is_kn
        self.rekeyBtn.IsEnabled = True
        self.removeBtn.IsEnabled = True
        self.findBtn.IsEnabled = is_kn
        self.placeBtn.IsEnabled = is_kn
        self.caseBtn.IsEnabled = True

        # Hierarchy buttons
        # Indent: can indent if it's a keynote and has a preceding sibling
        can_indent = False
        can_outdent = False
        can_up = False
        can_down = False

        if is_kn:
            siblings = _find_siblings(self.all_keynotes, sel.parent_key)
            idx = next((i for i, s in enumerate(siblings) if s.key == sel.key), -1)
            can_indent = idx > 0  # has a sibling above
            # Can outdent if parent is a keynote (not a category)
            cats = self.all_categories
            cat_keys = set(c.key for c in cats)
            parent_is_keynote = sel.parent_key not in cat_keys
            can_outdent = parent_is_keynote
            can_up = idx > 0
            can_down = idx < len(siblings) - 1
        elif is_cat:
            cats = natsorted(self.all_categories, key=lambda x: x.key)
            idx = next((i for i, c in enumerate(cats) if c.key == sel.key), -1)
            can_up = idx > 0
            can_down = idx < len(cats) - 1

        self.indentBtn.IsEnabled = can_indent
        self.outdentBtn.IsEnabled = can_outdent
        self.moveUpBtn.IsEnabled = can_up
        self.moveDownBtn.IsEnabled = can_down

    # =========================================================================
    # INDENT / OUTDENT — CORE HIERARCHY OPERATIONS
    # =========================================================================

    def indent_keynote(self, sender, args):
        """Indent: make selected node a child of the sibling above it.
        Effectively increases nesting depth by one level."""
        sel = self.selected_keynote
        if not sel or not sel.parent_key or sel.locked:
            return

        siblings = _find_siblings(self.all_keynotes, sel.parent_key)
        idx = next((i for i, s in enumerate(siblings) if s.key == sel.key), -1)
        if idx <= 0:
            return

        new_parent = siblings[idx - 1]
        try:
            kdb.move_keynote(self._conn, sel.key, new_parent.key)
            self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Indent failed: %s" % ex)
            return

        self._update_full_tree()
        self._update_status_bar()

    def outdent_keynote(self, sender, args):
        """Outdent: promote selected node up one level.
        Moves it to be a sibling of its current parent."""
        sel = self.selected_keynote
        if not sel or not sel.parent_key or sel.locked:
            return

        cats = self.all_categories
        cat_keys = set(c.key for c in cats)

        # Find current parent
        current_parent_key = sel.parent_key
        if current_parent_key in cat_keys:
            # Parent is already a top-level category — can't outdent further
            # (would need to become a category itself, which is a different op)
            forms.alert(
                "Already at the top keynote level.\n"
                "To make this a top-level group, use the Re-Key as "
                "category workflow."
            )
            return

        # Parent is a keynote — find grandparent
        all_kn = self.all_keynotes
        parent = next((k for k in all_kn if k.key == current_parent_key), None)
        if not parent:
            return

        grandparent_key = parent.parent_key
        if not grandparent_key:
            return

        try:
            kdb.move_keynote(self._conn, sel.key, grandparent_key)
            self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Outdent failed: %s" % ex)
            return

        self._update_full_tree()
        self._update_status_bar()

    # =========================================================================
    # MOVE UP / MOVE DOWN (swap keys with adjacent sibling)
    # =========================================================================

    def move_up(self, sender, args):
        """Swap selected node's key with the sibling above it."""
        self._swap_sibling(-1)

    def move_down(self, sender, args):
        """Swap selected node's key with the sibling below it."""
        self._swap_sibling(1)

    def _swap_sibling(self, direction):
        """Swap keys between the selected node and its adjacent sibling.
        direction: -1 for up, +1 for down."""
        sel = self.selected_keynote
        if not sel or sel.locked:
            return

        is_cat = sel.is_category
        if is_cat:
            siblings = natsorted(self.all_categories, key=lambda x: x.key)
        else:
            siblings = _find_siblings(self.all_keynotes, sel.parent_key)

        idx = next((i for i, s in enumerate(siblings) if s.key == sel.key), -1)
        target_idx = idx + direction
        if target_idx < 0 or target_idx >= len(siblings):
            return

        other = siblings[target_idx]
        if other.locked:
            forms.alert("Adjacent item is locked.")
            return

        # Swap keys
        sel_key = sel.key
        other_key = other.key
        temp_key = "__swap_{}__".format(uuid.uuid4().hex[:8])

        try:
            if is_cat:
                kdb.update_category_key(self._conn, sel_key, temp_key)
                kdb.update_category_key(self._conn, other_key, sel_key)
                kdb.update_category_key(self._conn, temp_key, other_key)
                # Update children parent_keys
                with kdb.BulkAction(self._conn):
                    for child in self.all_keynotes:
                        if child.parent_key == sel_key:
                            kdb.move_keynote(self._conn, child.key, other_key)
                        elif child.parent_key == other_key:
                            kdb.move_keynote(self._conn, child.key, sel_key)
            else:
                kdb.update_keynote_key(self._conn, sel_key, temp_key)
                kdb.update_keynote_key(self._conn, other_key, sel_key)
                kdb.update_keynote_key(self._conn, temp_key, other_key)
                # Update children of swapped nodes
                with kdb.BulkAction(self._conn):
                    for child in self.all_keynotes:
                        if child.parent_key == sel_key:
                            kdb.move_keynote(self._conn, child.key, other_key)
                        elif child.parent_key == other_key:
                            kdb.move_keynote(self._conn, child.key, sel_key)

            # Update references in Revit model (async via ExternalEvent)
            sk, ok = sel_key, other_key
            self._revit_run(lambda: self._swap_keynote_refs(sk, ok))
            self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Swap failed: %s" % ex)
            return

        self._update_full_tree()
        self._update_status_bar()

    def _swap_keynote_refs(self, key_a, key_b):
        """Swap Revit element references between two keynote keys."""
        temp = "__ref_{}__".format(uuid.uuid4().hex[:8])
        with revit.Transaction("Reorder Keynotes"):
            for kid in self.get_used_keynote_elements().get(key_a, []):
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p:
                        p.Set(temp)
            for kid in self.get_used_keynote_elements().get(key_b, []):
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p:
                        p.Set(key_a)
            for kid in self.get_used_keynote_elements().get(key_a, []):
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p and p.AsString() == temp:
                        p.Set(key_b)

    # =========================================================================
    # KEY PICKER
    # =========================================================================

    def _pick_new_key(self):
        try:
            cats = kdb.get_categories(self._conn)
            kns = kdb.get_keynotes(self._conn)
            locks = kdb.get_locks(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        reserved = [x.key for x in cats]
        reserved.extend([x.key for x in kns])
        reserved.extend([x.LockTargetRecordKey for x in locks])
        return forms.ask_for_unique_string(
            prompt="Enter a unique key:",
            title="Choose Unique Key",
            reserved_values=reserved,
            owner=self,
        )

    def _pick_parent(self):
        """Pick any node (category or keynote) as a parent."""
        cats = self.all_categories
        kns = self.all_keynotes
        items = natsorted(
            ["{} — {}".format(x.key, x.text) for x in cats]
            + ["{} — {}".format(x.key, x.text) for x in kns],
        )
        chosen = forms.SelectFromList.show(
            items, title="Select Parent", multiselect=False, owner=self
        )
        if chosen:
            return chosen.split(" — ")[0].strip()
        return None

    # =========================================================================
    # SEARCH
    # =========================================================================

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == "":
            self.clrsearch_b.Visibility = Windows.Visibility.Collapsed
        else:
            self.clrsearch_b.Visibility = Windows.Visibility.Visible

        # Stop and restart the timer on every keystroke.
        # The filter won't run until the typing pauses for 300ms.
        if hasattr(self, "_search_timer"):
            self._search_timer.Stop()
            self._search_timer.Start()

    def _on_search_timer_tick(self, sender, args):
        """Fires when the user stops typing."""
        self._search_timer.Stop()
        self._update_full_tree(fast_filter=True)

    def clear_search(self, sender, args):
        self.search_tb.Text = ""
        self.search_tb.Clear()
        self.search_tb.Focus()
        self._update_full_tree(fast_filter=True)

    def custom_filter(self, sender, args):
        sfilter = forms.SelectFromList.show(
            kdb.RKeynoteFilters.get_available_filters(),
            title="Select Filter",
            owner=self,
        )
        if sfilter:
            self.search_term = sfilter.format_term(self.search_term)

    # =========================================================================
    # SELECTION
    # =========================================================================

    def selected_keynote_changed(self, sender, args):
        self._update_buttons()

    # =========================================================================
    # KEYBOARD SHORTCUTS
    # =========================================================================

    def window_keydown(self, sender, args):
        key = args.Key
        mods = Windows.Input.Keyboard.Modifiers
        ctrl = Windows.Input.ModifierKeys.Control
        shift = Windows.Input.ModifierKeys.Shift

        if key == Windows.Input.Key.F5:
            self.refresh(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.F2:
            if self.selected_keynote:
                self.edit_keynote(sender, args)
                args.Handled = True
        elif key == Windows.Input.Key.Delete:
            if self.selected_keynote:
                self.remove_keynote(sender, args)
                args.Handled = True
        elif key == Windows.Input.Key.N and mods == ctrl:
            self.add_keynote(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.D and mods == ctrl:
            if self.selected_keynote:
                self.duplicate_keynote(sender, args)
                args.Handled = True
        elif key == Windows.Input.Key.I and mods == ctrl:
            self.import_keynotes(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.Tab and mods == shift:
            self.outdent_keynote(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.Tab and mods == getattr(
            Windows.Input.ModifierKeys, "None"
        ):
            self.indent_keynote(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.Up and mods == ctrl:
            self.move_up(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.Down and mods == ctrl:
            self.move_down(sender, args)
            args.Handled = True
        elif key == Windows.Input.Key.Escape:
            if self.search_term:
                self.clear_search(sender, args)
            else:
                self.Close()
            args.Handled = True

    # =========================================================================
    # DRAG AND DROP
    # =========================================================================

    def tree_preview_mouse_down(self, sender, args):
        self._drag_start_point = args.GetPosition(sender)

    def tree_preview_mouse_move(self, sender, args):
        if self._drag_start_point is None:
            return
        if args.LeftButton != Windows.Input.MouseButtonState.Pressed:
            self._drag_start_point = None
            return

        pt = args.GetPosition(sender)
        diff = self._drag_start_point - pt
        if (
            abs(diff.X) > System.Windows.SystemParameters.MinimumHorizontalDragDistance
            or abs(diff.Y) > System.Windows.SystemParameters.MinimumVerticalDragDistance
        ):
            sel = self.selected_keynote
            if sel and not sel.locked:
                self._is_dragging = True
                try:
                    data = Windows.DataObject("keynote", sel)
                    Windows.DragDrop.DoDragDrop(
                        self.keynotes_tv, data, Windows.DragDropEffects.Move
                    )
                except Exception as ex:
                    logger.debug("Drag failed | %s" % ex)
                finally:
                    self._is_dragging = False
                    self._drag_start_point = None

    def tree_double_click(self, sender, args):
        if not self._is_dragging and self.selected_keynote:
            if self.selected_keynote.parent_key:
                self.edit_keynote(sender, args)
            else:
                self.edit_category_inline(sender, args)

    def tree_drag_over(self, sender, args):
        args.Effects = getattr(Windows.DragDropEffects, "None")
        if args.Data.GetDataPresent("keynote"):
            args.Effects = Windows.DragDropEffects.Move

    def tree_item_drag_over(self, sender, args):
        args.Effects = getattr(Windows.DragDropEffects, "None")
        if args.Data.GetDataPresent("keynote"):
            args.Effects = Windows.DragDropEffects.Move
            # Visual feedback
            if hasattr(sender, "Background"):
                sender.Background = Windows.Media.SolidColorBrush(
                    Windows.Media.Color.FromArgb(40, 43, 87, 154)
                )
            args.Handled = True

    def tree_item_drag_leave(self, sender, args):
        if hasattr(sender, "Background"):
            sender.Background = None

    def tree_drop(self, sender, args):
        pass

    def tree_item_drop(self, sender, args):
        """Drop handler — reparent the dragged node under the target."""
        if hasattr(sender, "Background"):
            sender.Background = None

        if not args.Data.GetDataPresent("keynote"):
            return
        dragged = args.Data.GetData("keynote")
        if not dragged:
            return

        target = getattr(sender, "DataContext", None)
        if target is None or target == dragged:
            return

        # Determine new parent key
        new_parent_key = target.key

        # Don't allow dropping onto self or own children
        if new_parent_key == dragged.key:
            return

        # Check for circular reference
        def _is_descendant(parent_key, child_key, all_kn):
            """Check if child_key is a descendant of parent_key."""
            visited = set()
            stack = [child_key]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                for kn in all_kn:
                    if kn.parent_key == current:
                        if kn.key == parent_key:
                            return True
                        stack.append(kn.key)
            return False

        if dragged.parent_key and _is_descendant(
            new_parent_key, dragged.key, self.all_keynotes
        ):
            forms.alert("Cannot drop a parent onto its own descendant.")
            return

        # If dragged is a category, this is more complex — skip for now
        if dragged.is_category:
            forms.alert(
                "Drag top-level groups is not supported.\n"
                "Use Move Up / Move Down to reorder groups."
            )
            return

        if new_parent_key == dragged.parent_key:
            return  # no change

        try:
            kdb.move_keynote(self._conn, dragged.key, new_parent_key)
            self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
        except Exception as ex:
            forms.alert("Move failed: %s" % ex)

        self._update_full_tree()
        self._update_status_bar()
        args.Handled = True

    # =========================================================================
    # REFRESH
    # =========================================================================

    def refresh(self, sender, args):
        if self._conn:

            def _query_used():
                self._used_keysdict = self.get_used_keynote_elements()

            def _on_done():
                self._update_full_tree()
                self._update_status_bar()
                self.search_tb.Focus()

            self._revit_run(_query_used, callback=_on_done)
        else:
            self.search_tb.Focus()

    # =========================================================================
    # CATEGORY (GROUP) OPERATIONS
    # =========================================================================

    def add_category(self, sender, args):
        try:
            new_cat = EditRecordWindow(self, self._conn, kdb.EDIT_MODE_ADD_CATEG).show()
            if new_cat:
                self._needs_update = True
        except Exception as ex:
            forms.alert(str(ex))
        finally:
            self._update_full_tree()
            self._update_status_bar()

    def edit_category_inline(self, sender, args):
        """Edit a category (top-level group) via the edit dialog."""
        sel = self.selected_keynote
        if sel and sel.is_category and not sel.locked:
            try:
                EditRecordWindow(
                    self, self._conn, kdb.EDIT_MODE_EDIT_CATEG, rkeynote=sel
                ).show()
                self._needs_update = True
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_full_tree()
                self._update_status_bar()

    # =========================================================================
    # KEYNOTE CRUD
    # =========================================================================

    def add_keynote(self, sender, args):
        parent_key = None
        sel = self.selected_keynote
        if sel:
            parent_key = sel.key if sel.is_category else sel.parent_key
        if not parent_key:
            parent_key = self._pick_parent()
        if parent_key:
            try:
                EditRecordWindow(
                    self, self._conn, kdb.EDIT_MODE_ADD_KEYNOTE, pkey=parent_key
                ).show()
                self._needs_update = True
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_full_tree()
                self._update_status_bar()

    def duplicate_keynote(self, sender, args):
        sel = self.selected_keynote
        if sel and sel.parent_key:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    kdb.EDIT_MODE_ADD_KEYNOTE,
                    text=sel.text,
                    pkey=sel.parent_key,
                ).show()
                self._needs_update = True
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_full_tree()
                self._update_status_bar()

    def edit_keynote(self, sender, args):
        sel = self.selected_keynote
        if not sel:
            return
        if sel.is_category:
            self.edit_category_inline(sender, args)
            return
        try:
            EditRecordWindow(
                self, self._conn, kdb.EDIT_MODE_EDIT_KEYNOTE, rkeynote=sel
            ).show()
            self._needs_update = True
        except Exception as ex:
            forms.alert(str(ex))
        finally:
            self._update_full_tree()

    def remove_keynote(self, sender, args):
        sel = self.selected_keynote
        if not sel:
            return

        if sel.is_category:
            # Removing a category
            if sel.has_children():
                forms.alert("Group '%s' has children. Remove them first." % sel.key)
                return
            if sel.used:
                forms.alert("Group '%s' is in use." % sel.key)
                return
            if forms.alert("Delete group '%s'?" % sel.key, yes=True, no=True):
                try:
                    kdb.remove_category(self._conn, sel.key)
                    self._needs_update = True
                except Exception as ex:
                    forms.alert(str(ex))
        else:
            # Removing a keynote
            if sel.children:
                forms.alert("Keynote '%s' has children. Remove them first." % sel.key)
                return
            if sel.used:
                forms.alert("Keynote '%s' is in use." % sel.key)
                return
            if forms.alert("Delete keynote '%s'?" % sel.key, yes=True, no=True):
                try:
                    kdb.remove_keynote(self._conn, sel.key)
                    self._needs_update = True
                except Exception as ex:
                    forms.alert(str(ex))

        self._update_full_tree()
        self._update_status_bar()

    def rekey_keynote(self, sender, args):
        sel = self.selected_keynote
        if not sel:
            return
        if any(x.locked for x in sel.children):
            forms.alert("Some children are locked — cannot re-key.")
            return
        try:
            from_key = sel.key
            to_key = self._pick_new_key()
            if to_key and to_key != from_key:
                if sel.is_category:
                    kdb.update_category_key(self._conn, from_key, to_key)
                    with kdb.BulkAction(self._conn):
                        for child in self.all_keynotes:
                            if child.parent_key == from_key:
                                kdb.move_keynote(self._conn, child.key, to_key)
                else:
                    kdb.update_keynote_key(self._conn, from_key, to_key)
                    with kdb.BulkAction(self._conn):
                        for child in self.all_keynotes:
                            if child.parent_key == from_key:
                                kdb.move_keynote(self._conn, child.key, to_key)
                # Update Revit element refs (async via ExternalEvent)
                fk, tk = from_key, to_key
                self._revit_run(lambda: self._rekey_refs(fk, tk))
                self._needs_update = True
        except Exception as ex:
            forms.alert(str(ex))

        self._update_full_tree()
        self._update_status_bar()

    def _rekey_refs(self, from_key, to_key):
        with revit.Transaction("Re-Key {}".format(from_key)):
            for kid in self.get_used_keynote_elements().get(from_key, []):
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p:
                        p.Set(to_key)

    # =========================================================================
    # TEXT CAPITALIZATION (quick apply without opening edit dialog)
    # =========================================================================

    def show_case_menu(self, sender, args):
        """Open the capitalization context menu on the button."""
        self.caseMenu.PlacementTarget = sender
        self.caseMenu.IsOpen = True

    def _apply_case(self, transform_fn):
        """Apply a text transformation to the selected keynote/category."""
        sel = self.selected_keynote
        if not sel or sel.locked:
            return
        new_text = transform_fn(sel.text)
        if new_text == sel.text:
            return
        try:
            if sel.is_category:
                kdb.update_category_title(self._conn, sel.key, new_text)
            else:
                kdb.update_keynote_text(self._conn, sel.key, new_text)
            self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Case change failed: %s" % ex)
            return
        self._update_full_tree()

    def to_upper(self, sender, args):
        self._apply_case(lambda t: t.upper())

    def to_lower(self, sender, args):
        self._apply_case(lambda t: t.lower())

    def to_title(self, sender, args):
        self._apply_case(lambda t: t.title())

    def to_sentence(self, sender, args):
        self._apply_case(lambda t: t[:1].upper() + t[1:].lower() if t else t)

    # =========================================================================
    # FIND / PLACE
    # =========================================================================

    def show_keynote(self, sender, args):
        """Show keynote usage in pyRevit output — keeps the window open."""
        sel = self.selected_keynote
        if not sel:
            return
        key = sel.key
        used_snapshot = dict(self._used_keysdict)
        kids = used_snapshot.get(key, [])
        if not kids:
            self.statusLeft.Text = "Keynote '{}' — not placed in model".format(key)
            return

        def _do():
            for kid in kids:
                source = viewname = ""
                kel = revit.doc.GetElement(kid)
                if kel is None:
                    continue
                ehist = revit.query.get_history(kel)
                p = kel.Parameter[DB.BuiltInParameter.KEY_SOURCE_PARAM]
                if p:
                    source = p.AsString()
                vel = revit.doc.GetElement(kel.OwnerViewId)
                if vel:
                    viewname = revit.query.get_name(vel)
                report = "Keynote: {} | Source: {} | View: {}".format(
                    output.linkify(kid), source, viewname
                )
                if ehist:
                    report += " | Last edit: %s" % ehist.last_changed_by
                print(report)

        def _update_status():
            self.statusLeft.Text = (
                "Keynote '{}' — {} placements shown in output".format(key, len(kids))
            )

        self._revit_run(_do, callback=_update_status)

    def place_keynote(self, sender, args):
        sel = self.selected_keynote
        if not sel:
            return
        sel_key = sel.key
        postcmd = self.postable_keynote_command
        self.Close()

        def _do():
            keynotes_cat = revit.query.get_category(DB.BuiltInCategory.OST_KeynoteTags)
            if keynotes_cat:
                def_id = revit.doc.GetDefaultFamilyTypeId(keynotes_cat.Id)
                if revit.doc.GetElement(def_id):
                    DocumentEventUtils.PostCommandAndUpdateNewElementProperties(
                        HOST_APP.uiapp,
                        revit.doc,
                        postcmd,
                        "Update Keynotes",
                        DB.BuiltInParameter.KEY_VALUE,
                        sel_key,
                    )

        self._revit_run(_do)

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    def change_keynote_file(self, sender, args):
        kfile = forms.pick_file("txt")
        if not kfile:
            return

        def _set_file():
            with revit.Transaction("Set Keynote File"):
                revit.update.set_keynote_file(kfile, doc=revit.doc)

        def _reload():
            self._determine_kfile()
            self._connect_kfile()
            self._needs_update = True
            try:
                self._used_keysdict = self.get_used_keynote_elements()
            except Exception as ex:
                logger.debug("Refresh used keys failed | %s" % ex)
            self._update_full_tree()
            self._update_status_bar()

        self._revit_run(_set_file, callback=_reload)

    def show_keynote_file(self, sender, args):
        coreutils.show_entry_in_explorer(self._kfile)

    def import_keynotes(self, sender, args):
        kfile = forms.pick_file("txt")
        if kfile:
            res = forms.alert("Skip duplicate entries?", yes=True, no=True)
            try:
                kdb.import_legacy_keynotes(self._conn, kfile, skip_dup=res)
            except Exception as ex:
                forms.alert("Import failed: %s" % ex)
            finally:
                self._update_full_tree()
                self._update_status_bar()

    def export_keynotes(self, sender, args):
        kfile = forms.save_file("txt")
        if kfile:
            try:
                kdb.export_legacy_keynotes(self._conn, kfile)
            except Exception as ex:
                forms.alert(str(ex))

    def export_visible_keynotes(self, sender, args):
        kfile = forms.save_file("txt")
        if kfile:
            include = set()
            for rk in self.current_keynotes or []:
                include.update(rk.collect_keys())
            try:
                kdb.export_legacy_keynotes(self._conn, kfile, include_keys=include)
            except Exception as ex:
                forms.alert(str(ex))

    # =========================================================================
    # CLOSE
    # =========================================================================

    def update_model(self, sender, args):
        """Queue keynote update transaction and keep window open."""
        if self._needs_update:

            def _do_update():
                with revit.Transaction("Update Keynotes"):
                    revit.update.update_linked_keynotes(doc=revit.doc)

            def _on_update_complete():
                self._needs_update = False
                forms.alert("Revit model updated successfully.", title="Success")

            self._revit_run(_do_update, callback=_on_update_complete)
        else:
            forms.alert("The Revit model is already up to date.", title="Up to Date")

    def _finalize_close(self):
        """Called on WPF thread after Revit update completes."""
        self._needs_update = False
        self._close_pending = True
        self.Close()

    def window_closing(self, sender, args):
        global _active_window

        # If we haven't synced yet and user closed via X button, ask
        if self._needs_update and not self._close_pending:
            res = forms.alert(
                "Keynote file has been modified.\n"
                "Sync changes to the Revit model before closing?",
                yes=True,
                no=True,
            )
            if res:
                args.Cancel = True

                def _do_update():
                    with revit.Transaction("Update Keynotes"):
                        revit.update.update_linked_keynotes(doc=revit.doc)

                self._close_pending = True
                self._revit_run(_do_update, callback=self._finalize_close)
                return

        # Proceed with cleanup
        # Remove WndProc hook to prevent leaks
        if self._hwnd_source:
            try:
                self._hwnd_source.RemoveHook(self._wnd_proc)
            except Exception:
                pass
            self._hwnd_source = None

        if self._kfile_handler == "adc":
            try:
                adc.unlock_file(self._kfile_ext)
            except Exception:
                pass
        try:
            self.save_config()
        except Exception as ex:
            logger.debug("Save config failed | %s" % ex)
        if self._conn:
            try:
                self._conn.Dispose()
            except Exception:
                pass
        _active_window = None


# =============================================================================
# ENTRY POINT
# =============================================================================

try:
    # Singleton: if already open, bring to front
    if _active_window and _active_window.IsLoaded:
        _active_window.Activate()
        _active_window.WindowState = framework.Windows.WindowState.Normal
    else:
        _active_window = KeynoteManagerWindow(
            xaml_file_name="KeynoteManagerWindow.xaml",
            reset_config=__shiftclick__,  # pylint: disable=undefined-variable
        )
        _active_window.show(modal=False)
except Exception as kmex:
    forms.alert(str(kmex), expanded="Creating keynote manager window")
