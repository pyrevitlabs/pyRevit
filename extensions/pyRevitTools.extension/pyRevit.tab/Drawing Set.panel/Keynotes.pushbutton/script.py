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
from System.Windows.Threading import DispatcherTimer
from System import TimeSpan

from pyrevit.runtime.types import DocumentEventUtils

from pyrevit.interop import adc

import keynotesdb as kdb


logger = script.get_logger()
output = script.get_output()


def _resolve_bundle_dir():
    """Resolve the bundle directory at module load.

    EXEC_PARAMS.command_path is valid only during the current invocation, so
    a modeless window's handlers must never read it (#3548).
    """
    cmd_path = EXEC_PARAMS.command_path
    if cmd_path:
        return cmd_path
    try:
        fallback = op.dirname(op.abspath(__file__))
    except Exception:
        fallback = ""
    logger.warning("KeynoteManager | command path unavailable at module "
                   "load; bundle assets resolved from %s",
                   fallback or "<cwd>")
    return fallback


_BUNDLE_DIR = _resolve_bundle_dir()


def bundle_file(filename):
    """Absolute path to a bundle file, safe to call after the invocation ends."""
    return op.join(_BUNDLE_DIR, filename)


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

        if "persistent" not in cfg:
            return False
        return _coerce_persistent_flag(cfg.get("persistent"))


    probe = raw.replace(" ", "").replace('"', "").replace("'", "").lower()
    if "persistent:true" in probe:
        return True
    if "persistent:false" in probe:
        return False
    logger.debug("KeynoteManager | unrecognized engine cfgs: %s", raw)
    return None


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
              callback_on_error=True, on_finished=None):
        """Add an action (and optional WPF-thread callback) to the queue.

        callback_on_error=False skips the callback when the action raises.
        Use it whenever the callback would report success or discard state
        (e.g. clearing a pending-changes flag, closing the window) — running
        it after a failed action would silently claim work that never
        happened.

        on_finished ALWAYS runs on the WPF thread once the entry is done —
        after a success, after a raise, and after a callback that was
        skipped or itself threw.  Release a guard taken before queueing
        there and NOWHERE else: `action` never runs at all when the
        dispatcher refuses it, so a guard released inside `action` or
        inside `callback` stays held forever on the refusal path (#3631).

        Returns the queued entry, for `drop` if it never reaches Revit.
        """
        entry = (action, callback, window, callback_on_error, on_finished)
        self._queue.append(entry)
        return entry

    def drop(self, entry):
        """Discard a queued entry whose ExternalEvent was never accepted.

        Execute drains the whole queue, so an entry left behind by a rejected
        request would run on the next unrelated raise.
        """
        try:
            self._queue.remove(entry)
        except ValueError:
            pass

    def Execute(self, app):
        """Called by Revit on the main thread when the event fires."""
        while self._queue:
            (action, callback, window, callback_on_error,
             on_finished) = self._queue.pop(0)
            succeeded = True
            try:
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
                        logger.debug("Failed to display error in window | %s"
                                     % disp_ex)
                if callback and (succeeded or callback_on_error):
                    try:
                        if window and window.IsLoaded:
                            window.Dispatcher.Invoke(
                                System.Action(ui_guard(callback)))
                        else:
                            ui_guard(callback)()
                    except Exception as cbex:
                        logger.debug("Callback failed | %s" % cbex)
            finally:
                # covers the action AND the callback: an action refused
                # before it ran, and a callback that threw, must both still
                # release the caller's guard (#3631)
                if on_finished:
                    try:
                        if window and window.IsLoaded:
                            window.Dispatcher.Invoke(
                                System.Action(ui_guard(on_finished)))
                        else:
                            ui_guard(on_finished)()
                    except Exception as finex:
                        logger.debug("on_finished failed | %s" % finex)

    def GetName(self):
        return "KeynoteManagerHandler"


# Singleton — only one keynote manager window at a time.

KEYNOTEMGR_WINDOW_ENVVAR = "KEYNOTEMGR_ACTIVE_WINDOW"
MAX_KFILE_ATTEMPTS = 5
USAGE_SCOPE_NOTE = (
    "Usage is checked against keynote tags in THIS project only — other "
    "projects sharing this keynote file, linked models and un-tagged "
    "element/material keynotes are not visible to this check."
)

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


class EditRecordWindow(forms.WPFWindow):
    """Dialog for adding/editing a single keynote or category record."""

    def __init__(
        self, owner, conn, mode, rkeynote=None, rkey=None, text=None, pkey=None
    ):
        forms.WPFWindow.__init__(self, bundle_file("EditRecord.xaml"))
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


class PastePreviewWindow(forms.WPFWindow):
    """Shows what a paste would do to the TARGET file, row by row.

    Projects in a firm share a master keynote standard, so a key existing
    on both sides is the NORMAL case, not the exception.  The dangerous
    one is the same key with different text: that means the two projects
    have diverged, and silently taking either side loses somebody's
    edit.  Conflicts are therefore listed unticked — the user opts in.

    Rows are built in code rather than data-bound: WPF binding to plain
    IronPython objects is unreliable, and the whole grid is throwaway.
    """

    # Conflicts first: they are the only rows needing a decision.
    _STATUS_RANK = {"Conflict": 0, "New": 1, "Missing parent": 2,
                    "Locked": 3, "Identical": 4}

    # (resource key, English fallback, brush).  Every string here is
    # resolved through the merged ResourceDictionary, which is OPTIONAL:
    # _resolve_xaml_source merges nothing when no locale file is present,
    # so each entry has to carry a usable default.
    _RESULT = {
        "New": ("ResultAdd", "Add", "NewBrush"),
        "Conflict": ("ResultReplace", "Replace text", "ConflictBrush"),
        "Identical": ("ResultIdentical", "Already there", "MutedBrush"),
        "Locked": ("ResultLocked", "Locked by {0}", "MutedBrush"),
        "Missing parent": ("ResultNoParent", "No parent group",
                           "MutedBrush"),
    }

    def _text(self, key, default):
        """Localised string for `key`, falling back to the English default."""
        try:
            return self.get_locale_string(key, default) or default
        except Exception:
            return default

    def __init__(self, owner, rows, source_doc, target_name, same_file=False):
        forms.WPFWindow.__init__(self, bundle_file("PastePreview.xaml"))
        self.Owner = owner
        self.approved = None
        # remember the caller's parents-before-children order: the display
        # order below is by status, which would break insertion
        self._order = dict((r["key"], i) for i, r in enumerate(rows))
        self._rows = sorted(
            rows,
            key=lambda r: (self._STATUS_RANK.get(r["status"], 9), r["key"]))
        self._boxes = []
        self._by_key = {}
        self._children = defaultdict(list)
        for row in self._rows:
            if row.get("parent_needs_add"):
                self._children[row["parent"]].append(row["key"])
        # guards the cascade below against re-entering itself
        self._syncing = False

        # composed here rather than by the caller, so both halves are
        # translatable and the placeholders can be reordered per language
        source_name = source_doc or self._text("UnknownSource",
                                               "another project")
        if same_file:
            source_name += " " + self._text("SameFileNote",
                                            "(same keynote file)")
        self.headerText.Text = (
            self._text("HeaderInto",
                       "{0} record(s) from “{1}” into “{2}”.")
            .format(len(self._rows), source_name, target_name)
            + "\n"
            + self._text("HeaderNote",
                         "Ticked rows are written to the target keynote "
                         "file; everything else is left exactly as it is."))
        self.footerNote.Text = self._text(
            "FooterNote",
            "Taking a conflicting row replaces the target's TEXT only — "
            "its place in the tree is kept.")
        self._build_rows()
        self._update_summary()

    # --- construction ----------------------------------------------------

    def _build_rows(self):
        self.rowsPanel.Items.Clear()
        del self._boxes[:]
        for row in self._rows:
            self.rowsPanel.Items.Add(self._make_row(row))

    def _make_row(self, row):
        grid = Windows.Controls.Grid()
        grid.Margin = Windows.Thickness(4, 2, 4, 2)
        for width, star in ((26, False), (150, False), (1, True),
                            (1, True), (120, False)):
            coldef = Windows.Controls.ColumnDefinition()
            coldef.Width = Windows.GridLength(
                width,
                Windows.GridUnitType.Star if star
                else Windows.GridUnitType.Pixel)
            grid.ColumnDefinitions.Add(coldef)

        status = row["status"]
        box = Windows.Controls.CheckBox()
        box.VerticalAlignment = Windows.VerticalAlignment.Center
        box.IsEnabled = status in ("New", "Conflict")
        # New rows are additive and safe; a conflict overwrites text that
        # someone in the target project wrote, so it starts unticked.
        box.IsChecked = (status == "New")
        box.Tag = row
        box.Checked += self._on_row_toggled
        box.Unchecked += self._on_row_toggled
        Windows.Controls.Grid.SetColumn(box, 0)
        grid.Children.Add(box)
        self._boxes.append(box)
        self._by_key[row["key"]] = box

        label = row["key"]
        if row["is_category"]:
            label += "  " + self._text("GroupTag", "(group)")
        self._cell(grid, 1, label, mono=True)
        self._cell(grid, 2, row["text"])
        self._cell(grid, 3, row["target_text"])

        res_key, res_default, brush = self._RESULT.get(
            status, (None, status, "MutedBrush"))
        text = self._text(res_key, res_default) if res_key else res_default
        if status == "Locked":
            owner = row.get("owner") or self._text("UnknownUser",
                                                   "another user")
            try:
                text = text.format(owner)
            except Exception:
                # a translation with a stray brace must not kill the row
                text = "%s %s" % (res_default.split("{")[0].strip(), owner)
        self._cell(grid, 4, text, brush_key=brush)
        return grid

    def _cell(self, grid, column, text, brush_key=None, mono=False):
        block = Windows.Controls.TextBlock()
        block.Text = text or ""
        block.FontSize = 11
        block.TextTrimming = Windows.TextTrimming.CharacterEllipsis
        block.VerticalAlignment = Windows.VerticalAlignment.Center
        block.Margin = Windows.Thickness(4, 0, 4, 0)
        if mono:
            try:
                block.FontFamily = Windows.Media.FontFamily("Consolas")
            except Exception:
                pass
        if brush_key:
            try:
                block.SetResourceReference(
                    Windows.Controls.TextBlock.ForegroundProperty, brush_key)
            except Exception:
                pass
        Windows.Controls.Grid.SetColumn(block, column)
        grid.Children.Add(block)
        return block

    # --- interaction -----------------------------------------------------

    def _on_row_toggled(self, sender, args):
        """Keep parents and children consistent.

        A keynote whose group does not exist in the target yet can only be
        written if that group is written too, so ticking a child pulls in
        the groups it needs and unticking a group drops what sat under it.
        Rows whose parent already exists in the target are independent and
        are deliberately left alone.
        """
        if self._syncing:
            return
        self._syncing = True
        try:
            row = getattr(sender, "Tag", None)
            if row is None:
                return
            if sender.IsChecked:
                self._tick_required_parents(row)
            else:
                self._untick_dependents(row["key"])
        except Exception as ex:
            logger.debug("paste preview cascade failed | %s", ex)
        finally:
            self._syncing = False
        self._update_summary()

    def _tick_required_parents(self, row):
        seen = set()
        while row is not None and row.get("parent_needs_add"):
            parent_key = row["parent"]
            if parent_key in seen:
                return                      # defensive: cyclic parentage
            seen.add(parent_key)
            box = self._by_key.get(parent_key)
            if box is None or not box.IsEnabled:
                return
            box.IsChecked = True
            row = box.Tag

    def _untick_dependents(self, key):
        stack = list(self._children.get(key, []))
        while stack:
            child_key = stack.pop()
            box = self._by_key.get(child_key)
            if box is None or not box.IsChecked:
                continue
            box.IsChecked = False
            stack.extend(self._children.get(child_key, []))

    def _update_summary(self):
        adds = sum(1 for b in self._boxes
                   if b.IsChecked and b.Tag["status"] == "New")
        overs = sum(1 for b in self._boxes
                    if b.IsChecked and b.Tag["status"] == "Conflict")
        self.summaryText.Text = self._text(
            "SummaryCounts",
            "{0} to add · {1} to replace · {2} left alone").format(
                adds, overs, len(self._rows) - adds - overs)
        self.pasteBtn.IsEnabled = bool(adds or overs)

    def _set_all(self, predicate):
        """Apply a whole tick state at once.

        Each of these is already internally consistent — every New row
        is included or none is — so the per-row cascade is suppressed
        rather than run once per checkbox.
        """
        self._syncing = True
        try:
            for box in self._boxes:
                box.IsChecked = bool(box.IsEnabled and predicate(box.Tag))
        finally:
            self._syncing = False
        self._update_summary()

    def take_all(self, sender, args):
        self._set_all(lambda row: True)

    def only_new(self, sender, args):
        self._set_all(lambda row: row["status"] == "New")

    def take_none(self, sender, args):
        self._set_all(lambda row: False)

    # --- result ----------------------------------------------------------

    def _finish(self, result):
        try:
            self.DialogResult = result   # closes a modal dialog
        except Exception:
            self.Close()

    def do_paste(self, sender, args):
        approved = []
        for box in self._boxes:
            if not box.IsChecked:
                continue
            row = dict(box.Tag)
            row["action"] = "add" if row["status"] == "New" else "overwrite"
            approved.append(row)
        # back to parents-before-children before anything is written
        approved.sort(key=lambda r: self._order.get(r["key"], 0))

        # Belt and braces: the cascade above should make this impossible,
        # but writing a keynote under a group that was never created would
        # corrupt a SHARED file, so drop any such row rather than trust it.
        writable = set(r["key"] for r in approved)
        kept = []
        for row in approved:
            if row.get("parent_needs_add") and row["parent"] not in writable:
                logger.warning("paste: %s dropped — its group %s is not "
                               "being written", row["key"], row["parent"])
                continue
            kept.append(row)

        self.approved = kept
        self._finish(True)

    def do_cancel(self, sender, args):
        self.approved = None
        self._finish(False)

    def show(self):
        self.ShowDialog()
        return self.approved


