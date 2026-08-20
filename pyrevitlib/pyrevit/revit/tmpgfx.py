# -*- coding: utf-8 -*-
"""TemporaryGraphics wrapper and utilities.

Usage::

    from pyrevit.revit.tmpgfx import ControlManager, Handler

    class MyHandler(Handler):
        def on_click(self, index, payload):
            # payload is whatever you passed to add_control()
            TaskDialog.Show("Clicked", str(payload))

    mgr = ControlManager(doc, handler=MyHandler())
    mgr.add_control(icon_path, position, view, payload=my_elem)
    # ... later ...
    mgr.clear(view)
    mgr.unregister()
"""

import traceback

from pyrevit import DB, UI, HOST_APP, PyRevitException
from pyrevit.api import ExternalService as es
from pyrevit.framework import Guid
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


# Internal helpers

# TemporaryGraphicsHandlerService is a Revit 2022+ API member; older hosts
# don't have it, so importing this module must not fail before any of its
# classes are actually used.
_BUILTIN_SERVICE = (
    es.ExternalServices.BuiltInExternalServices.TemporaryGraphicsHandlerService
    if HOST_APP.is_newer_than(2021)
    else None
)


def _get_service():
    """Return the TemporaryGraphicsHandlerService instance."""
    if _BUILTIN_SERVICE is None:
        raise PyRevitException(
            "In-canvas controls (pyrevit.revit.tmpgfx) require Revit 2022 or newer."
        )
    return es.ExternalServiceRegistry.GetService(_BUILTIN_SERVICE)


# Handler


class Handler(UI.ITemporaryGraphicsHandler):
    """Base ITemporaryGraphicsHandler implementation.

    Subclass and override :meth:`on_click` to react to control clicks.
    The handler is automatically registered with the external service on
    construction unless *register* is ``False``.

    Args:
        guid (System.Guid, optional):
            Stable GUID for this handler.  A fresh random GUID is generated
            when ``None`` is passed.  Use a fixed GUID if you need the same
            handler identity across pyRevit reloads.  Defaults to ``None``.
        name (str, optional):
            Human-readable handler name visible in the Revit service registry.
            Defaults to ``"pyRevit TemporaryGraphics Handler"``.
        description (str, optional):
            Short description shown in the service registry.
            Defaults to ``"Handles in-canvas control click events"``.
        vendor_id (str, optional):
            Vendor identifier string.  Defaults to ``"pyRevit"``.
        register (bool, optional):
            Register the handler on construction.  Defaults to ``True``.
    """

    def __init__(
        self,
        guid=None,
        name="pyRevit TemporaryGraphics Handler",
        description="Handles in-canvas control click events",
        vendor_id="pyRevit",
        register=True,
    ):
        try:
            self.guid = Guid.NewGuid() if guid is None else guid
            self.name = name
            self.description = description
            self.vendor_id = vendor_id
            # index -> arbitrary payload
            self._control_map = {}

            if register:
                self.register()
        except Exception:
            print(traceback.format_exc())

    # ITemporaryGraphicsHandler interface

    def GetName(self):
        return self.name

    def GetDescription(self):
        return self.description

    def GetVendorId(self):
        return self.vendor_id

    def GetServerId(self):
        return self.guid

    def GetServiceId(self):
        return _BUILTIN_SERVICE

    def OnClick(self, command_data):
        """Dispatch a click event to :meth:`on_click`.

        Args:
            command_data (InCanvasControlClickCommandData):
                Revit-supplied click data; ``command_data.Index`` identifies
                the control that was clicked.
        """
        try:
            idx = command_data.Index
            payload = self._control_map.get(idx)
            self.on_click(idx, payload)
        except Exception:
            print(traceback.format_exc())

    # Public override point

    def on_click(self, index, payload):
        """Called when an in-canvas control is clicked.

        Override in a subclass to implement custom click behaviour.

        Args:
            index (int): The control index as assigned by the manager.
            payload: The arbitrary object that was associated with the
                control via :meth:`ControlManager.add_control`.
        """
        pass

    # Registration helpers

    def register(self):
        """Register this handler with the TemporaryGraphicsHandlerService.

        Safe to call multiple times; a previously registered instance with
        the same GUID is removed first.
        """
        try:
            svc = _get_service()
            registered = list(svc.GetRegisteredServerIds())
            if self.guid in registered:
                self.unregister()
            svc.AddServer(self)
            active = svc.GetActiveServerIds()
            active.Add(self.guid)
            svc.SetActiveServers(active)
        except Exception:
            print(traceback.format_exc())

    def unregister(self):
        """Remove this handler from the TemporaryGraphicsHandlerService."""
        try:
            svc = _get_service()
            registered = list(svc.GetRegisteredServerIds())
            if self.guid in registered:
                svc.RemoveServer(self.guid)
        except Exception:
            print(traceback.format_exc())

    # Internal map access (used by ControlManager)

    def _register_control(self, index, payload):
        """Store a payload keyed by control index."""
        self._control_map[index] = payload

    def _unregister_control(self, index):
        """Remove a control payload by index."""
        self._control_map.pop(index, None)

    def _clear_controls(self, indices):
        """Remove all payloads for a given list of indices."""
        for idx in indices:
            self._control_map.pop(idx, None)


