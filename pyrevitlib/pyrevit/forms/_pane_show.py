"""Show a registered dockable pane once Revit has created its window.

Revit creates a pane's window some time after registration, so a show request
for a pane that does not exist yet waits for it on ``Idling``. Pending shows
are shared by every engine in the Revit process.

Note:
    This module must stay importable by IronPython 2.7.
"""

import time

from pyrevit import HOST_APP, UI, framework
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)

_PENDING_SHOWS_SLOT = "pyRevit.forms.pendingDockablePaneShowTokens"
_PENDING_SHOW_TIMEOUT_SECONDS = 60
_PENDING_SHOW_STALE_SECONDS = 10


def _pending_panel_shows():
    """Return the pending shows shared by every engine in this Revit process.

    Values are ``"<token>|<heartbeat>"`` strings, never engine objects, so
    each engine can see and cancel a show another engine deferred.
    ``coreutils.envvars`` does not fit: it stores an engine-specific Python
    dictionary.

    Invariant:
        The ``Idling`` handler owning an entry refreshes its heartbeat on every
        call and removes the entry when it stops, including when it raises.
        An entry outlives its handler only if the handler stopped running, so
        an entry without a recent heartbeat is safe to replace.
    """
    system = framework.System
    domain = system.AppDomain.CurrentDomain
    pending = domain.GetData(_PENDING_SHOWS_SLOT)
    if pending is None:
        pending = system.Collections.Generic.Dictionary[system.String, system.Object]()
        domain.SetData(_PENDING_SHOWS_SLOT, pending)
    return pending


def _cancel_dockable_panel_show(pane_id):
    _pending_panel_shows().Remove(pane_id.Guid.ToString())


def _pending_entry(token, now):
    return "{}|{!r}".format(token, now)


def _pending_entry_token(entry):
    return str(entry).split("|", 1)[0]


def _pending_entry_is_stale(entry, now):
    parts = str(entry).split("|", 1)
    try:
        heartbeat = float(parts[1])
    except (IndexError, ValueError):
        return True
    return not 0 <= now - heartbeat <= _PENDING_SHOW_STALE_SECONDS


def _claim_pending_show(pending, panel_key, now):
    """Record a new pending show unless a live one exists for the panel.

    Returns:
        (str | None): the new token, or None when a live show is pending.
    """
    if pending.ContainsKey(panel_key) and not _pending_entry_is_stale(
        pending[panel_key], now
    ):
        return None
    token = framework.System.Guid.NewGuid().ToString()
    pending[panel_key] = _pending_entry(token, now)
    return token


def _defer_dockable_panel_show(pane_id):
    pending = _pending_panel_shows()
    panel_key = pane_id.Guid.ToString()
    token = _claim_pending_show(pending, panel_key, time.time())
    if token is None:
        return
    uiapp = HOST_APP.uiapp
    waited = [0.0]
    last_tick = [time.time()]

    def is_current():
        return (
            pending.ContainsKey(panel_key)
            and _pending_entry_token(pending[panel_key]) == token
        )

    def stop():
        uiapp.Idling -= show_when_created
        if is_current():
            pending.Remove(panel_key)

    def wait_for_pane():
        if not is_current():
            uiapp.Idling -= show_when_created
            return
        now = time.time()
        pending[panel_key] = _pending_entry(token, now)
        if UI.DockablePane.PaneExists(pane_id):
            stop()
            _show_deferred_pane(uiapp, pane_id)
            return
        if getattr(uiapp, "ActiveUIDocument", None) is not None:
            waited[0] += now - last_tick[0]
        last_tick[0] = now
        if waited[0] >= _PENDING_SHOW_TIMEOUT_SECONDS:
            stop()
            mlogger.warning(
                "Dockable panel %s was not created within %s seconds of a "
                "document being open; not shown.",
                panel_key,
                _PENDING_SHOW_TIMEOUT_SECONDS,
            )

    def show_when_created(sender, args):
        try:
            wait_for_pane()
        except Exception:
            stop()
            raise

    uiapp.Idling += show_when_created


def _show_deferred_pane(uiapp, pane_id):
    try:
        uiapp.GetDockablePane(pane_id).Show()
    except Exception as error:
        mlogger.error("Could not show dockable panel %s: %s", pane_id.Guid, error)