class _DocBinding(object):
    """Per-document state the panel swaps in and out on a project switch.

    The window keeps the ACTIVE binding's values in its own attributes
    (self._conn, self._kfile, self._needs_update, the usage maps) so the
    ~190 call sites that read them need no change: _capture_binding writes
    them back out, _activate_binding writes the next ones in.

    The keynote FILE is deliberately not held here.  Two open projects
    usually share one, and they must then share a single connection and a
    single ADC lock; see KeynoteManagerWindow._files.
    """

    def __init__(self, doc):
        self.doc = doc
        self.kfile = None      # key into KeynoteManagerWindow._files
        self.error = None      # why this project shows no tree, or None
        self.needs_update = False
        self.used_keysdict = defaultdict(list)
        self.used_typesdict = defaultdict(set)
        self.used_viewsdict = defaultdict(list)
        self.usage_stale = True
        self.cache = []
        self.snapshot_categories = []
        self.snapshot_keynotes = []
        self.search_term = ""
        self.selected_key = None
        self.scroll_offset = 0.0

    @property
    def title(self):
        """Short project name for the title bar and multi-project prompts."""
        try:
            return op.splitext(op.basename(self.doc.PathName))[0] \
                or self.doc.Title
        except Exception:
            try:
                return self.doc.Title
            except Exception:
                return "<unknown project>"

    def is_live(self):
        try:
            return self.doc is not None and self.doc.IsValidObject
        except Exception:
            return False


# =============================================================================
# MAIN KEYNOTE MANAGER WINDOW
# =============================================================================


