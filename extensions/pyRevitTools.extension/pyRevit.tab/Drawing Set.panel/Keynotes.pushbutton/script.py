# -*- coding: utf-8 -*-
"""Manage project keynotes — unified tree with hierarchy controls.

Features:
- Single hierarchical tree (no separate category sidebar)
- Indent / Outdent to promote or demote nodes (Tab / Shift+Tab)
- Move Up / Move Down to reorder siblings (Ctrl+Up / Ctrl+Down)
- Drag-and-drop to reparent across the tree
- Collapse All / Expand All tree controls
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
import json
from collections import defaultdict, OrderedDict
from natsort import natsorted

from pyrevit import EXEC_PARAMS
from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils import envvars
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.framework import System, Windows
from System.Windows.Interop import WindowInteropHelper
from System.Diagnostics import Process as SysProcess
from System.Windows.Threading import DispatcherTimer
from System import TimeSpan

from pyrevit.runtime.types import DocumentEventUtils

from pyrevit.interop import adc

import keynotesdb as kdb

# =============================================================================
# PERSISTENT ENGINE REQUIREMENT
# =============================================================================
# This window is MODELESS: its WPF event handlers keep running long after the
# pyRevit command returns.  On a NON-persistent engine, pyRevit wipes every
# module-level global as soon as the command returns (IronPythonEngine.Execute
# finally-block), so the next handler that touches a global raises NameError
# into Revit's message pump = fatal crash (issue #3517).
#
# The persistent engine is declared in bundle.yaml (`engine: persistent: true`)
# — NOT with a `__persistentengine__` constant here.  bundle.yaml is the
# authoritative route: it is honored unconditionally by both the legacy and the
# C# loader, whereas inline script metadata is gated by the
# `core.read_script_metadata` setting, is ignored by the legacy loader whenever
# bundle.yaml yields metadata (genericcomps.py: `if not self.meta`), and is
# deprecated for removal in pyRevit 7.x.  (A bundle.yaml that fails to PARSE
# falls back to script constants on the legacy loader — one more reason the
# runtime probe below is the real safety net rather than either declaration.)
#
# Declaring it is still not a guarantee at RUNTIME (a stale cached command
# assembly, a bundle.yaml parse failure, or a future loader change can all
# yield a non-persistent engine), so this script does not trust the
# declaration — it reads the engine config the loader actually baked into this
# command and degrades to a safe modal window if persistence is missing.
# See _persistent_engine_state() and the entry point at the bottom.

logger = script.get_logger()
output = script.get_output()


def _coerce_persistent_flag(value):
    """Interpret an engineCfgs "persistent" value, failing CLOSED.

    bool() alone is NOT safe here: bool("false") is True, so a value
    serialized as a string would treat a NON-persistent engine as
    persistent and skip safe mode — reintroducing the crash this guard
    exists to prevent.  Anything not recognized as affirmative therefore
    reads as False, which matches the runtime (an engineCfgs value it
    cannot read leaves persistent=false and the scope IS wiped).
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    # string-ish (str / unicode on IronPython 2.7) — avoid basestring so
    # this stays valid if the module is ever loaded under CPython
    if hasattr(value, "strip"):
        try:
            return value.strip().lower() in ("true", "1", "yes")
        except Exception:
            return False
    # numeric (int / long / .NET numeric): 0 is false, anything else true
    try:
        return int(value) != 0
    except Exception:
        return False


def _persistent_engine_state():
    """Return the RESOLVED persistent-engine flag for this command.

    Returns True (persistent), False (not persistent), or None (undetermined).
    Reads the engineCfgs JSON the loader compiled into this command's wrapper,
    so it reflects reality regardless of which metadata channel supplied it.
    """
    cfgs = None
    # The engineCfgs JSON lives on ScriptRuntimeConfigs.EngineConfigs.  Try
    # that first: EXEC_PARAMS.engine_cfgs reads ScriptRuntime.EngineConfigs,
    # which does not exist on every build (it raises on 6.5.3), so it is only
    # a secondary probe here.
    try:
        rt_cfgs = EXEC_PARAMS.script_runtime_cfgs
        cfgs = rt_cfgs.EngineConfigs if rt_cfgs else None
    except Exception:
        cfgs = None
    if not cfgs:
        try:
            cfgs = EXEC_PARAMS.engine_cfgs
        except Exception:
            cfgs = None
    if not cfgs:
        logger.debug("KeynoteManager | engine cfgs unavailable — "
                     "persistent state undetermined")
        return None

    # tolerate a typed configs object instead of a JSON string
    for _attr in ("persistent", "Persistent", "PersistentEngine"):
        _val = getattr(cfgs, _attr, None)
        if isinstance(_val, bool):
            return _val

    # materialize the text ONCE — str() on a CLR proxy can itself raise
    try:
        raw = str(cfgs)
    except Exception:
        return None
    if not raw:
        return None
    try:
        cfg = json.loads(raw)
    except Exception:
        cfg = None
    if isinstance(cfg, dict):
        # NOTE: a missing "persistent" key must read as False, matching the
        # runtime — IronPythonEngineConfigs.persistent defaults to false, so
        # anything the runtime cannot read is treated as non-persistent and
        # the scope IS wiped.  Failing closed here keeps us in step with it.
        if "persistent" not in cfg:
            return False
        return _coerce_persistent_flag(cfg.get("persistent"))

    # tolerate any JSON shape change — probe the raw text.  Quotes are
    # stripped so a stringified value ("persistent":"false") reads the same
    # as a real boolean ("persistent":false).
    probe = raw.replace(" ", "").replace('"', "").replace("'", "").lower()
    if "persistent:true" in probe:
        return True
    if "persistent:false" in probe:
        return False
    logger.debug("KeynoteManager | unrecognized engine cfgs: %s", raw)
    return None


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
# UI EXCEPTION SHIELD
# =============================================================================
# In a MODELESS window there is no pyRevit executor underneath WPF event
# handlers: any exception that escapes a handler, a DispatcherTimer tick,
# or a Dispatcher.BeginInvoke callback unwinds into Revit's native message
# pump and terminates Revit (0xe0434352).  Every runtime entry point must
# therefore be wrapped.  The wrapper deliberately captures everything it
# needs as closure references / default args and uses only builtins in its
# error path, so it keeps working even if the engine scope has been wiped.


class KeynoteSetupError(Exception):
    """Keynote file could not be resolved/connected.

    Raised instead of forms.alert(exitscript=True): sys.exit() is only
    safe while the pyRevit command itself is executing.  Once the modeless
    window exists, a SystemExit escaping a handler terminates Revit.
    """
    pass