# ControlManager


class ControlManager(object):
    """Manages in-canvas controls for one Revit document.

    Wraps :class:`DB.TemporaryGraphicsManager` and keeps controls organised
    per view so they can be cleared selectively.

    Args:
        doc (DB.Document): The active Revit document.
        handler (Handler, optional):
            A :class:`Handler` instance to dispatch click events.  When
            ``None``, a default no-op :class:`Handler` is created and
            registered automatically.  Defaults to ``None``.
    """

    _UNTRACKED_KEY = None  # sentinel bucket for indices recovered via sync()

    def __init__(self, doc, handler=None):
        try:
            self._doc = doc
            self._mgr = DB.TemporaryGraphicsManager.GetTemporaryGraphicsManager(doc)
            # view_id (int) -> list of control indices
            self._view_controls = {}

            if handler is None:
                self._handler = Handler()
            else:
                self._handler = handler
        except Exception:
            print(traceback.format_exc())

    # Public API

    @property
    def handler(self):
        """The :class:`Handler` instance owned by this manager."""
        return self._handler

    def add_control(self, icon_path, position, view, payload=None):
        """Place an in-canvas control icon at *position* in *view*.

        Args:
            icon_path (str):
                Absolute path to a BMP icon file (24-bit, recommended
                32 x 32 or 64 x 64 px for consistent display). To achieve
                a "transparent" background color effect over the provided
                bitmap, the bitmap should use color RGB(0, 128, 128) as its
                background and it will be cleared during rendering by Revit.
            position (DB.XYZ):
                World-space position for the control anchor point.
            view (DB.View):
                The view in which the control should appear.
            payload (object, optional):
                Arbitrary Python object forwarded to
                :meth:`Handler.on_click` when the control is clicked.
                Defaults to ``None``.

        Returns:
            int: The control index assigned by Revit, or ``-1`` on failure.
        """
        try:
            data = DB.InCanvasControlData(icon_path, position)
            index = self._mgr.AddControl(data, view.Id)
            if index < 0:
                return index
            view_id = get_elementid_value(view.Id)
            if view_id not in self._view_controls:
                self._view_controls[view_id] = []
            self._view_controls[view_id].append(index)
            self._handler._register_control(index, payload)
            return index
        except Exception:
            print(traceback.format_exc())
            return -1

    def remove_control(self, index, view):
        """Remove a single in-canvas control by *index*.

        Args:
            index (int): The control index returned by :meth:`add_control`.
            view (DB.View): The view the control belongs to.
        """
        try:
            self._mgr.RemoveControl(index)
            view_id = get_elementid_value(view.Id)
            if view_id in self._view_controls:
                try:
                    self._view_controls[view_id].remove(index)
                except ValueError:
                    pass
            self._handler._unregister_control(index)
        except Exception:
            print(traceback.format_exc())

    def clear(self, view):
        """Remove all in-canvas controls that belong to *view*.

        Args:
            view (DB.View): The view whose controls should be cleared.
        """
        try:
            view_id = get_elementid_value(view.Id)
            indices = list(self._view_controls.get(view_id, []))
            for idx in indices:
                self._mgr.RemoveControl(idx)
            self._handler._clear_controls(indices)
            self._view_controls[view_id] = []
        except Exception:
            print(traceback.format_exc())

    def clear_all(self):
        """Remove every in-canvas control across all views."""
        try:
            for _, indices in list(self._view_controls.items()):
                for idx in indices:
                    try:
                        self._mgr.RemoveControl(idx)
                    except Exception:
                        pass
                self._handler._clear_controls(indices)
            self._view_controls = {}
        except Exception:
            print(traceback.format_exc())

    def refresh(self):
        """Request a view refresh to make newly added controls visible."""
        try:
            from pyrevit import revit

            revit.uidoc.RefreshActiveView()
        except Exception:
            print(traceback.format_exc())

    def unregister(self):
        """Unregister the handler and remove all controls.

        Call this during script cleanup to avoid stale handlers persisting
        across pyRevit reloads.
        """
        self.clear_all()
        self._handler.unregister()

    def control_count(self, view=None):
        """Return the number of active controls, optionally scoped to *view*.

        Args:
            view (DB.View, optional):
                When provided, count only controls in that view.
                When ``None``, return the total count across all views.

        Returns:
            int: Number of active controls.
        """
        if view is not None:
            view_id = get_elementid_value(view.Id)
            return len(self._view_controls.get(view_id, []))
        return sum(len(v) for v in self._view_controls.values())

    def get_all_indices(self):
        """Return every control index currently live in the Revit manager.

        Delegates directly to :meth:`DB.TemporaryGraphicsManager.GetAll` so
        the result reflects the actual Revit state, not the internal dict.

        Returns:
            list[int]: Live control indices, or an empty list on failure.
        """
        try:
            return list(self._mgr.GetAll())
        except Exception:
            print(traceback.format_exc())
            return []

    def sync(self):
        """Reconcile the internal dict against the live Revit state.

        Any index returned by :meth:`DB.TemporaryGraphicsManager.GetAll` that
        is not already tracked is added to the ``None`` sentinel bucket.  This
        lets you recover control over indices that were registered by a
        previous script run (e.g. after a pyRevit reload) without knowing
        which view they belong to.

        Indices that are tracked internally but absent from Revit are pruned
        so the dict does not grow stale.

        Returns:
            tuple[list[int], list[int]]:
                ``(recovered, pruned)`` — indices newly added to the sentinel
                bucket, and indices removed because Revit no longer knows them.
        """
        try:
            live = set(self.get_all_indices())

            # collect every index we already track
            tracked = {}  # index -> view_key
            for view_key, indices in list(self._view_controls.items()):
                for idx in indices:
                    tracked[idx] = view_key

            recovered = []
            for idx in live:
                if idx not in tracked:
                    bucket = self._view_controls.setdefault(self._UNTRACKED_KEY, [])
                    bucket.append(idx)
                    recovered.append(idx)

            pruned = []
            for idx, view_key in list(tracked.items()):
                if idx not in live:
                    bucket = self._view_controls.get(view_key, [])
                    try:
                        bucket.remove(idx)
                    except ValueError:
                        pass
                    self._handler._unregister_control(idx)
                    pruned.append(idx)

            return recovered, pruned
        except Exception:
            print(traceback.format_exc())
            return [], []

    def remove_all_untracked(self):
        """Remove every control Revit knows about that is not in the dict.

        Useful after a script reload when you want a guaranteed clean slate
        without caring about preserving any existing controls.

        Returns:
            list[int]: Indices that were removed.
        """
        try:
            live = set(self.get_all_indices())
            tracked = set(
                idx for indices in self._view_controls.values() for idx in indices
            )
            untracked = live - tracked
            removed = []
            for idx in untracked:
                try:
                    self._mgr.RemoveControl(idx)
                    removed.append(idx)
                except Exception:
                    print(traceback.format_exc())
            return removed
        except Exception:
            print(traceback.format_exc())
            return []

    def set_visibility(self, index, visible):
        """Show or hide a single in-canvas control.

        Args:
            index (int): The control index to update.
            visible (bool): ``True`` to show, ``False`` to hide.
        """
        try:
            self._mgr.SetVisibility(index, visible)
        except Exception:
            print(traceback.format_exc())

    def set_visibility_all(self, visible, view=None):
        """Show or hide controls, optionally scoped to *view*.

        Args:
            visible (bool): ``True`` to show, ``False`` to hide.
            view (DB.View, optional):
                When provided, only controls tracked under that view are
                affected.  When ``None``, all tracked controls are affected.
        """
        try:
            if view is not None:
                view_id = get_elementid_value(view.Id)
                indices = list(self._view_controls.get(view_id, []))
            else:
                indices = [
                    idx for bucket in self._view_controls.values() for idx in bucket
                ]
            for idx in indices:
                try:
                    self._mgr.SetVisibility(idx, visible)
                except Exception:
                    print(traceback.format_exc())
        except Exception:
            print(traceback.format_exc())

    def update_control(self, index, icon_path, position):
        """Update the icon or position of an existing in-canvas control.

        Args:
            index (int): The control index to update.
            icon_path (str): Absolute path to the replacement BMP icon file.
            position (DB.XYZ): New world-space anchor position.
        """
        try:
            data = DB.InCanvasControlData(icon_path, position)
            self._mgr.UpdateControl(index, data)
        except Exception:
            print(traceback.format_exc())