class KeynoteManagerWindow(forms.WPFWindow):
    """Keynote manager with unified tree and hierarchy controls."""

    def __init__(self, xaml_file_name, reset_config=False, safe_mode=False):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._modal_mode = safe_mode
        self.Topmost = False
        self._base_title = self.Title

        # --- multi-project state ------------------------------------------
        # _files is keyed by keynote FILE because two open projects often
        # share one: they then share a connection and a single ADC lock,
        # held until this window closes.
        # _bindings is keyed by DOCUMENT.  self._binding is the one whose
        # state is currently mirrored into the window's own attributes.
        self._files = {}
        self._bindings = []
        self._binding = None
        self._bind_error = None
        self._pending_doc = None
        self._inflight = 0
        self._uiapp = None
        self._follow_error = "not armed yet"
        # Plain dicts, so the clipboard outlives a project switch and the
        # source file's connection.
        self._clipboard = None

        self._kfile = None
        self._kfile_handler = None
        self._kfile_ext = None
        self._conn = None
        self._doc = revit.doc
        self._ext_handler = RevitActionHandler()
        self._ext_event = None

        # The FIRST bind is interactive: the user asked for this window, so
        # a missing or unconvertible file is worth a prompt.  Every later
        # bind comes from a view switch and must stay silent (_bind_silent).
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
        self._usage_stale = True
        self._refresh_used_keynotes()

        # the document this window was opened for is binding #1
        self._binding = _DocBinding(self._doc)
        self._binding.kfile = self._kfile
        self._bindings.append(self._binding)

        self._drag_start_point = None
        self._is_dragging = False
        self._drag_left_window = False
        self._drag_cancelled = False
        self._shift_place_pending = None
        self._shift_release_timer = None

        # Multi-selection.  WPF TreeView selects one row, so the extra rows
        # are tracked here and drawn from the row data (see
        # RKeynote.multi_selected).
        self._sel_keys = set()
        self._sel_anchor = None
        self._suspend_sel_reset = False

        # modeless close state
        self._close_pending = False
        self._close_sync_pending = False

        self._search_timer = DispatcherTimer()
        # Wait 300ms after last keystroke before filtering.
        self._search_timer.Interval = TimeSpan.FromMilliseconds(300)
        self._search_timer.Tick += self._on_search_timer_tick

        # Coalesce view switches.  ViewActivated fires for every view, and
        # the user may tab through several projects before settling;
        # connecting can touch a cloud folder, so never bind on the first
        # tick of a switch.
        self._retarget_timer = DispatcherTimer()
        self._retarget_timer.Interval = TimeSpan.FromMilliseconds(250)
        self._retarget_timer.Tick += self._on_retarget_timer_tick

        self._refresh_pending = False
        self._doc_changed_app = None
        self.Loaded += self._on_window_loaded

        self.load_config(reset_config)
        self._update_full_tree()
        self._update_status_bar()
        self._update_title()
        self.search_tb.Focus()
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
        if self._follow_error and not self._modal_mode:
            safe += " \u2014 NOT following ({})".format(self._follow_error)
        if self._bind_error:
            self.statusLeft.Text = \
                self._bind_error.replace("\n", "  ") + safe
        elif self._kfile:
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
            if len(self._sel_keys) > 1:
                self.statusRight.Text += " \u00b7 {} selected".format(
                    len(self._sel_keys))
        except Exception:
            self.statusRight.Text = ""

    # =========================================================================
    # MULTI-SELECTION
    # =========================================================================

    def _flat_display_rows(self, filtered=True):
        """Every row in tree order.

        Walks the cached tree rather than the database: this runs on every
        Ctrl/Shift click, and selecting rows must never touch the keynote
        file.

        filtered=True follows `children`, the search-aware view, so a
        Shift+Click range covers exactly what is on screen.  filtered=False
        follows the raw `_children`, which is what the SELECTION itself has
        to be read through: a row stays selected while a search hides it,
        and Copy must still take it rather than quietly dropping it.
        """
        rows = []

        def _walk(nodes):
            for rec in nodes or []:
                rows.append(rec)
                _walk(rec.children if filtered else rec._children)

        _walk(self._cache)
        return rows

    def _apply_selection_marks(self, rows=None):
        """Push the selection set onto the row objects.

        Unfiltered: a row hidden by the current search keeps its highlight
        so it is still marked when the search is cleared.
        """
        if rows is None:
            rows = self._flat_display_rows(filtered=False)
        for rec in rows:
            rec.multi_selected = rec.key in self._sel_keys

    def _set_selection(self, keys, anchor=None):
        self._sel_keys = set(keys or [])
        if anchor is not None:
            self._sel_anchor = anchor
        self._apply_selection_marks()
        self._update_status_bar()
        self._update_buttons()

    def _toggle_in_selection(self, rec):
        """Ctrl+Click: add or remove one row, keeping the rest."""
        keys = set(self._sel_keys)
        if not keys:
            # first Ctrl+Click extends the row the user already had focused
            focus = self.selected_keynote
            if focus:
                keys.add(focus.key)
        if rec.key in keys:
            keys.discard(rec.key)
        else:
            keys.add(rec.key)
        self._set_selection(keys, anchor=rec.key)

    def _extend_selection_to(self, rec):
        """Shift+Click: select everything between the anchor and this row.

        The anchor deliberately stays put, so a second Shift+Click
        re-ranges from the same origin instead of creeping down the tree.
        """
        rows = self._flat_display_rows()
        order = dict((r.key, i) for i, r in enumerate(rows))
        anchor = self._sel_anchor
        if anchor not in order:
            focus = self.selected_keynote
            anchor = focus.key if focus else rec.key
        if anchor not in order or rec.key not in order:
            self._set_selection([rec.key], anchor=rec.key)
            return
        low, high = sorted((order[anchor], order[rec.key]))
        self._set_selection([r.key for r in rows[low:high + 1]], anchor=anchor)

    @property
    def selected_keynotes(self):
        """The multi-selection in tree order, or the focused row alone.

        Tree order matters: copy walks these as roots and writes parents
        before children.
        """
        if not self._sel_keys:
            focus = self.selected_keynote
            return [focus] if focus else []
        return [r for r in self._flat_display_rows(filtered=False)
                if r.key in self._sel_keys]

    def _prune_nested(self, recs):
        """Keep only the topmost row of each selected branch.

        Copy takes whole subtrees, so a keynote selected alongside its own
        group would otherwise be collected twice.
        """
        chosen = set(r.key for r in recs)
        parents = {}
        for rec in self._flat_display_rows(filtered=False):
            parents[rec.key] = rec.parent_key
        roots = []
        for rec in recs:
            parent = parents.get(rec.key)
            seen = set()
            nested = False
            while parent and parent not in seen:
                seen.add(parent)
                if parent in chosen:
                    nested = True
                    break
                parent = parents.get(parent)
            if not nested:
                roots.append(rec.key)
        return roots

    # =========================================================================
    # COPY / PASTE BETWEEN PROJECTS
    # =========================================================================

    def _subtree_rows(self, root_keys):
        """Flatten `root_keys` and their descendants, parents before children.

        Reads the FILE rather than the on-screen tree: RKeynote.children
        returns the FILTERED children while a search is active, so walking
        the view would silently copy only the rows matching the filter.
        """
        by_key = {}
        kids = defaultdict(list)
        knotes = kdb.get_keynotes(self._conn)
        for rec in kdb.get_categories(self._conn) + knotes:
            by_key[rec.key] = rec
        for rec in knotes:
            if rec.parent_key:
                kids[rec.parent_key].append(rec)

        rows = []
        seen = set()

        def _walk(key):
            if key in seen:
                return
            rec = by_key.get(key)
            if rec is None:
                return
            seen.add(key)
            rows.append({"key": rec.key,
                         "text": rec.text,
                         "parent_key": rec.parent_key,
                         "is_category": rec.is_category})
            for child in natsorted(kids.get(key, []), key=lambda x: x.key):
                _walk(child.key)

        for root_key in root_keys:
            _walk(root_key)
        return rows

    def copy_keynote(self, sender, args):
        """Copy the selection and everything under it to the clipboard."""
        picked = self.selected_keynotes
        if not picked:
            return
        if not self._conn:
            forms.alert("No keynote file is connected.")
            return
        root_keys = self._prune_nested(picked)
        if not root_keys:
            return
        try:
            rows = self._subtree_rows(root_keys)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Could not read the keynotes to copy.\n%s" % ex)
            return
        if not rows:
            return
        self._clipboard = {
            "source_doc": self._binding.title if self._binding else "",
            "source_kfile": self._kfile,
            "roots": root_keys,
            "items": rows,
        }
        knote_count = sum(1 for r in rows if not r["is_category"])
        self._hint("Copied {} — {} keynote(s), {} group(s)".format(
            ", ".join(root_keys), knote_count, len(rows) - knote_count))

    def _classify_paste(self, items, target_parent):
        """Work out what each incoming row would do.  READ ONLY.

        Nothing may be written before the user approves the preview, so
        this must not touch the target file.
        """
        existing = {}
        for rec in (kdb.get_categories(self._conn)
                    + kdb.get_keynotes(self._conn)):
            existing[rec.key] = rec
        locks = {}
        try:
            for lock in kdb.get_locks(self._conn):
                if lock.IsRecordLock:
                    locks[lock.LockTargetRecordKey] = lock.LockRequester
        except Exception as ex:
            logger.debug("lock read failed | %s", ex)

        incoming = set(i["key"] for i in items)
        rows = []
        for item in items:
            key = item["key"]
            if item["is_category"]:
                parent = ""                      # groups are roots
            elif item["parent_key"] in incoming:
                parent = item["parent_key"]      # copied with its parent
            elif target_parent:
                parent = target_parent           # re-home onto the selection
            elif item["parent_key"] in existing:
                parent = item["parent_key"]      # same group already here
            else:
                parent = None                    # nowhere to put it

            old = existing.get(key)
            if key in locks:
                status = "Locked"
            elif parent is None:
                status = "Missing parent"
            elif old is None:
                status = "New"
            elif (kdb.normalize_keynote_text(old.text)
                  == kdb.normalize_keynote_text(item["text"])):
                status = "Identical"
            else:
                status = "Conflict"

            rows.append({"key": key,
                         "text": item["text"],
                         "parent": parent,
                         "is_category": item["is_category"],
                         "target_text": old.text if old else "",
                         "owner": locks.get(key, ""),
                         # True when this row's parent does not exist in the
                         # target yet, so the row is only writable if the
                         # parent is pasted too
                         "parent_needs_add": bool(parent
                                                  and parent in incoming
                                                  and parent not in existing),
                         "status": status})
        return rows

    def paste_keynote(self, sender, args):
        """Paste the clipboard into the keynote file on screen."""
        if not self._clipboard:
            self._hint("Nothing copied yet")
            return
        if not self._conn:
            forms.alert("No keynote file is connected.")
            return

        sel = self.selected_keynote
        try:
            rows = self._classify_paste(self._clipboard["items"],
                                        sel.key if sel else None)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Could not read the target keynote file.\n%s" % ex)
            return
        if not rows:
            return

        approved = PastePreviewWindow(
            self, rows,
            self._clipboard.get("source_doc"),
            self._binding.title if self._binding else "",
            same_file=(self._clipboard.get("source_kfile") == self._kfile)
        ).show()
        if not approved:
            return

        try:
            written = kdb.paste_records(self._conn, approved)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Paste failed — nothing was written.\n%s" % ex)
            return

        # every open project on THIS file now has a stale keynote table;
        # _capture_binding fans that out to the other bindings
        self._needs_update = True
        self._hint("Pasted {} record(s)".format(written))
        self._update_full_tree()
        self._update_status_bar()
        self._update_buttons()

    # =========================================================================
    # MULTI-PROJECT BINDINGS
    # =========================================================================

    def _find_binding(self, doc):
        """The binding for `doc`, or None.

        Linear over the handful of open projects rather than a dict lookup:
        a Revit Document is not a safe dictionary key.
        """
        if doc is None:
            return None
        for b in self._bindings:
            try:
                if b.doc is not None and b.doc.IsValidObject \
                        and b.doc.Equals(doc):
                    return b
            except Exception:
                continue
        return None

    def _bind_silent(self, binding):
        """Resolve and connect `binding`'s keynote file without prompting.

        Following must never raise a file picker or a Convert dialog in the
        middle of a view switch, so every failure lands in binding.error and
        is shown in the panel instead.  Returns True when a connection is
        available.

        MUST run in a valid Revit API context (it is queued through
        _revit_run): resolving the keynote file reads the KeynoteTable.
        """
        binding.error = None
        binding.kfile = None
        try:
            kfile, kfile_ext, handler = self._resolve_kfile_for(binding.doc)
        except KeynoteSetupError as kex:
            binding.error = str(kex)
            return False
        except Exception as ex:
            logger.debug("keynote file resolve failed | %s", ex)
            binding.error = ("Could not resolve this project's keynote "
                             "file.\n%s" % ex)
            return False

        if not kfile:
            binding.error = ("This project has no keynote file set.\n"
                             "Use Change Keynote File to pick one.")
            return False

        entry = self._files.get(kfile)
        if entry is not None and entry.get("conn") is not None:
            # another open project already has this file — share the
            # connection and its single ADC lock
            binding.kfile = kfile
            return True

        try:
            conn = self._open_kfile(kfile)
        except KeynoteSetupError as kex:
            binding.error = str(kex)
            return False
        except Exception as ex:
            binding.error = "Cannot connect to the keynote file.\n%s" % ex
            return False

        self._files[kfile] = {"conn": conn, "ext": kfile_ext,
                              "handler": handler, "shadowed": False}
        self._shadow_once(kfile)
        binding.kfile = kfile
        return True

    def _capture_binding(self):
        """Write the window's live state back into the active binding.

        Also fans the pending-sync flag out to every other open project on
        the SAME keynote file: editing that file leaves their keynote
        tables stale too, and they have to be offered on close.
        """
        b = self._binding
        if b is None:
            return
        b.needs_update = self._needs_update
        b.used_keysdict = self._used_keysdict
        b.used_typesdict = self._used_typesdict
        b.used_viewsdict = self._used_viewsdict
        b.usage_stale = self._usage_stale
        b.cache = self._cache
        b.snapshot_categories = self._snapshot_categories
        b.snapshot_keynotes = self._snapshot_keynotes
        b.error = self._bind_error
        if self._needs_update and self._kfile:
            for other in self._bindings:
                if other is not b and other.kfile == self._kfile:
                    other.needs_update = True
        try:
            b.search_term = self.search_tb.Text or ""
        except Exception:
            b.search_term = ""
        try:
            sel = self.selected_keynote
            b.selected_key = sel.key if sel else None
        except Exception:
            b.selected_key = None
        try:
            b.scroll_offset = self._get_scroll_offset()
        except Exception:
            b.scroll_offset = 0.0

    def _activate_binding(self, binding):
        """Make `binding` the panel's view and redraw.

        Mirrors the binding into the window's own attributes so every
        existing call site (self._conn, self._kfile, the usage maps) keeps
        working unchanged.
        """
        # the previous project's rows are gone from the tree; a key from
        # one file means nothing in another
        self._sel_keys = set()
        self._sel_anchor = None
        self._binding = binding
        self._doc = binding.doc
        self._kfile = binding.kfile
        self._bind_error = binding.error
        entry = self._files.get(binding.kfile) or {}
        self._conn = entry.get("conn")
        self._kfile_ext = entry.get("ext")
        self._kfile_handler = entry.get("handler")
        self._needs_update = binding.needs_update
        self._used_keysdict = binding.used_keysdict
        self._used_typesdict = binding.used_typesdict
        self._used_viewsdict = binding.used_viewsdict
        self._usage_stale = binding.usage_stale
        self._cache = binding.cache
        self._snapshot_categories = binding.snapshot_categories
        self._snapshot_keynotes = binding.snapshot_keynotes

        try:
            self.search_tb.Text = binding.search_term or ""
        except Exception:
            pass
        self._update_full_tree()
        self._update_buttons()
        self._update_status_bar()
        self._update_title()
        if binding.selected_key:
            try:
                self._select_keynote_by_key(binding.selected_key)
            except Exception:
                pass
        try:
            self._set_scroll_offset(binding.scroll_offset)
        except Exception:
            pass
        if self._conn is not None and binding.usage_stale:
            self._queue_usage_refresh()

    def _queue_usage_refresh(self):
        """Re-read this project's tag usage in a valid Revit API context.

        A view switch lands on the WPF dispatcher, which is NOT a Revit API
        context, so the collector has to go through the ExternalEvent.
        """
        holder = {}

        def _query():
            holder["data"] = self.get_used_keynote_elements()

        def _apply():
            if self._closed:
                return
            data = holder.get("data")
            if not data:
                return
            used, types, views, ok = data
            if ok:
                self._used_keysdict = used
                self._used_typesdict = types
                self._used_viewsdict = views
                self._usage_stale = False
            else:
                self._usage_stale = True
            if self._binding is not None:
                self._binding.used_keysdict = self._used_keysdict
                self._binding.used_typesdict = self._used_typesdict
                self._binding.used_viewsdict = self._used_viewsdict
                self._binding.usage_stale = self._usage_stale
            self._update_full_tree()
            self._update_status_bar()

        self._revit_run(_query, callback=_apply, callback_on_error=False,
                        needs_active_doc=False)

    def _retarget(self, doc):
        """Point the panel at `doc`, connecting its keynote file if needed."""
        binding = self._find_binding(doc)
        if binding is not None and (binding.kfile or binding.error):
            # already resolved once this session — swap straight in
            self._capture_binding()
            self._activate_binding(binding)
            return

        if binding is None:
            binding = _DocBinding(doc)
            self._bindings.append(binding)

        def _resolve():
            self._bind_silent(binding)

        def _swap():
            self._capture_binding()
            self._activate_binding(binding)

        # _bind_silent records its own failures, so the swap must happen
        # either way: a project we cannot read still has to be shown, with
        # the reason, rather than leaving the previous project on screen.
        self._revit_run(_resolve, callback=_swap, needs_active_doc=False)

    def _on_view_activated(self, sender, args):
        """Follow the active document.  Runs on the Revit thread.

        Fires for every view change, including within one project, so the
        same-document case must cost nothing.
        """
        if self._closed or self._modal_mode:
            return
        try:
            doc = args.Document
        except Exception:
            return
        if doc is None:
            return
        try:
            if self._doc is not None and self._doc.IsValidObject \
                    and self._doc.Equals(doc):
                self._pending_doc = None
                return
        except Exception:
            pass
        self._pending_doc = doc
        try:
            self._retarget_timer.Stop()
            self._retarget_timer.Start()
        except Exception:
            logger.debug("retarget timer unavailable")

    def _on_retarget_timer_tick(self, sender, args):
        """Bind to whichever project the user actually settled on."""
        try:
            self._retarget_timer.Stop()
        except Exception:
            pass
        if self._closed:
            return
        doc = self._pending_doc
        if doc is None:
            return
        if self._inflight > 0:
            # an action is already queued against the project on screen;
            # swapping now would run it against the wrong model
            try:
                self._retarget_timer.Start()
            except Exception:
                pass
            return
        self._pending_doc = None
        try:
            self._retarget(doc)
        except Exception as ex:
            logger.error("KeynoteManager | could not follow document | %s", ex)

    def _on_doc_closing(self, sender, args):
        """Drop the binding for a project that is going away."""
        if self._closed:
            return
        try:
            doc = args.Document
        except Exception:
            return
        b = self._find_binding(doc)
        if b is None:
            return
        if b.needs_update:
            logger.warning("KeynoteManager | %s closed with keynote changes "
                           "that were never synced to it", b.title)
        try:
            self._bindings.remove(b)
        except ValueError:
            pass
        if b is self._binding:
            self._binding = None
            self._pending_doc = revit.doc
            try:
                self._retarget_timer.Stop()
                self._retarget_timer.Start()
            except Exception:
                pass

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

    def _run_on_finished(self, on_finished):
        """Dispatch a release hook to the WPF thread, after any callback.

        Queued at the same priority as the callback, so it always lands
        after it.  Never raises — a failed release must not take down a
        caller that is already unwinding.
        """
        if not on_finished:
            return
        try:
            self.Dispatcher.BeginInvoke(
                System.Action(ui_guard(on_finished)),
                Windows.Threading.DispatcherPriority.Background)
        except Exception as finex:
            logger.debug("on_finished dispatch failed | %s", finex)

    def _revit_run(self, action, callback=None, callback_on_error=True,
                   on_finished=None, needs_active_doc=True):
        """Queue an action to execute on Revit's main thread.
        Optional callback runs on the WPF thread after the action.

        By default the action is refused if the user switched to a
        different document — otherwise transactions would silently modify
        the wrong model.  Pass needs_active_doc=False for an action that
        names its document explicitly (self._doc) and never reads
        revit.doc: refusing one of those blocks work that would have been
        correct, and leaves the user no way to complete it (#3631).

        Pass callback_on_error=False when the callback reports success or
        discards state, so a failed action cannot masquerade as a good one.

        on_finished ALWAYS runs, on the WPF thread, however the attempt
        ended — completed, refused before the action ran, or never
        dispatched at all.  It is the ONLY safe place to release a guard
        taken before the call.

        Returns False when the action could not be dispatched at all and
        the queued entry was dropped.  Only Accepted and Pending count as
        dispatched, so an unrecognised Raise() result fails safe.
        """

        # A queued action belongs to the project that was on screen when it
        # was queued.  _on_retarget_timer_tick waits while this is non-zero,
        # so the panel cannot swap underneath it.  on_finished always runs
        # exactly once, on every path, which is what keeps this balanced.
        self._inflight += 1

        def _finished():
            self._inflight = max(0, self._inflight - 1)
            if on_finished:
                on_finished()

        def _doc_affine_action():
            if needs_active_doc and not self._is_owned_doc_active():
                raise Exception(
                    "Keynote Manager was opened for a different document.\n"
                    "Switch back to that document, or close and reopen "
                    "the Keynote Manager.")
            action()

        if self._modal_mode:
            _succeeded = True
            try:
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
                    try:
                        self.Dispatcher.BeginInvoke(
                            System.Action(ui_guard(callback)),
                            Windows.Threading.DispatcherPriority.Background)
                    except Exception as cbex:
                        logger.debug("Callback dispatch failed | %s", cbex)
            finally:
                # the modal branch refuses in-line, so this is the only
                # release the caller's guard will ever get (#3631)
                self._run_on_finished(_finished)
            return True

        if self._ext_event is None:
            logger.error("KeynoteManager | ExternalEvent unavailable; "
                         "action not queued")
            forms.alert("Keynote Manager cannot reach Revit right now.\n"
                        "Please try again.")
            self._run_on_finished(_finished)
            return False
        entry = self._ext_handler.queue(_doc_affine_action, callback, self,
                                        callback_on_error=callback_on_error,
                                        on_finished=_finished)
        try:
            request = self._ext_event.Raise()
        except Exception as rex:
            logger.error("KeynoteManager | could not raise ExternalEvent "
                         "| %s", rex)
            self._ext_handler.drop(entry)
            self._run_on_finished(_finished)
            return False
        if request not in (UI.ExternalEventRequest.Accepted,
                           UI.ExternalEventRequest.Pending):
            logger.error("KeynoteManager | Revit rejected the request | %s",
                         request)
            self._ext_handler.drop(entry)
            self._run_on_finished(_finished)
            forms.alert("Revit is not accepting requests right now.\n"
                        "Please try again.")
            return False
        return True

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
                try:
                    vel = doc.GetElement(kn.OwnerViewId)
                    if vel:
                        used_views[key].append(revit.query.get_name(vel))
                except Exception:
                    pass
        except Exception as ex:
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
            used = self._used_keysdict
            self._usage_stale = True
        return dict((k, list(used.get(k, []))) for k in keys)

    # =========================================================================
    # CONFIG
    # =========================================================================

    def save_config(self):
        if not self._kfile:
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

    def _resolve_kfile_for(self, doc):
        """Resolve (kfile, kfile_ext, handler) for `doc`.

        Reads nothing off self and assigns nothing, so a view switch can
        resolve a project the panel is not showing yet.  Raises
        KeynoteSetupError when a file is configured but unreachable;
        returns a None kfile when the project simply has none set.

        Resolution order:
          1. Local keynote file (revit.query.get_local_keynote_file)
          2. External/cloud file via ADC (Autodesk Desktop Connector)
          3. Raise if ADC is needed and not available
        """
        kfile = revit.query.get_local_keynote_file(doc=doc)
        if kfile:
            return kfile, None, None

        kfile_ext = revit.query.get_external_keynote_file(doc=doc)
        if not kfile_ext:
            return None, None, "unknown"

        # CRITICAL: call is_available() FIRST on a clean AppDomain.
        # No legacy DLL probing before this point.
        if adc.is_available():
            return self._resolve_adc_keynote(kfile_ext), kfile_ext, "adc"

        raise KeynoteSetupError(
            "{} is not available.\n\n"
            "Please ensure Desktop Connector is running "
            "in the system tray.".format(adc.ADC_NAME)
        )

    def _determine_kfile(self):
        """Resolve the keynote file for the document this window owns."""
        # resolve against the OWNING document, never whatever is active now
        (self._kfile, self._kfile_ext,
         self._kfile_handler) = self._resolve_kfile_for(self._doc)

    def _resolve_adc_keynote(self, kfile_ext):
        """Resolve a cloud keynote path to a local file via ADC.

        Takes the ADC lock and does NOT release it on a project switch: the
        panel follows the active document, so dropping and retaking the
        lock each time would hand it to a colleague mid-edit.  Every lock
        taken here is released in window_closing.
        """
        try:
            local_kfile = adc.get_local_path(kfile_ext)

            if not local_kfile:
                raise KeynoteSetupError(
                    "Cannot resolve local path via {}.".format(adc.ADC_NAME)
                )

            try:
                locked, owner = adc.is_locked(kfile_ext)
                if locked:
                    raise KeynoteSetupError(
                        "Keynote file is locked by {}.".format(owner))
            except KeynoteSetupError:
                raise
            except Exception:
                pass

            try:
                adc.sync_file(kfile_ext)
                adc.lock_file(kfile_ext)
            except Exception:
                pass

            return local_kfile

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

    def _preflight_kfile(self, kfile):
        """Prove `kfile` is writable and its folder allows lock sidecars.

        DeffrelDB creates/deletes '<kfile>.lock' sidecar files in INFINITE
        retry loops with no timeout (DataStore.CreateLock/DeleteLock).  If
        the folder refuses file create/delete — offline cloud folder, sync
        client holding handles — Revit hangs at 100% CPU forever.  Prove
        the folder allows it before connecting.
        """
        if not os.access(kfile, os.W_OK):
            raise KeynoteSetupError("Keynote file is read-only:\n" + kfile)
        probe = kfile + ".probe_{}".format(uuid.uuid4().hex[:6])
        try:
            with open(probe, "w"):
                pass
            os.remove(probe)
        except Exception as probex:
            raise KeynoteSetupError(
                "The keynote file's folder does not allow creating lock "
                "files (offline or locked by a sync client?):\n{}\n\n{}"
                .format(op.dirname(kfile), probex))

    def _open_kfile(self, kfile):
        """Connect to `kfile` with no prompting.  Raises KeynoteSetupError.

        The silent counterpart to _connect_kfile: a view switch must never
        raise a file picker or a Convert dialog, so everything this cannot
        handle becomes an error string on the binding instead.
        """
        if not kfile or not op.exists(kfile):
            raise KeynoteSetupError("Keynote file not found:\n%s" % kfile)
        self._preflight_kfile(kfile)
        try:
            return kdb.connect(kfile)
        except System.TimeoutException as toutex:
            raise KeynoteSetupError(toutex.Message)
        except Exception as ex:
            raise KeynoteSetupError(
                "Cannot connect to this project's keynote file.\n%s\n\n"
                "It may need conversion to the new format — open the "
                "project and use Change Keynote File." % ex)

    def _shadow_once(self, kfile):
        """Back the keynote file up once per file per session."""
        entry = self._files.get(kfile)
        if not entry or entry.get("shadowed"):
            return
        try:
            shadow = script.get_data_file(
                "kshadow_" + op.basename(kfile), "txt")
            shutil.copy(kfile, shadow)
            entry["shadowed"] = True
            logger.debug("Keynote shadow backup: %s", shadow)
        except Exception as shex:
            logger.debug("Shadow backup failed | %s", shex)

    def _register_file(self):
        """Publish the window's current connection into the shared file map.

        _activate_binding rebuilds self._conn from self._files on every
        project switch, so a connection opened anywhere ELSE — first
        open, Change Keynote File, Convert — has to be registered here
        or switching away and back would find nothing and blank the tree.
        """
        if not self._kfile or self._conn is None:
            return
        entry = self._files.get(self._kfile)
        if entry is None:
            entry = {"shadowed": False}
            self._files[self._kfile] = entry
        entry["conn"] = self._conn
        entry["ext"] = self._kfile_ext
        entry["handler"] = self._kfile_handler
        self._bind_error = None
        if self._binding is not None:
            self._binding.kfile = self._kfile
            self._binding.error = None

    def _drop_file_entry(self, kfile, reason):
        """Forget a keynote file so a project switch cannot resurrect it.

        Clearing self._conn alone is not enough: it is only a mirror of
        self._files, and the next _activate_binding would hand the dead
        connection straight back.
        """
        entry = self._files.pop(kfile, None)
        if entry:
            conn = entry.get("conn")
            if conn is not None:
                try:
                    conn.Dispose()
                except Exception:
                    pass
        for b in self._bindings:
            if b.kfile == kfile:
                b.kfile = None
                b.error = reason
        if self._kfile == kfile:
            self._conn = None
            self._bind_error = reason

    def _update_title(self):
        """Rebuild the title from scratch for the currently bound project.

        Never append: with the panel following the active document this
        runs on every switch, and '+=' would stack suffixes.
        """
        bits = [self._base_title]
        if self._binding is not None:
            bits.append("— " + self._binding.title)
        if self._kfile_handler == "adc":
            bits.append("( ACC / FORMA )")
        if self._modal_mode:
            bits.append("[Safe Mode]")
        try:
            self.Title = " ".join(bits)
        except Exception:
            pass

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
            if not self._kfile or not op.exists(self._kfile):
                raise KeynoteSetupError(
                    "No valid keynote file set for this project.")
            # Release any previous connection (reconnect via Change File)
            if self._conn:
                try:
                    self._conn.Dispose()
                except Exception:
                    pass
                self._conn = None

            self._preflight_kfile(self._kfile)

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

        # Register BEFORE the backup: _shadow_once reads the file entry,
        # and every later project switch reads the connection from it.
        self._register_file()
        if self._conn and self._kfile:
            self._shadow_once(self._kfile)

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
            _gone = ("The keynote file is missing — renamed or removed "
                     "by the sync client?\n{}\n\nUse Change Keynote File "
                     "to reconnect.".format(self._kfile))
            self._drop_file_entry(self._kfile, _gone)
            forms.alert(_gone)
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

        # Rows are rebuilt from the file on every refresh, so re-apply the
        # highlight to the NEW objects, dropping keys that no longer exist.
        if self._sel_keys:
            live = self._flat_display_rows(filtered=False)
            self._sel_keys &= set(r.key for r in live)
            self._apply_selection_marks(live)

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
        if self._doc_changed_app is not None:
            try:
                self._doc_changed_app.DocumentClosing += self._on_doc_closing
            except Exception:
                logger.debug("DocumentClosing unavailable")
        # ViewActivated is what tells us the user switched projects.  Only
        # the modeless window follows: in safe mode Revit is blocked by the
        # dialog and there is nothing to follow.
        if not self._modal_mode:
            try:
                self._uiapp = HOST_APP.uiapp
                self._uiapp.ViewActivated += self._on_view_activated
                self._follow_error = None
            except Exception as _subex:
                # Surfaced in the status bar, not just logged: a silent
                # failure here is indistinguishable from the panel simply
                # not reacting, which costs a whole test cycle to diagnose.
                self._uiapp = None
                self._follow_error = str(_subex) or "ViewActivated refused"
                logger.error("KeynoteManager | cannot follow the active "
                             "document | %s", _subex)
        else:
            self._follow_error = "safe mode"
        self._update_status_bar()

    def _on_doc_changed(self, sender, args):
        """Fires on the Revit thread after any document change.
        Refreshes keynote usage data and updates the tree."""
        if self._closed or self._refresh_pending:
            return
        # Only refresh the tree for the project on screen, but a change in
        # another open project still invalidates ITS cached usage map, so
        # flag that binding rather than dropping the event.
        try:
            changed_doc = args.GetDocument()
            if changed_doc and not changed_doc.Equals(self._doc):
                other = self._find_binding(changed_doc)
                if other is not None:
                    other.usage_stale = True
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
        # A plain click starts a new selection.  Ctrl/Shift clicks set
        # IsSelected themselves and suppress this, so the rows they just
        # gathered are not thrown away again.
        if not self._suspend_sel_reset:
            focus = self.selected_keynote
            self._sel_keys = set([focus.key]) if focus else set()
            self._sel_anchor = focus.key if focus else None
            self._apply_selection_marks()
            self._update_status_bar()
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
        elif key == Windows.Input.Key.C and mods == ctrl:
            if self.selected_keynote:
                self.copy_keynote(sender, args)
                args.Handled = True
        elif key == Windows.Input.Key.V and mods == ctrl:
            self.paste_keynote(sender, args)
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

    def _cancel_shift_release_wait(self):
        """Stop and forget any in-flight SHIFT-release wait."""
        timer = self._shift_release_timer
        self._shift_release_timer = None
        if timer is not None:
            try:
                timer.Stop()
            except Exception as ex:
                logger.debug("Shift-release timer stop failed | %s" % ex)

    def _place_when_clear(self, rec):
        """Place `rec`, but not while a disturbing modifier is still held.

        Revit reads modifier state as it dispatches a posted command and
        starts its interactive tool, and discards the placement if SHIFT is
        down — so wait for a clean keyboard first.

        Polls rather than hooking KeyUp: this window may not hold keyboard
        focus (the mouse-down that started this was suppressed), so a WPF
        KeyUp is not guaranteed to arrive.

        Only ever ONE wait may be in flight.  Each timer closes over its own
        `rec`, so a second SHIFT+CLICK while SHIFT is still held would leave
        two timers polling and place BOTH rows when SHIFT came up.  Note the
        cancel has to happen before the immediate-placement branch too: a
        gesture that arrives with SHIFT already released must still cancel
        the earlier one, or the stale timer fires later on its own.
        """
        self._cancel_shift_release_wait()

        if not self._place_modifier_held():
            self._place_keynote(rec)
            return

        timer = DispatcherTimer()
        timer.Interval = TimeSpan.FromMilliseconds(40)
        # Bound the wait: a stuck or sticky SHIFT must not strand the
        # placement forever.  25 x 40ms = 1s, then place regardless.
        state = {"ticks": 0}

        def _tick(sender, args):
            # A tick queued before this timer was cancelled can still be
            # delivered afterwards.  Ignore it unless this is still the live
            # wait — otherwise a superseded gesture would place its own row
            # and null out the newer timer's slot on the way past.
            if self._shift_release_timer is not timer:
                try:
                    timer.Stop()
                except Exception:
                    pass
                return
            # The window can be closed inside the wait — never place into a
            # torn-down window (its ExternalEvent is already disposed).
            if self._closed:
                self._cancel_shift_release_wait()
                return
            state["ticks"] += 1
            timed_out = state["ticks"] > 25
            if self._place_modifier_held() and not timed_out:
                return
            self._cancel_shift_release_wait()
            self._place_keynote(rec)

        # A DispatcherTimer tick fires after the command has returned, so it
        # needs shielding like every other entry point; a local closure
        # cannot go in _GUARDED_ENTRY_POINTS by name.
        timer.Tick += ui_guard(_tick)
        # Held on the instance so the timer cannot be collected mid-wait.
        self._shift_release_timer = timer
        timer.Start()

    def _hint(self, message):
        """Show a one-line, non-modal note in the status bar.

        Not a TaskDialog: these fire on a mis-aimed click, where a modal box
        would be worse than saying nothing.  Cleared by the next
        _update_status_bar().
        """
        try:
            self.statusRight.Text = message
        except Exception:
            pass

    @staticmethod
    def _modifier_down(name):
        """True when the named modifier ("Shift"/"Control"/"Alt") is held.

        Two sources, because neither alone is reliable: WPF's
        Keyboard.Modifiers only reflects key events WPF itself has seen, so
        it reads empty on the click that reactivates this window from Revit,
        while WinForms' Control.ModifierKeys wraps Win32 GetKeyState and
        reports true key state regardless of focus.  Either one is enough.

        Flag test rather than equality: the tree now binds Ctrl+Click,
        Shift+Click AND Alt+Click, so each is tested on its own and a
        second modifier held alongside must not eat the gesture.
        """
        try:
            mods = Windows.Input.Keyboard.Modifiers
            flag = getattr(Windows.Input.ModifierKeys, name)
            if (mods & flag) == flag:
                return True
        except Exception:
            pass
        try:
            wmods = Windows.Forms.Control.ModifierKeys
            wflag = getattr(Windows.Forms.Keys, name)
            return (wmods & wflag) == wflag
        except Exception:
            return False

    @staticmethod
    def _shift_is_down():
        """True when SHIFT is physically held."""
        return KeynoteManagerWindow._modifier_down("Shift")

    @staticmethod
    def _place_modifier_held():
        """True while a modifier that would disturb a posted command is held.

        Revit reads modifier state as it dispatches the posted command and
        starts its interactive tool, so the placement waits for a clean
        keyboard.  Alt is included because Alt+Click is now the gesture
        that arms it.
        """
        return (KeynoteManagerWindow._modifier_down("Shift")
                or KeynoteManagerWindow._modifier_down("Alt"))

    @staticmethod
    def _treeviewitem_from_source(source):
        """Walk up from a clicked visual to the TreeViewItem that owns it.

        args.OriginalSource is whatever was physically hit inside the item
        template — the key badge, a TextBlock, the row Border — and can even
        be a content element such as a Run, which VisualTreeHelper refuses.
        Fall back to the logical tree for anything that is not a Visual.

        Returns None for a click on the expand/collapse arrow, leaving that
        gesture alone: the arrow is the only ToggleButton inside a row, the
        item template being Borders and TextBlocks only.
        """
        dep = source
        while dep is not None:
            if isinstance(dep, Windows.Controls.Primitives.ToggleButton):
                return None
            if isinstance(dep, Windows.Controls.TreeViewItem):
                return dep
            try:
                if isinstance(dep, Windows.Media.Visual):
                    dep = Windows.Media.VisualTreeHelper.GetParent(dep)
                else:
                    dep = Windows.LogicalTreeHelper.GetParent(dep)
            except Exception:
                return None
        return None

    def tree_preview_mouse_down(self, sender, args):
        # CTRL+CLICK toggles a row, SHIFT+CLICK extends the range,
        # ALT+CLICK places the row.
        self._shift_place_pending = None

        ctrl = shift = alt = False
        tvi = None
        try:
            ctrl = self._modifier_down("Control")
            shift = self._modifier_down("Shift")
            alt = self._modifier_down("Alt")
            if ctrl or shift or alt:
                tvi = self._treeviewitem_from_source(args.OriginalSource)
        except Exception as ex:
            # A failed hit-test degrades to an ordinary click rather than
            # breaking a mouse handler.
            logger.debug("Modifier click hit-test failed | %s" % ex)

        # ALT+CLICK places the row (this was SHIFT+CLICK before multi-select
        # took that gesture; the toolbar button and context menu are
        # unchanged).  Checked first so Alt wins over a stray Shift.
        if alt:
            if tvi is None:
                # Empty space below the rows, or the expand/collapse arrow.
                self._hint("Alt+Click a keynote row to place it")
            else:
                tvi.IsSelected = True
                self._drag_start_point = None
                args.Handled = True
                self._shift_place_pending = tvi.DataContext
            return

        if (ctrl or shift) and tvi is not None:
            rec = getattr(tvi, "DataContext", None)
            if rec is not None and hasattr(rec, "key"):
                if ctrl:
                    self._toggle_in_selection(rec)
                else:
                    self._extend_selection_to(rec)
                # Move WPF's own focus row to the clicked row without
                # letting selected_keynote_changed collapse what we just
                # gathered.
                self._suspend_sel_reset = True
                try:
                    tvi.IsSelected = True
                finally:
                    self._suspend_sel_reset = False
                self._update_buttons()
                self._drag_start_point = None
                args.Handled = True
                return

        self._drag_start_point = args.GetPosition(sender)

    def tree_preview_mouse_up(self, sender, args):
        """Place the row an ALT+CLICK armed on mouse-down, if any.

        Marshalled off the input event rather than run inline: Revit drops a
        posted command that arrives while WPF is still dispatching a mouse
        gesture, so Background priority is used to reach the same settled
        dispatcher frame a Button.Click handler runs from.

        args is not marked Handled — the matching mouse-down was already
        suppressed, and letting WPF finish its normal button-up bookkeeping
        keeps its input state consistent.
        """
        pending = self._shift_place_pending
        self._shift_place_pending = None
        if pending is None:
            return
        try:
            self.Dispatcher.BeginInvoke(
                System.Action(
                    ui_guard(lambda: self._place_when_clear(pending))),
                Windows.Threading.DispatcherPriority.Background)
        except Exception as ex:
            logger.debug("Place dispatch failed | %s" % ex)
            self._place_when_clear(pending)

    def tree_item_right_click(self, sender, args):
        """Select the row under the cursor before its context menu opens.

        The menu reuses the toolbar's handlers, which read
        self.selected_keynote — and right-click does not move TreeView
        selection on its own the way left-click does.  Without this, every
        command on the menu would act on whatever was previously selected
        rather than the row that was actually clicked.

        Right-clicking INSIDE an existing multi-selection is the exception:
        the menu is about to act on every selected row, so moving the focus
        must not collapse the selection down to the row under the cursor.
        Right-clicking OUTSIDE it still starts a fresh single selection,
        which is what the gesture means everywhere else.
        """
        tvi = self._treeviewitem_from_source(sender)
        if tvi is None:
            return
        rec = getattr(tvi, "DataContext", None)
        inside = (rec is not None and hasattr(rec, "key")
                  and len(self._sel_keys) > 1 and rec.key in self._sel_keys)
        self._suspend_sel_reset = inside
        try:
            tvi.IsSelected = True
            tvi.Focus()
        finally:
            self._suspend_sel_reset = False

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
                self._drag_left_window = False
                self._drag_cancelled = False
                effect = getattr(Windows.DragDropEffects, "None")
                try:
                    data = Windows.DataObject("keynote", sel)
                    # Subscribed only for the life of the drag: these fire
                    # continuously and have nothing to say otherwise.
                    self.keynotes_tv.GiveFeedback += self._drag_give_feedback
                    self.keynotes_tv.QueryContinueDrag += \
                        self._drag_query_continue
                    try:
                        effect = Windows.DragDrop.DoDragDrop(
                            self.keynotes_tv, data, Windows.DragDropEffects.Move
                        )
                    finally:
                        self.keynotes_tv.GiveFeedback -= \
                            self._drag_give_feedback
                        self.keynotes_tv.QueryContinueDrag -= \
                            self._drag_query_continue
                except Exception as ex:
                    logger.debug("Drag failed | %s" % ex)
                finally:
                    self._is_dragging = False
                    self._drag_start_point = None
                self._maybe_place_after_drag(sel, effect)

    def _cursor_outside_window(self):
        """True when the pointer is outside this window's own rectangle.

        Both sides are DEVICE pixels: PointToScreen maps through the
        window's HWND, and WinForms' Cursor.Position is already physical.
        Comparing against Left/Top/Width instead would drift on a scaled
        display, because those are device-independent units.

        Fails CLOSED — an unanswerable hit-test must never be read as
        "the user dropped this on Revit".
        """
        try:
            pos = Windows.Forms.Cursor.Position
            origin = self.PointToScreen(Windows.Point(0, 0))
            corner = self.PointToScreen(
                Windows.Point(self.ActualWidth, self.ActualHeight))
        except Exception as ex:
            logger.debug("drag hit-test failed | %s" % ex)
            return False
        return not (origin.X <= pos.X <= corner.X
                    and origin.Y <= pos.Y <= corner.Y)

    def _drag_query_continue(self, sender, args):
        """Track where the drag is and whether the user bailed out.

        Sampled during the drag rather than read once it ends: the pointer
        can move between the button release and DoDragDrop returning.
        """
        try:
            if args.EscapePressed:
                self._drag_cancelled = True
            self._drag_left_window = self._cursor_outside_window()
        except Exception as ex:
            logger.debug("drag tracking failed | %s" % ex)

    def _drag_give_feedback(self, sender, args):
        """Show a placement cursor once the drag leaves the panel.

        Revit registers no drop target for our data, so Windows would show
        the "no drop" cursor over the drawing area — telling the user
        the exact opposite of what is about to happen.
        """
        if not self._drag_left_window:
            return
        try:
            args.UseDefaultCursors = False
            Windows.Input.Mouse.SetCursor(Windows.Input.Cursors.Cross)
            args.Handled = True
        except Exception as ex:
            logger.debug("drag cursor failed | %s" % ex)

    def _maybe_place_after_drag(self, rec, effect):
        """Arm placement for a keynote dragged out onto the Revit window.

        There is no drop to react to: Revit cannot accept a WPF drag, so
        nothing outside this window ever reports an effect.  DoDragDrop is
        synchronous though, so a drag that ENDED with no effect while the
        pointer was outside the panel is one that finished somewhere we do
        not own — in practice the drawing area behind us.

        Deliberately conservative.  A drag cancelled with ESC, one that
        dropped back onto the tree (which reparents and reports Move), and
        one whose hit-test could not be answered all place nothing.

        The placement itself is marshalled to a settled dispatcher frame
        for the same reason the Alt+Click path is: Revit drops a posted
        command that arrives while WPF is still dispatching the gesture.
        """
        if self._closed or self._modal_mode or rec is None:
            return
        if self._drag_cancelled or not self._drag_left_window:
            return
        if effect != getattr(Windows.DragDropEffects, "None"):
            return          # the tree handled it: that was a reparent
        try:
            self.Dispatcher.BeginInvoke(
                System.Action(ui_guard(lambda: self._place_when_clear(rec))),
                Windows.Threading.DispatcherPriority.Background)
        except Exception as ex:
            logger.debug("drag placement dispatch failed | %s" % ex)
            self._place_when_clear(rec)

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

    @staticmethod
    def _clear_row_highlight(row):
        """Remove a row's drag highlight, back to TRANSPARENT — not null.

        A null Background is not hit-testable, and the row Border relies on
        Transparent (set in KeynoteManagerWindow.xaml) so clicks anywhere in
        the row resolve to it.  Clearing to null here would silently stop
        the row's empty space responding to clicks after the first drag
        passed over it.  ClearValue is no help: the template's attribute IS
        the local value, so clearing it falls back to null.
        """
        if hasattr(row, "Background"):
            row.Background = Windows.Media.Brushes.Transparent

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
        self._clear_row_highlight(sender)

    def tree_drop(self, sender, args):
        pass

    def tree_item_drop(self, sender, args):
        """Drop handler — reparent the dragged node under the target."""
        self._clear_row_highlight(sender)

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

    def _remove_many(self, recs):
        """Delete every selected row that can go, and report the rest.

        Blockers CASCADE UPWARD: a group can only go once everything under
        it goes, so one in-use keynote also spares its parent, and its
        parent's parent.  That is settled to a fixpoint before anything is
        written, and the skipped rows are named in the confirmation rather
        than only afterwards, so the delete is never a surprise.

        What does run is still one compensated write, so the keynote file
        is never left half-changed even though the batch is partial.
        """
        try:
            db_keynotes = kdb.get_keynotes(self._conn)
        except Exception as ex:
            forms.alert("Keynote file is busy — nothing was deleted.\n"
                        "%s\n\nPlease try again." % ex)
            return

        children_of = defaultdict(list)
        for knote in db_keynotes:
            if knote.parent_key:
                children_of[knote.parent_key].append(knote.key)

        deletable = set(r.key for r in recs)
        blocked = OrderedDict()

        for rec in recs:
            if rec.locked:
                blocked[rec.key] = ("locked by %s"
                                    % (rec.owner or "another user"))
            elif rec.used:
                blocked[rec.key] = "in use in the model"
        for key in blocked:
            deletable.discard(key)

        # Fixpoint: dropping one row can block its parent, which can block
        # ITS parent.  Each pass either removes a key from `deletable` or
        # changes nothing, so this always settles.
        changed = True
        while changed:
            changed = False
            for rec in recs:
                if rec.key not in deletable:
                    continue
                staying = [c for c in children_of.get(rec.key, [])
                           if c not in deletable]
                if staying:
                    blocked[rec.key] = ("%d row(s) under it are staying"
                                        % len(staying))
                    deletable.discard(rec.key)
                    changed = True

        def _blocked_lines(limit):
            items = list(blocked.items())[:limit]
            out = "\n  ".join("%s — %s" % (k, why) for k, why in items)
            if len(blocked) > limit:
                out += "\n  ... and {} more".format(len(blocked) - limit)
            return out

        going = [r for r in recs if r.key in deletable]
        if not going:
            forms.alert("Nothing could be deleted.\n\n  "
                        + _blocked_lines(12))
            return

        shown = [r.key for r in going[:12]]
        msg = "Delete these {} rows?\n\n  {}".format(
            len(going), "\n  ".join(shown))
        if len(going) > 12:
            msg += "\n  ... and {} more".format(len(going) - 12)
        if blocked:
            msg += ("\n\nSkipping {} row(s):\n\n  ".format(len(blocked))
                    + _blocked_lines(8))
        unverified = [r.key for r in going if self._usage_unknown_note(r.key)]
        if unverified:
            # same caveat _confirm_delete makes for a single row: an
            # unverified usage map reports everything as unused, so the
            # rec.used guard above can pass vacuously
            msg += ("\n\nUsage could not be verified for {} of these. Any "
                    "tag still pointing at a deleted key would keep that key "
                    "with no matching row in the keynote file."
                    .format(len(unverified)))
        if not forms.alert(msg, yes=True, no=True):
            return

        # `going` keeps tree order (parents first); reversing a pre-order
        # walk puts every child ahead of its parent at any depth
        rows = [{"key": r.key, "text": r.text, "parent": r.parent_key,
                 "is_category": r.is_category}
                for r in reversed(going)]
        try:
            removed = kdb.delete_records(self._conn, rows)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return
        except Exception as ex:
            forms.alert("Delete failed — nothing was removed.\n%s" % ex)
            return

        self._needs_update = True
        self._set_selection([])
        if blocked:
            self._hint("Deleted {} rows, skipped {}".format(removed,
                                                            len(blocked)))
        else:
            self._hint("Deleted {} rows".format(removed))

    def remove_keynote(self, sender, args):
        picked = self.selected_keynotes
        if len(picked) > 1:
            if not self._conn:
                forms.alert("No keynote file is connected.")
                return
            self._remove_many(picked)
            self._update_full_tree()
            self._update_status_bar()
            return

        sel = self.selected_keynote
        if not sel:
            return
        if not self._conn:
            forms.alert("No keynote file is connected.")
            return

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
            forms.alert("No keynote file is connected.")
            return
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

        self._revit_run(_do, callback=_update_status, callback_on_error=False)

    def place_keynote(self, sender, args):
        self._place_keynote(self.selected_keynote)

    def _place_keynote(self, sel):
        """Arm Revit's keynote-tag tool with `sel`'s key.

        Shared by the toolbar button (on the current selection) and by
        ALT+CLICK on a tree row (on the row clicked).  Takes the record
        explicitly rather than reading self.selected_keynote, so the
        shift-click path cannot place a keynote other than the one clicked.
        """
        if not sel:
            return
        if sel.locked:
            self._hint("%s is locked by another user — cannot place" % sel.key)
            return
        if not sel.parent_key:
            self._hint("%s is a group — Alt+Click a keynote to place"
                       % sel.key)
            return

        if self._modal_mode:
            forms.alert(
                "Placing keynotes needs the modeless window, which requires "
                "a persistent engine (see SAFE MODE in the status bar).\n\n"
                "Close the Keynote Manager, then place the tag — or reload "
                "pyRevit so the tool gets a persistent engine.",
                title="Not available in Safe Mode")
            return

        sel_key = sel.key
        postcmd = self.postable_keynote_command

        def _do():

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

            self._hint("Placing %s — click in the view" % sel_key)


        self._revit_run(_do, callback=_on_placed, callback_on_error=False)

    def _place_keynote_as(self, sender, args, radio):
        """Place the selection as `radio`'s keynote type, then restore.

        Lets a single context-menu click place a specific keynote type
        without disturbing the user's standing Place choice, which is put
        back to whatever it was checked to before.

        Restoring as soon as place_keynote() returns — rather than from its
        async completion callback — is safe: _place_keynote reads
        self.postcmd_idx synchronously via self.postable_keynote_command
        and captures the result in a local before it ever queues the
        PostCommand on the ExternalEvent.
        """
        prev_idx = self.postcmd_idx
        try:
            self.postcmd_idx = self.postcmd_options.index(radio)
            self.place_keynote(sender, args)
        finally:
            self.postcmd_idx = prev_idx

    def place_user_keynote(self, sender, args):
        self._place_keynote_as(sender, args, self.userknote_rb)

    def place_element_keynote(self, sender, args):
        self._place_keynote_as(sender, args, self.elementknote_rb)

    def place_material_keynote(self, sender, args):
        self._place_keynote_as(sender, args, self.materialknote_rb)

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
                self._drop_file_entry(self._kfile, str(kex))
                forms.alert(str(kex))
                self._update_full_tree()
                self._update_status_bar()
                self._update_title()
                return
            self._needs_update = True
            self._refresh_used_keynotes()
            self._update_full_tree()
            self._update_status_bar()
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
            # success if the update transaction failed.
            # needs_active_doc=False: the sync names self._doc explicitly,
            # so it is correct from whichever project is in front (#3631).
            self._revit_run(_do_update, callback=_on_update_complete,
                            callback_on_error=False,
                            needs_active_doc=False)
        else:
            forms.alert("The Revit model is already up to date.", title="Up to Date")

    def _dirty_bindings(self):
        """Open projects whose keynote table is stale.

        Call _capture_binding() on the WPF thread first: the active
        project's pending flag lives on the window until it is captured.
        """
        out = []
        for b in self._bindings:
            if b.needs_update and b.is_live():
                out.append(b)
        return out

    def _sync_all_dirty(self):
        """Reload the keynote table in every open project that needs it.

        One project failing must not hide another that succeeded, so each
        is attempted, successes are cleared as they go, and the failures
        are raised together at the end — which keeps the
        callback_on_error gate meaningful for the caller.
        """
        failures = []
        for b in self._dirty_bindings():
            try:
                self._sync_doc_keynotes(b.doc)
                b.needs_update = False
            except Exception as ex:
                failures.append("%s: %s" % (b.title, ex))
        if self._binding is not None:
            self._needs_update = self._binding.needs_update
        if failures:
            raise Exception("Some projects were not updated:\n\n"
                            + "\n".join(failures))

    def _sync_model_keynotes(self):
        """Reload the bound project's keynote table."""
        self._sync_doc_keynotes(self._doc)

    def _sync_doc_keynotes(self, doc):
        """Reload `doc`'s keynote table and VERIFY that it happened.

        Neither pyRevit helper reports failure: revit.Transaction swallows
        commit errors and discards Commit()'s TransactionStatus
        (revit/db/transaction.py), and revit.update.update_linked_keynotes
        throws away the ExternalResourceLoadStatus that
        KeynoteTable.Reload() returns (revit/db/update.py).  A failed sync
        would therefore return normally and be reported as success.  This
        RAISES instead, so the callback_on_error gate actually engages.
        """
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
        """Offer to sync pending changes before closing.

        Invariant:
            The prompt is owned by this window, so Close cannot re-enter
            while it is up.  The SYNC that follows is asynchronous and the
            window stays live across it, so the guard held over the
            ExternalEvent MUST be released from on_finished and nowhere
            else, or the window becomes unclosable (#3548, #3631).
        """
        if not self._close_pending:
            # the project on screen keeps its pending flag on the window
            self._capture_binding()
            dirty = self._dirty_bindings()
        else:
            dirty = []

        if dirty:
            if self._close_sync_pending:
                args.Cancel = True
                return

            if len(dirty) == 1:
                _msg = ("Keynote file has been modified.\n"
                        "Sync changes to the Revit model before "
                        "closing?")
            else:
                # a shared keynote file leaves every open project that
                # uses it stale, not just the one that was edited
                _msg = ("Keynote files have been modified.\n"
                        "Sync changes to these open projects before "
                        "closing?\n\n  "
                        + "\n  ".join(b.title for b in dirty))

            # Owned by THIS window rather than by Revit.  forms.alert builds
            # a Revit TaskDialog, which is modal to Revit's main window but
            # NOT to a modeless WPF window: the manager could be raised over
            # its own prompt, leaving a window that ignored X with no dialog
            # anywhere in sight (#3631).  An owned MessageBox disables this
            # window while it is up, so the re-entrant Close that
            # _close_prompt_open existed to absorb cannot happen at all.
            res = Windows.MessageBox.Show(
                self, _msg, "Keynote Manager",
                Windows.MessageBoxButton.YesNo,
                Windows.MessageBoxImage.Question)

            if res == Windows.MessageBoxResult.Yes:
                args.Cancel = True
                self._close_sync_pending = True

                def _do_update():
                    self._sync_all_dirty()

                def _sync_done():
                    self._close_pending = True
                    self._finalize_close()

                def _release_close_sync():
                    self._close_sync_pending = False

                # needs_active_doc=False: _sync_model_keynotes reloads
                # self._doc's keynote table and never reads revit.doc, so
                # refusing it because another project is in front only
                # blocks a sync that would have succeeded.
                # on_finished: the refusal raises BEFORE the action runs, so
                # releasing inside _do_update would strand the guard and
                # make every later Close a silent no-op (#3631).
                self._revit_run(_do_update, callback=_sync_done,
                                callback_on_error=False,
                                on_finished=_release_close_sync,
                                needs_active_doc=False)
                return

        # Proceed with cleanup
        self._closed = True
        try:
            self._search_timer.Stop()
        except Exception:
            pass
        try:
            self._retarget_timer.Stop()
        except Exception:
            pass
        self._cancel_shift_release_wait()
        if self._doc_changed_app:
            try:
                self._doc_changed_app.DocumentChanged -= self._on_doc_changed
            except Exception:
                pass
            try:
                self._doc_changed_app.DocumentClosing -= self._on_doc_closing
            except Exception:
                pass
            self._doc_changed_app = None
        if self._uiapp is not None:
            try:
                self._uiapp.ViewActivated -= self._on_view_activated
            except Exception:
                pass
            self._uiapp = None
        try:
            self.save_config()
        except Exception as ex:
            logger.debug("Save config failed | %s" % ex)
        # Release EVERY keynote file this window touched, not just the one
        # on screen: following holds each project's ADC lock until close,
        # and a lock left behind blocks a colleague with nothing in the UI
        # to say so.
        for _kpath, _kentry in list(self._files.items()):
            if _kentry.get("handler") == "adc" and _kentry.get("ext"):
                try:
                    adc.unlock_file(_kentry["ext"])
                except Exception:
                    logger.debug("could not unlock %s", _kpath)
            _kconn = _kentry.get("conn")
            if _kconn is not None:
                try:
                    _kconn.Dispose()
                except Exception:
                    pass
                _kentry["conn"] = None
        self._files = {}
        self._conn = None
        if self._ext_event is not None:
            try:
                self._ext_event.Dispose()
            except Exception:
                pass
            self._ext_event = None
        if not self._modal_mode:
            try:
                envvars.set_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR, None)
            except Exception:
                pass