def ui_guard(fn, _logger=logger, _alert=forms.alert):
    """Shield a UI-thread entry point so no exception can escape into
    Revit's message pump.  SystemExit (forms.alert(exitscript=True),
    script.exit()) is also intercepted — it is fatal in modeless context.
    """

    def _shielded(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SystemExit:
            # sys.exit() from a modeless handler would kill Revit.
            try:
                _logger.warning(
                    "KeynoteManager | blocked SystemExit from %s",
                    getattr(fn, "__name__", "?"),
                )
            except Exception:
                pass
        except BaseException as ex:  # noqa: broad by design — last line of defense
            try:
                _logger.error(
                    "KeynoteManager | unhandled error in %s | %s",
                    getattr(fn, "__name__", "?"), ex,
                )
            except Exception:
                pass
            try:
                if isinstance(ex, NameError):
                    # Module globals are gone — engine was recycled
                    # (e.g. persistent engine flag lost).  The window can
                    # no longer run its code safely; tell the user once.
                    wnd = args[0] if args else None
                    already = getattr(wnd, "_scope_wiped_notified", False) \
                        if wnd is not None else True
                    if not already:
                        try:
                            wnd._scope_wiped_notified = True
                        except Exception:
                            pass
                        _alert(
                            "Keynote Manager lost its script engine "
                            "(pyRevit recycled it).\n\n"
                            "The window will close — please reopen it. "
                            "If this happens repeatedly, reload pyRevit.",
                            title="Keynote Manager",
                        )
                        try:
                            wnd.Close()
                        except Exception:
                            pass
            except Exception:
                pass

    # keep the original name so XAML wiring and logs stay readable
    try:
        _shielded.__name__ = fn.__name__
        _shielded.__doc__ = fn.__doc__
    except Exception:
        pass
    return _shielded


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

    def queue(self, action, callback=None, window=None,
              callback_on_error=True):
        """Add an action (and optional WPF-thread callback) to the queue.

        callback_on_error=False skips the callback when the action raises.
        Use it whenever the callback would report success or discard state
        (e.g. clearing a pending-changes flag, closing the window) — running
        it after a failed action would silently claim work that never
        happened.
        """
        self._queue.append((action, callback, window, callback_on_error))

    def Execute(self, app):
        """Called by Revit on the main thread when the event fires."""
        while self._queue:
            action, callback, window, callback_on_error = self._queue.pop(0)
            succeeded = True
            try:
                action()
            except Exception as ex:
                succeeded = False
                logger.error("RevitActionHandler | %s" % ex)
                # ALWAYS surface the failure — the callback_on_error=False
                # call sites rely on the user being told why nothing
                # happened, so this must not be conditional on IsLoaded.
                try:
                    if window and window.IsLoaded:
                        window.Dispatcher.Invoke(
                            System.Action(lambda e=str(ex): forms.alert(e))
                        )
                    else:
                        forms.alert(str(ex))
                except Exception as disp_ex:
                    logger.debug("Failed to display error in window | %s" % disp_ex)
            if callback and (succeeded or callback_on_error):
                try:
                    if window and window.IsLoaded:
                        window.Dispatcher.Invoke(System.Action(ui_guard(callback)))
                    else:
                        ui_guard(callback)()
                except Exception as cbex:
                    logger.debug("Callback failed | %s" % cbex)

    def GetName(self):
        return "KeynoteManagerHandler"


# Singleton — only one keynote manager window at a time.
# NOTE: module globals do NOT survive across button clicks (each execution
# gets a fresh scope even on a persistent engine — IronPythonEngine.Execute
# calls Engine.CreateScope() per run), so the singleton handle lives in
# pyRevit's cross-scope environment variables instead.
KEYNOTEMGR_WINDOW_ENVVAR = "KEYNOTEMGR_ACTIVE_WINDOW"

# How many times the user may retry picking a keynote file during setup
# before _connect_kfile gives up (bounds the "Select Other" retry loop).
MAX_KFILE_ATTEMPTS = 5

# Usage data comes from a collector over OST_KeynoteTags in the CURRENT
# document, so "not in use" is advisory even when the query fully succeeded:
# it cannot see other projects sharing this keynote file, linked models, or
# element/material keynote parameters with no tag placed.  Destructive
# commands say so rather than implying the check was authoritative.
USAGE_SCOPE_NOTE = (
    "Usage is checked against keynote tags in THIS project only — other "
    "projects sharing this keynote file, linked models and un-tagged "
    "element/material keynotes are not visible to this check."
)


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


def _is_enum(value, expected_name, enum_type=None):
    """True if a .NET enum value matches expected_name.

    Compares against the real enum member when the type is available and
    falls back to the name string, so this keeps working if an enum moves
    or is unavailable on a given Revit version.
    """
    if value is None:
        return False
    if enum_type is not None:
        member = getattr(enum_type, expected_name, None)
        if member is not None:
            try:
                return value == member
            except Exception:
                pass
    try:
        return str(value) == expected_name
    except Exception:
        return False


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
        self.recordText.Text = kdb.normalize_keynote_text(value)

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
            except Exception as dbex:
                forms.alert("Could not save changes:\n%s" % dbex)
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
            except Exception as dbex:
                forms.alert("Could not save changes:\n%s" % dbex)
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
            except Exception as dbex:
                forms.alert("Could not save changes:\n%s" % dbex)
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
            except Exception as dbex:
                forms.alert("Could not save changes:\n%s" % dbex)
                return False

        return True

    def show(self):
        self.ShowDialog()
        return self._res

    def pick_key(self, sender, args):
        if self._reserved_key:
            try:
                kdb.release_key(self._conn, self._reserved_key, category=self._cat)
            except Exception as ex:
                forms.alert(str(ex))
                return
        try:
            categories = kdb.get_categories(self._conn)
            keynotes = kdb.get_keynotes(self._conn)
            locks = kdb.get_locks(self._conn)
        except Exception as ex:
            forms.alert("Cannot read keynote file:\n%s" % ex)
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
        try:
            categories = kdb.get_categories(self._conn)
            keynotes = kdb.get_keynotes(self._conn)
        except Exception as ex:
            forms.alert("Cannot read keynote file:\n%s" % ex)
            return
        available = [x.key for x in categories]
        available.extend([x.key for x in keynotes])
        if self.active_key in available:
            available.remove(self.active_key)
        new_parent = forms.SelectFromList.show(
            natsorted(available), title="Select Parent", multiselect=False,
            owner=self,
        )
        if new_parent:
            try:
                kdb.reserve_key(self._conn, self.active_key, category=self._cat)
            except Exception as ex:
                forms.alert(str(ex))
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

    def __init__(self, xaml_file_name, reset_config=False, safe_mode=False):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # SAFE MODE = this command did not get a persistent engine, so the
        # window must run MODAL (see the entry point).  While a modal dialog
        # blocks, Revit does not pump ExternalEvents — but the command frame
        # is still on the stack, so the Revit API is directly usable and
        # queued actions can simply run inline instead.
        self._modal_mode = safe_mode

        # Set Revit as the owner window — critical for modeless stability.
        # Without this, WPF's message pump collides with Revit's on focus
        # change, causing hard crashes.
        try:
            wih = WindowInteropHelper(self)
            wih.Owner = SysProcess.GetCurrentProcess().MainWindowHandle
        except Exception as ex:
            logger.debug("WindowInteropHelper failed | %s" % ex)

        # Modeless focus management — keep window always on top of Revit.
        # Pointless (and visually intrusive) for a modal safe-mode window.
        self.Topmost = not self._modal_mode

        self._kfile = None
        self._kfile_handler = None
        self._kfile_ext = None
        self._conn = None

        # The document this window belongs to.  Deferred Revit actions must
        # never run against a DIFFERENT document the user switched to.
        self._doc = revit.doc

        # ExternalEvent is instance-owned: module-level creation would leak
        # one Revit-registered event per button click (fresh scope per run).
        # It is created at the very END of __init__ (see below) so that no
        # setup failure can leak a Revit-registered event: if __init__ aborts,
        # the entry-point handler never receives the instance and therefore
        # could never dispose it.
        self._ext_handler = RevitActionHandler()
        self._ext_event = None

        self._determine_kfile()
        self._connect_kfile()

        self._cache = []
        self._snapshot_categories = []
        self._snapshot_keynotes = []
        self._needs_update = False
        self._closed = False
        self._tree_updating = False
        self._config = script.get_config()
        self._used_keysdict = defaultdict(list)
        self._used_typesdict = defaultdict(set)
        self._used_viewsdict = defaultdict(list)
        # True until a COMPLETE usage snapshot has been collected: the
        # delete / re-key guards must not read "unused" out of a map that
        # never got filled.
        self._usage_stale = True
        self._refresh_used_keynotes()

        # drag state
        self._drag_start_point = None
        self._is_dragging = False

        # modeless close state
        self._close_pending = False

        self._search_timer = DispatcherTimer()
        # Wait 300ms after last keystroke before filtering.
        self._search_timer.Interval = TimeSpan.FromMilliseconds(300)
        self._search_timer.Tick += self._on_search_timer_tick

        # Auto-refresh — subscribe to Revit's DocumentChanged event
        # so usage counts and type filters update instantly.
        # Deferred to Loaded event to avoid delegate creation crash
        # during __init__ (IronPython .NET interop limitation).
        self._refresh_pending = False
        self._doc_changed_app = None
        self.Loaded += self._on_window_loaded

        self.set_image_source(self.expandAllIcon, "expand_all.png")
        self.set_image_source(self.collapseAllIcon, "collapse_all.png")

        self.load_config(reset_config)
        self._update_full_tree()
        self._update_status_bar()
        self.search_tb.Focus()

        # LAST step — everything that could abort __init__ has now succeeded,
        # so this Revit-registered event cannot be orphaned.  Nothing above
        # uses _revit_run, and the Loaded handler only fires after __init__.
        # ExternalEvent.Create requires a valid API context, which holds here
        # inside the command's execution frame.
        self._ext_event = UI.ExternalEvent.Create(self._ext_handler)

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
        pcommands = get_keynote_pcommands()
        idx = self.postcmd_idx
        return pcommands[idx if 0 <= idx < len(pcommands) else 0]

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
        # Quiet-safe: this property is hit from selection-changed and other
        # hot paths — never alert or raise here (file may be mid-sync on a
        # cloud drive).  Actions that need user feedback handle their own.
        if not self._conn:
            return []
        try:
            return kdb.get_categories(self._conn)
        except Exception as ex:
            logger.debug("all_categories read failed | %s", ex)
            return []

    @property
    def all_keynotes(self):
        if not self._conn:
            return []
        try:
            return kdb.get_keynotes(self._conn)
        except Exception as ex:
            logger.debug("all_keynotes read failed | %s", ex)
            return []

    # =========================================================================
    # STATUS BAR
    # =========================================================================

    def _update_status_bar(self):
        safe = " \u2014 SAFE MODE (no persistent engine)" \
            if self._modal_mode else ""
        if self._kfile:
            fname = op.basename(self._kfile)
            handler = " ( ACC / FORMA )" if self._kfile_handler == "adc" else ""
            self.statusLeft.Text = "{}{} \u2014 {}{}".format(
                fname, handler, op.dirname(self._kfile), safe
            )
        else:
            self.statusLeft.Text = "No keynote file loaded" + safe

        try:
            cats = self.all_categories if self._conn else []
            knotes = self.all_keynotes if self._conn else []
            # Never print "0 in use" off a map that failed to collect \u2014 the
            # count is the only place the user sees that usage is unknown.
            used = ("usage unverified (F5)" if self._usage_stale
                    else "{} in use".format(len(self._used_keysdict)))
            self.statusRight.Text = (
                "{} groups \u00b7 {} keynotes \u00b7 {}".format(
                    len(cats), len(knotes), used
                )
            )
        except Exception:
            self.statusRight.Text = ""

    # =========================================================================
    # REVIT THREAD DISPATCH (for modeless window)
    # =========================================================================

    def _is_owned_doc_active(self):
        """True when this window's document is still the active document."""
        try:
            return (self._doc is not None
                    and self._doc.IsValidObject
                    and revit.doc is not None
                    and self._doc.Equals(revit.doc))
        except Exception:
            return False

    def _revit_run(self, action, callback=None, callback_on_error=True):
        """Queue an action to execute on Revit's main thread.
        Optional callback runs on the WPF thread after the action.

        The action is refused if the user switched to a different document
        — otherwise transactions would silently modify the wrong model.

        Pass callback_on_error=False when the callback reports success or
        discards state, so a failed action cannot masquerade as a good one."""

        def _doc_affine_action():
            if not self._is_owned_doc_active():
                raise Exception(
                    "Keynote Manager was opened for a different document.\n"
                    "Switch back to that document, or close and reopen "
                    "the Keynote Manager.")
            action()

        if self._modal_mode:
            # Modal: ExternalEvents would never fire while we block, but we
            # are still inside the command's API context — run the action
            # directly.  (This holds for transactions; it does NOT hold for
            # PostCommand — see place_keynote.)
            _succeeded = True
            try:
                _doc_affine_action()
            except Exception as ex:
                _succeeded = False
                logger.error("KeynoteManager | action failed | %s", ex)
                # wrapped so an alert failure cannot bypass the gate below
                try:
                    forms.alert(str(ex))
                except Exception as disp_ex:
                    logger.debug("Failed to display error | %s", disp_ex)
            if callback and (_succeeded or callback_on_error):
                # Marshal the callback instead of calling it inline: when the
                # caller is window_closing, an inline callback would re-enter
                # Close() from inside the Closing handler, which WPF rejects
                # ("Cannot ... call Close while a Window is closing") — the
                # window would silently stay open.  BeginInvoke matches the
                # modeless ordering; ShowDialog keeps this Dispatcher pumping.
                try:
                    self.Dispatcher.BeginInvoke(
                        System.Action(ui_guard(callback)),
                        Windows.Threading.DispatcherPriority.Background)
                except Exception as cbex:
                    logger.debug("Callback dispatch failed | %s", cbex)
            return

        if self._ext_event is None:
            # window still initializing, or setup aborted.  Be loud: a
            # silent return here would leave e.g. a cancelled close with no
            # work done and no explanation.
            logger.error("KeynoteManager | ExternalEvent unavailable; "
                         "action not queued")
            forms.alert("Keynote Manager cannot reach Revit right now.\n"
                        "Please try again.")
            return
        self._ext_handler.queue(_doc_affine_action, callback, self,
                                callback_on_error=callback_on_error)
        self._ext_event.Raise()

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
            System.Action(ui_guard(_do_scroll)),
            Windows.Threading.DispatcherPriority.Loaded,
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
            System.Action(ui_guard(_do_select)),
            Windows.Threading.DispatcherPriority.Loaded,
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

    def _set_all_tree_items_expanded(self, expanded, max_passes=2):
        """Set IsExpanded on tree containers with bounded layout passes."""
        tv = self.keynotes_tv
        if not tv:
            return False

        def _safe_update_layout():
            try:
                tv.UpdateLayout()
                return True
            except Exception as ex:
                logger.warning("Expand/collapse tree update failed | %s" % ex)
                return False

        if not _safe_update_layout():
            return False

        missing_any = False
        for _ in range(max_passes):
            missing_in_pass = False
            root_gen = tv.ItemContainerGenerator
            queue = []
            for root in tv.Items:
                root_container = root_gen.ContainerFromItem(root)
                if root_container is None:
                    missing_in_pass = True
                    continue
                queue.append(root_container)

            while queue:
                container = queue.pop()
                if not container or not hasattr(container, "IsExpanded"):
                    continue
                container.IsExpanded = expanded
                gen = container.ItemContainerGenerator
                for child in container.Items:
                    child_container = gen.ContainerFromItem(child)
                    if child_container is None:
                        missing_in_pass = True
                        continue
                    queue.append(child_container)

            if not missing_in_pass:
                _safe_update_layout()
                return True

            missing_any = True
            if expanded:
                if not _safe_update_layout():
                    return False
            else:
                break

        _safe_update_layout()
        return not missing_any

    def expand_all_tree(self, sender, args):
        def _do_expand():
            self._set_all_tree_items_expanded(True, max_passes=3)

        self.Dispatcher.BeginInvoke(
            System.Action(ui_guard(_do_expand)),
            Windows.Threading.DispatcherPriority.Loaded,
        )

    def collapse_all_tree(self, sender, args):
        def _do_collapse():
            collapsed = self._set_all_tree_items_expanded(False, max_passes=1)
            if not collapsed:
                # Some deep virtualized branches may not be realized on demand.
                self._set_all_tree_items_expanded(True, max_passes=3)
                self._set_all_tree_items_expanded(False, max_passes=1)

        self.Dispatcher.BeginInvoke(
            System.Action(ui_guard(_do_collapse)),
            Windows.Threading.DispatcherPriority.Loaded,
        )

    # =========================================================================
    # USED KEYNOTE TRACKING
    # =========================================================================

    def get_used_keynote_elements(self):
        """Collect keynote usage data from the model.

        Runs Revit API queries — call ONLY from a valid API context
        (command execution, DocumentChanged handler, ExternalEvent).
        Returns (used_ids, used_types, used_views, ok) as plain dicts so the
        WPF thread never needs to touch the Revit API afterwards.

        `ok` is False when the key map may be INCOMPLETE: the query could not
        run, or it raised part-way and the dicts hold only the tags seen
        before the failure.  A False `ok` must NEVER be read as "these keys
        are unused" — that is what makes the delete/re-key guards fail open.
        See _refresh_used_keynotes and _usage_stale.

        Failures of the per-tag enrichment lookups (source param, owner view)
        deliberately do NOT clear `ok`: they only degrade tooltips and type
        filters, and cannot drop a key from `used`.  Flagging them would cry
        stale on every delete and train users to click through the warning.
        """
        used = defaultdict(list)
        used_types = defaultdict(set)
        used_views = defaultdict(list)
        try:
            doc = self._doc
            if doc is None or not doc.IsValidObject:
                # nothing can be verified against a closed/invalid document
                return used, used_types, used_views, False
            keynotes = revit.query.get_used_keynotes(doc=doc)
            if not keynotes:
                # no keynote tags at all — an empty map IS the answer here
                return used, used_types, used_views, True
            for kn in keynotes:
                if kn is None:
                    continue
                p = kn.Parameter[DB.BuiltInParameter.KEY_VALUE]
                if not p:
                    continue
                key = p.AsString()
                if not key:
                    continue
                used[key].append(kn.Id)
                # Detect keynote type from the tag's source param
                try:
                    src = kn.Parameter[
                        DB.BuiltInParameter.KEY_SOURCE_PARAM]
                    if src and src.HasValue:
                        val = src.AsString()
                        if val:
                            used_types[key].add(val)
                except Exception:
                    pass
                # Resolve owner view names NOW, while in API context,
                # so tooltip building never hits the API from WPF events
                try:
                    vel = doc.GetElement(kn.OwnerViewId)
                    if vel:
                        used_views[key].append(revit.query.get_name(vel))
                except Exception:
                    pass
        except Exception as ex:
            # The loop stopped early, so keynotes that ARE placed may be
            # missing from `used`.  Report the failure instead of handing
            # back a partial map that reads as "unused".
            logger.debug("Collect used keynotes failed | %s" % ex)
            return used, used_types, used_views, False
        return used, used_types, used_views, True

    def _refresh_used_keynotes(self):
        """Re-collect usage data, keeping the last good snapshot on failure.

        Runs Revit API queries — API context only.  Maintains _usage_stale so
        the destructive commands can tell "verified unused" apart from "could
        not check".  Returns True when the snapshot was refreshed.

        On failure the PREVIOUS snapshot is kept: an older complete map is
        better than a partial one, and F5 can still recover.
        """
        try:
            used, used_types, used_views, ok = \
                self.get_used_keynote_elements()
        except Exception as ex:
            logger.debug("Refresh used keys failed | %s" % ex)
            self._usage_stale = True
            return False
        if not ok:
            self._usage_stale = True
            return False
        self._used_keysdict = used
        self._used_typesdict = used_types
        self._used_viewsdict = used_views
        self._usage_stale = False
        return True

    def _usage_unknown_note(self, key):
        """Warning text for a destructive action on an unverified usage map.

        Returns None when the usage snapshot is trustworthy.
        """
        if not self._usage_stale:
            return None
        return (
            "Cannot verify whether '%s' is placed in the model — reading "
            "keynote usage from the document failed, so this tool does NOT "
            "know whether any tag references it.\n\n"
            "Press F5 to refresh first." % key)

    def _collect_used_ids(self, keys, operation):
        """Fresh tag ids for `keys`, collected in the current API context.

        Callers run right after the shared keynote FILE has already been
        rewritten, so silently skipping tags would leave them pointing at a
        key that no longer exists.  Query the model directly rather than
        trusting the cached snapshot; fall back to the snapshot only when it
        is known complete, and otherwise raise — _revit_run surfaces the
        message to the user instead of failing quietly.
        """
        try:
            used, _types, _views, ok = self.get_used_keynote_elements()
        except Exception as ex:
            logger.debug("%s: usage re-query failed | %s" % (operation, ex))
            used, ok = None, False
        if not ok:
            if self._usage_stale:
                raise Exception(
                    "%s: could not read keynote tags from the model, so no "
                    "tag was updated.\nThe keynote file has already been "
                    "changed — press F5 and check the affected tags."
                    % operation)
            # Fresh read failed, but the cached snapshot is a complete one:
            # use it, and flag usage as unverified from here on so the next
            # delete / re-key warns rather than trusting a map the model just
            # refused to confirm.
            used = self._used_keysdict
            self._usage_stale = True
        return dict((k, list(used.get(k, []))) for k in keys)

    # =========================================================================
    # CONFIG
    # =========================================================================

    def save_config(self):
        if not self._kfile:
            # nothing to key the per-file settings on (file resolution
            # failed mid-session) — skip rather than write a None key
            return
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
        if (all(v is not None for v in (w, h, t, l))
                and coreutils.is_box_visible_on_screens(l, t, w, h)):
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
        # resolve against the OWNING document, never whatever is active now
        self._kfile = revit.query.get_local_keynote_file(doc=self._doc)
        self._kfile_handler = None
        self._kfile_ext = None

        if self._kfile:
            return

        self._kfile_ext = revit.query.get_external_keynote_file(doc=self._doc)
        self._kfile_handler = "unknown"

        if not self._kfile_ext:
            return

        # CRITICAL: call is_available() FIRST on a clean AppDomain.
        # No legacy DLL probing before this point.
        if adc.is_available():
            self._kfile_handler = "adc"
            self._resolve_adc_keynote()
            return

        raise KeynoteSetupError(
            "{} is not available.\n\n"
            "Please ensure Desktop Connector is running "
            "in the system tray.".format(adc.ADC_NAME)
        )

    def _resolve_adc_keynote(self):
        """Resolve cloud keynote path to local file via ADC."""
        try:
            local_kfile = adc.get_local_path(self._kfile_ext)

            if not local_kfile:
                raise KeynoteSetupError(
                    "Cannot resolve local path via {}.".format(adc.ADC_NAME)
                )

            try:
                locked, owner = adc.is_locked(self._kfile_ext)
                if locked:
                    raise KeynoteSetupError(
                        "Keynote file is locked by {}.".format(owner))
            except KeynoteSetupError:
                raise
            except Exception:
                pass

            try:
                adc.sync_file(self._kfile_ext)
                adc.lock_file(self._kfile_ext)
            except Exception:
                pass

            self._kfile = local_kfile
            self.Title += " ( ACC / FORMA )"

        except KeynoteSetupError:
            raise
        except Exception as adcex:
            raise KeynoteSetupError(
                "ADC communication failed.\n{}".format(adcex))

    def _change_kfile(self):
        kfile = forms.pick_file("txt")
        if kfile:
            try:
                with revit.Transaction("Set Keynote File", doc=self._doc):
                    revit.update.set_keynote_file(kfile, doc=self._doc)
            except Exception as ex:
                forms.alert(str(ex))

    def _connect_kfile(self):
        """Resolve and connect the keynote file, with bounded user retries.

        Retries are an explicit LOOP, not recursion: "Select Other" used to
        call this method again, so a user who kept picking invalid or
        unconvertible files added a stack frame per attempt and could
        exhaust the stack during error recovery.
        """
        for attempt in range(MAX_KFILE_ATTEMPTS):
            if not self._kfile or not op.exists(self._kfile):
                self._kfile = None
                forms.alert("Keynote file not found. Select a valid file.")
                self._change_kfile()
                self._determine_kfile()
            # Existence must be re-checked: get_local_keynote_file returns the
            # path stored in the document WITHOUT testing it, so cancelling
            # the picker hands back the same missing path.  Without this, a
            # missing file would fall through to the read-only check below and
            # be misreported as a permissions problem.
            if not self._kfile or not op.exists(self._kfile):
                raise KeynoteSetupError(
                    "No valid keynote file set for this project.")
            if not os.access(self._kfile, os.W_OK):
                raise KeynoteSetupError(
                    "Keynote file is read-only:\n" + self._kfile)

            # Release any previous connection (reconnect via Change File)
            if self._conn:
                try:
                    self._conn.Dispose()
                except Exception:
                    pass
                self._conn = None

            # Pre-flight: DeffrelDB creates/deletes '<kfile>.lock' sidecar
            # files in INFINITE retry loops with no timeout
            # (DataStore.CreateLock/DeleteLock).  If the folder refuses file
            # create/delete — offline cloud folder, sync client holding
            # handles — Revit would hang at 100% CPU forever.  Prove the
            # folder allows it before connecting.
            probe = self._kfile + ".probe_{}".format(uuid.uuid4().hex[:6])
            try:
                with open(probe, "w"):
                    pass
                os.remove(probe)
            except Exception as probex:
                raise KeynoteSetupError(
                    "The keynote file's folder does not allow creating lock "
                    "files (offline or locked by a sync client?):\n{}\n\n{}"
                    .format(op.dirname(self._kfile), probex))

            try:
                self._conn = kdb.connect(self._kfile)
            except System.TimeoutException as toutex:
                raise KeynoteSetupError(toutex.Message)
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
                        if not self._conn:
                            raise KeynoteSetupError(
                                "Converted — please reopen Keynote Manager.")
                    except KeynoteSetupError:
                        raise
                    except Exception as convex:
                        raise KeynoteSetupError(
                            "Conversion failed: %s" % convex)
                elif res == "Select Other":
                    # Don't prompt on the final pass: _change_kfile COMMITS
                    # set_keynote_file, so picking a file the loop is about
                    # to discard would repoint the document at a keynote file
                    # that was never actually tried.
                    if attempt >= MAX_KFILE_ATTEMPTS - 1:
                        raise KeynoteSetupError(
                            "Could not connect to a valid keynote file after "
                            "{} attempts.\n\nPlease reopen Keynote Manager "
                            "to try again.".format(MAX_KFILE_ATTEMPTS))
                    self._change_kfile()
                    self._determine_kfile()
                    continue  # retry in THIS frame — never recurse
                elif res == "Help":
                    script.open_url(
                        "https://www.notion.so/pyrevitlabs/"
                        "Manage-Keynotes-6f083d6f66fe43d68dc5d5407c8e19da"
                    )
                    raise KeynoteSetupError(
                        "See the help page for converting the keynote file, "
                        "then reopen Keynote Manager.")
                else:
                    raise KeynoteSetupError("No valid keynote file.")

            # connected (or converted) — stop retrying
            break
        else:
            raise KeynoteSetupError(
                "Could not connect to a valid keynote file after {} "
                "attempts.".format(MAX_KFILE_ATTEMPTS))

        # Session shadow backup — DeffrelDB rewrites the whole file on
        # every commit with no atomic-rename step; if a cloud-sync race
        # ever mangles the file, this copy is the recovery point.
        if self._conn and self._kfile:
            try:
                shadow = script.get_data_file(
                    "kshadow_" + op.basename(self._kfile), "txt")
                shutil.copy(self._kfile, shadow)
                logger.debug("Keynote shadow backup: %s", shadow)
            except Exception as shex:
                logger.debug("Shadow backup failed | %s", shex)

    def _convert_existing(self):
        """Convert a legacy keynote file in place.

        The backup copy is only removed after a VERIFIED successful
        conversion; on any failure it is preserved and its path surfaced,
        so the user's keynote data can never be lost to a truncate+failed
        restore (cloud-synced files fail exactly that way)."""
        temp = script.get_data_file(op.basename(self._kfile), "bak")
        if op.exists(temp):
            script.remove_data_file(temp)
        try:
            shutil.copy(self._kfile, temp)
        except Exception:
            raise Exception("Backup failed — conversion aborted, keynote "
                            "file untouched.")
        try:
            with open(self._kfile, "w"):
                pass
            self._conn = kdb.connect(self._kfile)
            kdb.import_legacy_keynotes(self._conn, temp, skip_dup=True)
        except Exception as ex:
            try:
                shutil.copy(temp, self._kfile)
            except Exception:
                # restore ALSO failed — the backup is now the only copy
                raise Exception(
                    "Conversion failed AND the original could not be "
                    "restored (file locked by a sync client?).\n\n"
                    "Your keynotes are SAFE in this backup:\n{}\n\n"
                    "Copy it back manually once the file unlocks."
                    .format(temp))
            raise ex
        # success — keep the backup anyway; it is cheap insurance
        logger.debug("Legacy keynote backup kept at: %s", temp)

    # =========================================================================
    # TREE BUILDING — UNIFIED (categories + keynotes in one tree)
    # =========================================================================

    def _build_full_tree(self):
        """Build a single tree: categories at root, keynotes nested by
        parent_key.  Returns the root-level list of RKeynote objects
        with children populated recursively."""
        if not self._conn:
            return []
        if self._kfile and not op.exists(self._kfile):
            # File vanished (cloud rename/eviction).  DeffrelDB would
            # silently resurrect it as an EMPTY file on the next call and
            # the tree would show blank — disconnect loudly instead.
            self._conn = None
            forms.alert(
                "The keynote file is missing — renamed or removed by the "
                "sync client?\n{}\n\nUse Change Keynote File to reconnect."
                .format(self._kfile))
            return []
        try:
            categories = kdb.get_categories(self._conn)
            all_knotes = kdb.get_keynotes(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []
        except Exception as ex:
            # Keep the window alive: the file may be temporarily locked by
            # a cloud-sync client (Google Drive / OneDrive / Desktop
            # Connector).  Exiting here would raise SystemExit through the
            # dispatcher and take Revit down with it.
            logger.error("Error loading keynotes | %s", ex)
            forms.alert(
                "Error loading keynotes:\n%s\n\n"
                "The keynote file may be locked or syncing. "
                "Use Refresh (F5) to retry." % ex)
            return []

        # Build parent -> children map from keynotes
        cat_keys = set(c.key for c in categories)
        children_map = defaultdict(list)
        for kn in all_knotes:
            if kn.parent_key:
                children_map[kn.parent_key].append(kn)

        # Iterative child population (explicit stack).
        # - visited-set guards against parent_key CYCLES in a hand-edited
        #   keynote file;
        # - the explicit stack + depth cap guard against pathologically
        #   DEEP chains — native StackOverflow would kill the whole Revit
        #   process uncatchably.  The cap also bounds every later
        #   recursive traversal (filter/update_used/collect_keys/find).
        visited = set()
        max_depth = 64

        def _populate(root):
            stack = [(root, 0)]
            while stack:
                node, depth = stack.pop()
                if node.key in visited:
                    logger.warning(
                        "Keynote hierarchy cycle detected at key '%s' — "
                        "check the keynote file.", node.key)
                    continue
                visited.add(node.key)
                # Replace the children list (clear first to avoid dupes)
                while node.children:
                    node.children.pop()
                if depth >= max_depth:
                    logger.warning(
                        "Keynote nesting deeper than %s levels truncated "
                        "at key '%s'.", max_depth, node.key)
                    continue
                for child in natsorted(
                        children_map.get(node.key, []),
                        key=lambda x: x.key):
                    node.children.append(child)
                    stack.append((child, depth + 1))

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
        """Re-entrancy-safe tree refresh.

        A DispatcherTimer tick or DocumentChanged dispatch can fire while
        a modal dialog opened inside a previous update is still pumping
        messages — never run two updates nested."""
        if self._tree_updating:
            return
        self._tree_updating = True
        try:
            self._update_full_tree_core(fast_filter=fast_filter)
        finally:
            self._tree_updating = False

    def _update_full_tree_core(self, fast_filter=False):
        """Refresh the single unified tree, applying search filter."""
        # Save current state before rebuild
        saved_key = None
        saved_scroll = None
        sel = self.selected_keynote
        if sel:
            saved_key = sel.key
        saved_scroll = self._get_scroll_offset()

        keynote_filter = self.search_term if self.search_term else None

        # Update view-only filter keys.
        # NOTE: this runs on the WPF/dispatcher side, outside a Revit API
        # context — a read query usually works, but never let it throw.
        if keynote_filter and kdb.RKeynoteFilters.ViewOnly.code in keynote_filter:
            try:
                visible_keys = [
                    x.TagText
                    for x in revit.query.get_visible_keynotes(revit.active_view)
                ]
                kdb.RKeynoteFilters.ViewOnly.set_keys(visible_keys)
            except Exception as ex:
                logger.debug("View filter unavailable | %s", ex)
                kdb.RKeynoteFilters.ViewOnly.set_keys([])

        if fast_filter and keynote_filter:
            tree = list(self._cache)
        else:
            tree = self._build_full_tree()

        # Mark used (pre-resolved view names — no Revit API access here)
        for node in tree:
            node.update_used(
                self._used_keysdict,
                self._used_typesdict,
                view_names=self._used_viewsdict,
            )

        # Cache for fast re-filter
        self._cache = list(tree)

        # Flat snapshots for hot paths: selection-changed fires constantly
        # and must never re-read the DB file (slow / throwy on cloud drives)
        flat_knotes = []

        def _flatten(node):
            for child in node._children:
                flat_knotes.append(child)
                _flatten(child)

        for _root in self._cache:
            _flatten(_root)
        self._snapshot_categories = list(self._cache)
        self._snapshot_keynotes = flat_knotes

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
        # placement is unavailable in safe (modal) mode — see place_keynote
        self.placeBtn.IsEnabled = is_kn and not self._modal_mode
        self.caseBtn.IsEnabled = True

        # Hierarchy buttons
        # Indent: can indent if it's a keynote and has a preceding sibling
        can_indent = False
        can_outdent = False
        can_up = False
        can_down = False

        # Use the cached snapshots — NOT the DB-reading properties.
        # This method fires on every selection change; hitting the keynote
        # file each time is slow and can throw while a cloud drive syncs.
        if is_kn:
            siblings = _find_siblings(self._snapshot_keynotes, sel.parent_key)
            idx = next((i for i, s in enumerate(siblings) if s.key == sel.key), -1)
            can_indent = idx > 0  # has a sibling above
            # Can outdent if parent is a keynote (not a category)
            cat_keys = set(c.key for c in self._snapshot_categories)
            parent_is_keynote = sel.parent_key not in cat_keys
            can_outdent = parent_is_keynote
            can_up = idx > 0
            can_down = idx < len(siblings) - 1
        elif is_cat:
            cats = natsorted(self._snapshot_categories, key=lambda x: x.key)
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
        if idx < 0:
            # stale selection — sel no longer exists in the fresh sibling
            # read; without this guard, Move Down would swap the WRONG
            # records (idx -1 + 1 = 0 -> first sibling)
            return
        target_idx = idx + direction
        if target_idx < 0 or target_idx >= len(siblings):
            return

        other = siblings[target_idx]
        if other.locked:
            forms.alert("Adjacent item is locked.")
            return

        # Swap keys — single atomic commit with rollback on failure
        sel_key = sel.key
        other_key = other.key
        temp_key = "__swap_{}__".format(uuid.uuid4().hex[:8])

        try:
            kdb.swap_keys(
                self._conn, sel_key, other_key, temp_key, category=is_cat)

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
        # Collect BEFORE opening the transaction, and from the model rather
        # than the cached snapshot: the keys have already been swapped in the
        # keynote file, so a stale map would leave tags on the wrong text.
        ids = self._collect_used_ids([key_a, key_b], "Reorder")
        a_ids = ids.get(key_a, [])
        b_ids = ids.get(key_b, [])
        temp = "__ref_{}__".format(uuid.uuid4().hex[:8])
        with revit.Transaction("Reorder Keynotes"):
            for kid in a_ids:
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p:
                        p.Set(temp)
            for kid in b_ids:
                kel = revit.doc.GetElement(kid)
                if kel:
                    p = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if p:
                        p.Set(key_a)
            for kid in a_ids:
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
        except Exception as ex:
            forms.alert("Cannot read keynote file:\n%s" % ex)
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
        if self._closed:
            return
        self._update_full_tree(fast_filter=True)

    def _on_window_loaded(self, sender, args):
        """Subscribe to DocumentChanged after window is fully loaded."""
        try:
            self._doc_changed_app = HOST_APP.uiapp.Application
            self._doc_changed_app.DocumentChanged += self._on_doc_changed
        except Exception:
            try:
                self._doc_changed_app = HOST_APP.app
                self._doc_changed_app.DocumentChanged += self._on_doc_changed
            except Exception:
                self._doc_changed_app = None

    def _on_doc_changed(self, sender, args):
        """Fires on the Revit thread after any document change.
        Refreshes keynote usage data and updates the tree."""
        if self._closed or self._refresh_pending:
            return
        # Only react to changes in THIS window's document
        try:
            changed_doc = args.GetDocument()
            if changed_doc and not changed_doc.Equals(self._doc):
                return
        except Exception:
            pass
        self._refresh_pending = True

        # Collect data on the Revit thread (we have API access here)
        try:
            new_used, new_types, new_views, ok = \
                self.get_used_keynote_elements()
        except Exception:
            self._refresh_pending = False
            self._usage_stale = True
            return

        # Dispatch UI update to WPF thread
        def _update_ui():
            try:
                if self._closed:
                    return
                if ok:
                    self._used_keysdict = new_used
                    self._used_typesdict = new_types
                    self._used_viewsdict = new_views
                    self._usage_stale = False
                else:
                    # partial map — keep the last good snapshot and flag it
                    self._usage_stale = True
                self._update_full_tree()
                self._update_status_bar()
            except Exception:
                pass
            finally:
                self._refresh_pending = False

        try:
            self.Dispatcher.BeginInvoke(
                System.Action(ui_guard(_update_ui)),
                Windows.Threading.DispatcherPriority.Background)
        except Exception:
            self._refresh_pending = False

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

        # Never hijack keys while the user is typing in a text field —
        # Delete would delete the selected KEYNOTE instead of a character
        # and Tab would indent it instead of moving focus.
        try:
            focused = Windows.Input.Keyboard.FocusedElement
            if isinstance(focused, Windows.Controls.Primitives.TextBoxBase):
                if key not in (Windows.Input.Key.F5, Windows.Input.Key.Escape):
                    return
        except Exception:
            pass

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

        # Read the keynote list DIRECTLY and abort on failure — the quiet
        # all_keynotes property returns [] on a read error, which would
        # make this cycle check pass vacuously and let a parent_key cycle
        # be committed to the shared file.
        try:
            fresh_keynotes = kdb.get_keynotes(self._conn)
        except Exception as ex:
            forms.alert(
                "Keynote file is busy — move not applied.\n%s\n\n"
                "Try the move again." % ex)
            return

        if dragged.parent_key and _is_descendant(
            new_parent_key, dragged.key, fresh_keynotes
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
                self._refresh_used_keynotes()

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
        if not self._conn:
            forms.alert("No keynote file is connected.")
            return

        # Ask the DATABASE, not the in-memory tree.  The tree is not a
        # reliable source for this check, for three separate reasons:
        #   - an active search filter hides children (sel.children returns
        #     only the FILTERED subset);
        #   - _build_full_tree truncates below max_depth, so a node at that
        #     boundary looks childless while the file still has descendants
        #     under it;
        #   - the cycle guard skips already-visited nodes, which likewise
        #     omits them from the snapshots.
        # Deleting on a stale "no children" answer orphans those rows
        # invisibly in the shared keynote file, so a read failure must ABORT
        # rather than fall through to "no children".
        try:
            db_keynotes = kdb.get_keynotes(self._conn)
        except Exception as ex:
            forms.alert(
                "Keynote file is busy — nothing was deleted.\n%s\n\n"
                "Please try again." % ex)
            return
        has_any_children = any(k.parent_key == sel.key for k in db_keynotes)

        if sel.is_category:
            # Removing a category
            if has_any_children:
                forms.alert("Group '%s' has children. Remove them first." % sel.key)
                return
            if sel.used:
                forms.alert("Group '%s' is in use." % sel.key)
                return
            if self._confirm_delete("group", sel.key):
                try:
                    kdb.remove_category(self._conn, sel.key)
                    self._needs_update = True
                except Exception as ex:
                    forms.alert(str(ex))
        else:
            # Removing a keynote
            if has_any_children:
                forms.alert("Keynote '%s' has children. Remove them first." % sel.key)
                return
            if sel.used:
                forms.alert("Keynote '%s' is in use." % sel.key)
                return
            if self._confirm_delete("keynote", sel.key):
                try:
                    kdb.remove_keynote(self._conn, sel.key)
                    self._needs_update = True
                except Exception as ex:
                    forms.alert(str(ex))

        self._update_full_tree()
        self._update_status_bar()

    def _confirm_delete(self, kind, key):
        """Confirm a delete, stating plainly how well usage was verified.

        The `sel.used` guard above is only as good as the usage map behind it
        — an unverified map reports every keynote as unused, so the guard
        passes vacuously.  Deleting then drops the row (and its text) from the
        SHARED keynote file while tags keep KEY_VALUE pointing at a key that
        no longer exists.  Never let that happen without saying so.
        """
        unknown = self._usage_unknown_note(key)
        if unknown:
            return forms.alert(
                "%s\n\nDelete %s '%s' anyway?  Any tag still pointing at "
                "'%s' would keep that key with no matching row in the "
                "keynote file." % (unknown, kind, key, key),
                yes=True, no=True)
        return forms.alert(
            "Delete %s '%s'?\n\n%s" % (kind, key, USAGE_SCOPE_NOTE),
            yes=True, no=True)

    def rekey_keynote(self, sender, args):
        sel = self.selected_keynote
        if not sel:
            return
        if not self._conn:
            # _conn is legitimately None while the window is alive: the
            # keynote file may have vanished, or a Change-File reconnect
            # may have failed.
            forms.alert("No keynote file is connected.")
            return
        # Locked-children check against the DATABASE for the same reason as
        # remove_keynote: filtering, depth truncation and the cycle guard can
        # all hide a locked child from the in-memory tree.  Abort on a read
        # failure rather than proceeding on incomplete information.
        try:
            db_keynotes = kdb.get_keynotes(self._conn)
        except Exception as ex:
            forms.alert("Keynote file is busy — re-key not applied.\n%s\n\n"
                        "Please try again." % ex)
            return
        if any(k.locked for k in db_keynotes if k.parent_key == sel.key):
            forms.alert("Some children are locked — cannot re-key.")
            return
        try:
            from_key = sel.key
            to_key = self._pick_new_key()
            if (to_key and to_key != from_key
                    and self._confirm_rekey(from_key, to_key)):
                # single atomic commit with rollback on failure
                kdb.rekey_with_children(
                    self._conn, from_key, to_key, category=sel.is_category)
                # Update Revit element refs (async via ExternalEvent)
                fk, tk = from_key, to_key
                self._revit_run(lambda: self._rekey_refs(fk, tk))
                self._needs_update = True
        except Exception as ex:
            forms.alert(str(ex))

        self._update_full_tree()
        self._update_status_bar()

    def _confirm_rekey(self, from_key, to_key):
        """Confirm a re-key, stating whether placed tags can be re-pointed.

        Re-keying renames the row in the shared keynote file and only then
        re-points the tags it can find.  Tags it cannot find keep the OLD key
        and end up referencing a row that no longer exists, so an unverified
        usage map has to be surfaced BEFORE the file is rewritten.
        """
        unknown = self._usage_unknown_note(from_key)
        if unknown:
            return forms.alert(
                "%s\n\nRe-key '%s' to '%s' anyway?  Placed tags may NOT be "
                "updated, leaving them pointing at the old key."
                % (unknown, from_key, to_key),
                yes=True, no=True)
        return forms.alert(
            "Re-key '%s' to '%s'?\n\nKeynote tags in this project will be "
            "re-pointed to the new key (%d found in the last usage check).\n\n"
            "%s" % (from_key, to_key,
                    len(self._used_keysdict.get(from_key, [])),
                    USAGE_SCOPE_NOTE),
            yes=True, no=True)

    def _rekey_refs(self, from_key, to_key):
        # Re-query rather than trusting the cached snapshot: the keynote file
        # has already been rewritten at this point, so a stale map here would
        # silently leave tags pointing at a key that no longer exists.
        ids = self._collect_used_ids([from_key], "Re-key")
        with revit.Transaction("Re-Key {}".format(from_key)):
            for kid in ids.get(from_key, []):
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
            # an unverified map reports everything as unplaced — don't claim it
            self.statusLeft.Text = (
                "Keynote '{}' — usage unverified, press F5".format(key)
                if self._usage_stale
                else "Keynote '{}' — not placed in model".format(key))
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

        # callback_on_error=False: don't claim "N placements shown" when the
        # report failed part-way (or was refused by the doc-affinity guard)
        self._revit_run(_do, callback=_update_status, callback_on_error=False)

    def place_keynote(self, sender, args):
        # NOT AVAILABLE IN SAFE (MODAL) MODE — and this is a hard block, not
        # just a UX nicety.  PostCommandAndUpdateNewElementProperties both
        # (a) PostCommands an interactive tool that cannot run while a modal
        # dialog owns the UI and the command frame has not returned, and
        # (b) arms pyRevit's CancelAllDialogs DialogBoxShowing hook, which is
        # only ever unsubscribed from an Idling handler — and Idling never
        # fires while a modal dialog blocks.  Left armed, it silently
        # auto-confirms EVERY later TaskDialog, including the delete-keynote
        # prompts = silent deletions from the shared keynote file.
        if self._modal_mode:
            forms.alert(
                "Placing keynotes needs the modeless window, which requires "
                "a persistent engine (see SAFE MODE in the status bar).\n\n"
                "Close the Keynote Manager, then place the tag — or reload "
                "pyRevit so the tool gets a persistent engine.",
                title="Not available in Safe Mode")
            return

        sel = self.selected_keynote
        if not sel:
            return
        sel_key = sel.key
        postcmd = self.postable_keynote_command

        def _do():
            # clear first — a stale value from a previous click would
            # otherwise be reported if this attempt fails early
            self._place_result = None
            keynotes_cat = revit.query.get_category(
                DB.BuiltInCategory.OST_KeynoteTags)
            if not keynotes_cat:
                self._place_result = 'no_family'
                return
            def_id = revit.doc.GetDefaultFamilyTypeId(keynotes_cat.Id)
            if not def_id or not revit.doc.GetElement(def_id):
                self._place_result = 'no_family'
                return
            self._place_result = 'ok'
            DocumentEventUtils.PostCommandAndUpdateNewElementProperties(
                HOST_APP.uiapp,
                revit.doc,
                postcmd,
                "Update Keynotes",
                DB.BuiltInParameter.KEY_VALUE,
                sel_key,
            )

        def _on_placed():
            result = getattr(self, '_place_result', None)
            if result == 'no_family':
                forms.alert(
                    "No Keynote Tag family is loaded in this project.\n\n"
                    "Please load a Keynote Tag family from the library "
                    "before placing keynotes.",
                    title="Keynote Tag Missing")
                return
            self._refresh_used_keynotes()
            self._update_full_tree()
            self._update_status_bar()
            # Re-assert visibility — Revit steals focus on PostCommand
            try:
                self.Topmost = not self._modal_mode
                self.Activate()
            except Exception:
                pass

        # callback_on_error=False: don't refresh/report as if a placement
        # happened when the PostCommand setup itself failed
        self._revit_run(_do, callback=_on_placed, callback_on_error=False)

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
            if not self._is_owned_doc_active():
                # never re-resolve against a foreign document
                forms.alert(
                    "Keynote Manager was opened for a different document.\n"
                    "Switch back to that document, or close and reopen "
                    "the Keynote Manager.")
                return
            try:
                self._determine_kfile()
                self._connect_kfile()
            except KeynoteSetupError as kex:
                self._conn = None
                forms.alert(str(kex))
                self._update_full_tree()
                self._update_status_bar()
                return
            self._needs_update = True
            self._refresh_used_keynotes()
            self._update_full_tree()
            self._update_status_bar()

        # callback_on_error=False: _reload tears down and rebuilds the DB
        # connection and sets _needs_update.  If _set_file failed, the
        # document still points at the OLD file, so there is nothing to
        # reload — and the likeliest failure is the doc-affinity guard, in
        # which case reloading would rebind this window to a different
        # document's keynote file.
        self._revit_run(_set_file, callback=_reload, callback_on_error=False)

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
                # verified sync — raises if Revit did not actually reload
                self._sync_model_keynotes()

            def _on_update_complete():
                self._needs_update = False
                forms.alert("Revit model updated successfully.", title="Success")

            # callback_on_error=False: never clear _needs_update or claim
            # success if the update transaction failed
            self._revit_run(_do_update, callback=_on_update_complete,
                            callback_on_error=False)
        else:
            forms.alert("The Revit model is already up to date.", title="Up to Date")

    def _sync_model_keynotes(self):
        """Reload the model's keynote table and VERIFY that it happened.

        Neither pyRevit helper reports failure: revit.Transaction swallows
        commit errors and discards Commit()'s TransactionStatus
        (revit/db/transaction.py), and revit.update.update_linked_keynotes
        throws away the ExternalResourceLoadStatus that
        KeynoteTable.Reload() returns (revit/db/update.py).  A failed sync
        would therefore return normally and be reported as success.  This
        RAISES instead, so the callback_on_error gate actually engages.
        """
        doc = self._doc
        if doc is None or not doc.IsValidObject:
            raise Exception("The document this window was opened for is no "
                            "longer available.")

        ktable = DB.KeynoteTable.GetKeynoteTable(doc)

        def _reload_checked():
            status = ktable.Reload(None)
            if not _is_enum(status, "Success",
                            getattr(DB, "ExternalResourceLoadStatus", None)):
                raise Exception(
                    "Revit could not reload the keynote table "
                    "(status: {}).\n\nThe keynote file may be locked, "
                    "missing, or still syncing.".format(status))

        if doc.IsModifiable:
            # already inside a transaction — just do the checked reload
            _reload_checked()
            return

        txn = DB.Transaction(doc, "Update Keynotes")
        txn.Start()
        resolved = False
        try:
            _reload_checked()
            tstatus = txn.Commit()
            resolved = True
            if not _is_enum(tstatus, "Committed",
                            getattr(DB, "TransactionStatus", None)):
                raise Exception(
                    "Revit rolled back the keynote update "
                    "(status: {}).".format(tstatus))
        finally:
            if not resolved:
                try:
                    txn.RollBack()
                except Exception:
                    pass
            try:
                txn.Dispose()
            except Exception:
                pass

    def _finalize_close(self):
        """Called on WPF thread after Revit update completes."""
        self._needs_update = False
        self._close_pending = True
        self.Close()

    def window_closing(self, sender, args):
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
                    # verified sync — raises if Revit did not actually
                    # reload, so the gate below keeps the window open
                    self._sync_model_keynotes()

                def _sync_done():
                    # Only reached when the sync actually succeeded
                    # (callback_on_error=False).  On failure the handler has
                    # already alerted, _needs_update stays True and
                    # _close_pending stays False, so the window remains open
                    # and the next close attempt prompts again instead of
                    # discarding an unsynced change.
                    self._close_pending = True
                    self._finalize_close()

                self._revit_run(_do_update, callback=_sync_done,
                                callback_on_error=False)
                return

        # Proceed with cleanup
        self._closed = True
        try:
            self._search_timer.Stop()
        except Exception:
            pass
        if self._doc_changed_app:
            try:
                self._doc_changed_app.DocumentChanged -= self._on_doc_changed
            except Exception:
                pass
            self._doc_changed_app = None
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
            self._conn = None
        if self._ext_event is not None:
            try:
                self._ext_event.Dispose()
            except Exception:
                pass
            self._ext_event = None
        # Only the modeless window owns the singleton handle — a safe-mode
        # (modal) window never registers one, so it must not clear a live
        # modeless window's handle either.
        if not self._modal_mode:
            try:
                envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
            except Exception:
                pass


# =============================================================================
# APPLY UI EXCEPTION SHIELD
# =============================================================================
# Every method that WPF, the DispatcherTimer, the Revit event system, or
# the ExternalEvent framework can invoke AFTER the command returns must be
# shielded.  Add new handlers to this list when wiring them in XAML.

_GUARDED_ENTRY_POINTS = (
    (RevitActionHandler, (
        "Execute",
    )),
    (EditRecordWindow, (
        "apply_changes", "cancel_changes", "pick_key", "pick_parent",
        "select_template", "translate",
        "to_upper", "to_lower", "to_title", "to_sentence",
        "window_closing",
    )),
    (KeynoteManagerWindow, (
        # XAML-wired
        "add_category", "add_keynote", "change_keynote_file", "clear_search",
        "collapse_all_tree", "custom_filter", "duplicate_keynote",
        "edit_keynote", "edit_category_inline", "expand_all_tree",
        "export_keynotes", "export_visible_keynotes", "import_keynotes",
        "indent_keynote", "outdent_keynote", "move_up", "move_down",
        "place_keynote", "refresh", "rekey_keynote", "remove_keynote",
        "show_case_menu", "show_keynote", "show_keynote_file",
        "to_upper", "to_lower", "to_title", "to_sentence",
        "update_model", "window_closing", "window_keydown",
        "search_txt_changed", "selected_keynote_changed",
        "tree_preview_mouse_down", "tree_preview_mouse_move",
        "tree_double_click", "tree_drag_over", "tree_drop",
        "tree_item_drag_over", "tree_item_drag_leave", "tree_item_drop",
        # code-wired
        "_on_search_timer_tick", "_on_window_loaded", "_on_doc_changed",
    )),
)

for _cls, _names in _GUARDED_ENTRY_POINTS:
    for _mname in _names:
        _fn = _cls.__dict__.get(_mname)
        if _fn:
            setattr(_cls, _mname, ui_guard(_fn))
        else:
            logger.warning(
                "ui_guard: %s.%s not found — XAML handler unshielded?",
                _cls.__name__, _mname)


# =============================================================================
# ENTRY POINT
# =============================================================================

try:
    # Is this command ACTUALLY running on a persistent engine?  Do not trust
    # the declaration — read what the loader resolved (see the note at the
    # top of this file).  True -> modeless (best UX).  False -> modal, which
    # keeps the command frame alive for the window's whole lifetime and is
    # therefore safe without a persistent engine.  None (undetermined) ->
    # modeless, with ui_guard as the backstop.
    _persistent = _persistent_engine_state()
    _safe_mode = _persistent is False
    if _safe_mode:
        logger.warning(
            "KeynoteManager | no persistent engine resolved for this "
            "command — opening in safe (modal) mode.  Check that "
            "bundle.yaml declares `engine: persistent: true` and reload "
            "pyRevit; a stale cached command assembly can also cause this.")

    # Singleton: if already open, bring to front.  The handle lives in
    # pyRevit env-vars because module globals do not survive across
    # executions (fresh scope per click even on a persistent engine).
    # The LOOKUP runs in both modes: a live modeless window from an earlier
    # run must be reused (never orphaned) even if this run lands in safe
    # mode.  Only the REGISTRATION is modeless-only.
    _existing = envvars.get_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR)
    _needs_new = True
    if _existing:
        try:
            if _existing.IsLoaded:
                _existing.Activate()
                _existing.WindowState = framework.Windows.WindowState.Normal
                _needs_new = False
        except Exception:
            # stale handle from a closed window or reloaded pyRevit
            pass

    if _needs_new:
        if not _safe_mode:
            envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
        _new_window = KeynoteManagerWindow(
            xaml_file_name="KeynoteManagerWindow.xaml",
            reset_config=__shiftclick__,  # pylint: disable=undefined-variable
            safe_mode=_safe_mode,
        )
        if _safe_mode:
            _new_window.Title += "  [Safe Mode]"
            # modal: blocks here until the user closes the window
            _new_window.show(modal=True)
        else:
            envvars.set_pyrevit_env_var(
                KEYNOTEMGR_WINDOW_ENVVAR, _new_window)
            _new_window.show(modal=False)
except KeynoteSetupError as kser:
    # Expected setup failures (no keynote file, ADC offline, locked file)
    envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
    forms.alert(str(kser))
except SystemExit:
    # A SystemExit here (e.g. from a pyRevit library helper) would
    # otherwise vanish with ZERO output — pyRevit's engine swallows
    # SystemExitException silently.  Surface it instead of going dark.
    envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
    logger.error("KeynoteManager | a SystemExit was raised during setup")
    forms.alert(
        "Keynote Manager could not start (an internal exit was "
        "triggered before the window opened).\n\n"
        "Check the output window above for any earlier messages, "
        "and check the pyRevit log if this repeats.",
        title="Keynote Manager")
except BaseException as kmex:  # noqa: broad by design — never fail silently
    envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
    logger.error("KeynoteManager | %s", kmex)
    forms.alert(str(kmex), expanded="Creating keynote manager window")