# =============================================================================
# APPLY UI EXCEPTION SHIELD
# =============================================================================


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
    (PastePreviewWindow, (
        "take_all", "only_new", "take_none", "do_paste", "do_cancel",
    )),
    (KeynoteManagerWindow, (
        # XAML-wired
        "add_category", "add_keynote", "change_keynote_file", "clear_search",
        "copy_keynote", "paste_keynote",
        "collapse_all_tree", "custom_filter", "duplicate_keynote",
        "edit_keynote", "edit_category_inline", "expand_all_tree",
        "export_keynotes", "export_visible_keynotes", "import_keynotes",
        "indent_keynote", "outdent_keynote", "move_up", "move_down",
        "place_keynote", "place_user_keynote", "place_element_keynote",
        "place_material_keynote",
        "refresh", "rekey_keynote", "remove_keynote",
        "show_case_menu", "show_keynote", "show_keynote_file",
        "to_upper", "to_lower", "to_title", "to_sentence",
        "update_model", "window_closing", "window_keydown",
        "search_txt_changed", "selected_keynote_changed",
        "tree_preview_mouse_down", "tree_preview_mouse_up",
        "tree_preview_mouse_move",
        "tree_double_click", "tree_drag_over", "tree_drop",
        "tree_item_drag_over", "tree_item_drag_leave", "tree_item_drop",
        "tree_item_right_click",
        # code-wired
        "_on_search_timer_tick", "_on_window_loaded", "_on_doc_changed",
        "_on_doc_closing", "_on_view_activated", "_on_retarget_timer_tick",
        "_drag_query_continue", "_drag_give_feedback",
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
    _persistent = _persistent_engine_state()
    _safe_mode = _persistent is False
    if _safe_mode:
        logger.warning(
            "KeynoteManager | no persistent engine resolved for this "
            "command — opening in safe (modal) mode.  Check that "
            "bundle.yaml declares `engine: persistent: true` and reload "
            "pyRevit; a stale cached command assembly can also cause this.")

    _existing = envvars.get_pyrevit_env_var(KEYNOTEMGR_WINDOW_ENVVAR)
    _needs_new = True
    if _existing:
        try:
            if _existing.IsLoaded:
                # Restore before activating: Activate()
                # (SetForegroundWindow) does not un-minimize, and setting
                # WindowState afterwards restores without re-activating.
                _existing.WindowState = framework.Windows.WindowState.Normal
                _existing.Activate()
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
            # [Safe Mode] is applied by _update_title, which rebuilds the
            # whole title on every project switch
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
