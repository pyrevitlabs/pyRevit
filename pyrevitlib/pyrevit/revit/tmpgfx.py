# -*- coding: utf-8 -*-
"""TemporaryGraphics wrapper and utilities.

Usage in a bundle script::

    from pyrevit import revit, UI
    from pyrevit.revit import tmpgfx

    class MyHandler(tmpgfx.Handler):
        def __init__(self, guid):
            tmpgfx.Handler.__init__(self, guid=guid, name="My tool")

        def on_click(self, index, payload):
            element = self.clicked_document.GetElement(payload)
            UI.TaskDialog.Show("Clicked", str(element))

    manager = tmpgfx.get_manager("MyTool", revit.doc, MyHandler)
    manager.add_control(icon_path, position, view, payload=element.Id)

    tmpgfx.dispose("MyTool")

:func:`get_manager` and :func:`dispose` keep one handler per tool however
often the script runs. Creating a :class:`Handler` and a
:class:`ControlManager` directly leaves that to the caller, who then has to
keep both objects to remove the controls later.

Notes:
    - Clicks arrive after the creating script has ended, so a bundle that
      places controls needs a persistent engine (``engine: persistent:
      true`` in ``bundle.yaml``).
    - Revit calls every registered handler for a click, whoever added the
      control. :class:`Handler` filters out controls it does not own.
    - Revit kept showing an already loaded image after the file at that
      path changed; restart Revit or use a new file name.
    - Icons must be BMP files. Transparency comes from the background color
      RGB(0, 128, 128) only. Save them as 24-bit: an alpha channel is not
      honored the way image editors write it.
    - In testing on Revit 2026, controls were drawn in 3D and floor plan
      views but not in structural plan views.
    - Prefer an ``ElementId`` over an element as payload. It stays usable
      after the element is deleted or the change that created it is undone.
"""

from pyrevit import DB, UI
from pyrevit import PyRevitException
from pyrevit.api import ExternalService as es
from pyrevit.framework import Guid
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import envvars, get_str_hash
from pyrevit.coreutils.logger import get_logger

get_elementid_value = get_elementid_value_func()

mlogger = get_logger(__name__)

_TOOL_ENVVAR_PREFIX = "PYREVIT_TMPGFX_TOOL_"


# Internal helpers

_BUILTIN_SERVICE = (
    es.ExternalServices.BuiltInExternalServices.TemporaryGraphicsHandlerService
)


def _get_service():
    """Return the TemporaryGraphicsHandlerService instance."""
    return es.ExternalServiceRegistry.GetService(_BUILTIN_SERVICE)


# Handler


class Handler(UI.ITemporaryGraphicsHandler):  # compat-ignore: imported only on 2022+
    """Base ITemporaryGraphicsHandler implementation.

    Subclass and override :meth:`on_click` to react to control clicks.
    Only clicks on controls added through a :class:`ControlManager` that
    uses this handler are dispatched. Controls of other handlers, other
    add-ins, or added with the raw API are ignored. While :meth:`on_click`
    runs, ``clicked_document`` is the document of the clicked control.
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
        self.guid = Guid.NewGuid() if guid is None else guid
        self.name = name
        self.description = description
        self.vendor_id = vendor_id
        self.clicked_document = None
        # (document hash, index) -> arbitrary payload
        self._control_map = {}

        if register:
            self.register()

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
        """Dispatch a click on an owned control to :meth:`on_click`.

        Args:
            command_data (UI.TemporaryGraphicsCommandData):
                Revit-supplied click data. ``Document`` and ``Index``
                together identify the clicked control, because indices are
                numbered per document.
        """
        try:
            idx = command_data.Index
            key = self._control_key(command_data.Document, idx)
            if key not in self._control_map:
                return
            self.clicked_document = command_data.Document
            self.on_click(idx, self._control_map[key])
        except Exception:
            mlogger.exception("Temporary graphics click handler failed")

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
        self.unregister()
        svc = _get_service()
        svc.AddServer(self)
        active = svc.GetActiveServerIds()
        active.Add(self.guid)
        svc.SetActiveServers(active)

    def unregister(self):
        """Remove this handler from the TemporaryGraphicsHandlerService."""
        svc = _get_service()
        if self.guid in list(svc.GetRegisteredServerIds()):
            svc.RemoveServer(self.guid)

    # Internal map access (used by ControlManager)

    @staticmethod
    def _control_key(doc, index):
        return (doc.GetHashCode(), index)

    def _register_control(self, doc, index, payload):
        """Store a payload for a control of *doc*."""
        self._control_map[self._control_key(doc, index)] = payload

    def _unregister_control(self, doc, index):
        """Remove a control payload of *doc* by index."""
        self._control_map.pop(self._control_key(doc, index), None)

    def _forget_document(self, doc_key):
        """Drop the payloads of a document identified by its hash code."""
        for key in [key for key in self._control_map if key[0] == doc_key]:
            del self._control_map[key]

    def _clear_controls(self, doc, indices):
        """Remove the payloads of *doc* for a list of indices."""
        for idx in indices:
            self._unregister_control(doc, idx)


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
        self._doc = doc
        self._mgr = DB.TemporaryGraphicsManager.GetTemporaryGraphicsManager(
            doc
        )  # compat-ignore: imported only on 2022+
        # view_id (int) -> list of control indices
        self._view_controls = {}
        self._handler = Handler() if handler is None else handler

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
                Do not rely on an alpha channel.
            position (DB.XYZ):
                World-space position for the control anchor point.
            view (DB.View):
                The view in which the control should appear.
            payload (object, optional):
                Arbitrary Python object forwarded to
                :meth:`Handler.on_click` when the control is clicked.
                Defaults to ``None``.

        Returns:
            int: The control index assigned by Revit.

        Raises:
            PyRevitException: Revit did not create the control. Errors of
                the Revit API itself, such as a missing or non-BMP icon,
                propagate unchanged.
        """
        data = DB.InCanvasControlData(
            icon_path, position
        )  # compat-ignore: imported only on 2022+
        index = self._mgr.AddControl(
            data, view.Id
        )  # compat-ignore: imported only on 2022+
        if index < 0:
            raise PyRevitException("Revit did not create the in-canvas control")
        view_id = get_elementid_value(view.Id)
        self._view_controls.setdefault(view_id, []).append(index)
        self._handler._register_control(self._doc, index, payload)
        return index

    def remove_control(self, index, view):
        """Remove a single in-canvas control by *index*.

        Args:
            index (int): The control index returned by :meth:`add_control`.
            view (DB.View): The view the control belongs to.
        """
        try:
            self._mgr.RemoveControl(index)  # compat-ignore: imported only on 2022+
        finally:
            view_id = get_elementid_value(view.Id)
            if index in self._view_controls.get(view_id, []):
                self._view_controls[view_id].remove(index)
            self._handler._unregister_control(self._doc, index)

    def _remove_indices(self, indices):
        removed = 0
        for idx in indices:
            try:
                self._mgr.RemoveControl(idx)
                removed += 1
            except Exception as ex:
                mlogger.debug("Control {} is already gone: {}".format(idx, ex))
        self._handler._clear_controls(self._doc, indices)
        return removed

    def clear(self, view):
        """Remove all in-canvas controls that belong to *view*.

        Args:
            view (DB.View): The view whose controls should be cleared.

        Returns:
            int: Number of controls removed.
        """
        view_id = get_elementid_value(view.Id)
        return self._remove_indices(self._view_controls.pop(view_id, []))

    def clear_all(self):
        """Remove every in-canvas control across all views.

        Returns:
            int: Number of controls removed.
        """
        indices = [idx for bucket in self._view_controls.values() for idx in bucket]
        self._view_controls = {}
        return self._remove_indices(indices)

    def refresh(self):
        """Request a view refresh to make newly added controls visible."""
        from pyrevit import revit

        revit.uidoc.RefreshActiveView()

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
            list[int]: Live control indices.
        """
        return list(self._mgr.GetAll())

    def sync(self):
        """Reconcile the internal dict against the live Revit state.

        Any index returned by :meth:`DB.TemporaryGraphicsManager.GetAll` that
        is not already tracked is added to the ``None`` sentinel bucket.  This
        lets you recover control over indices that were registered by a
        previous script run (e.g. after a pyRevit reload) without knowing
        which view they belong to.

        Warning:
            The Revit manager is shared by every tool working on the
            document. This adopts their controls too, so a following
            :meth:`clear_all` or :meth:`unregister` removes them. To clean
            up only your own controls, keep your manager instead.

        Indices that are tracked internally but absent from Revit are pruned
        so the dict does not grow stale.

        Returns:
            tuple[list[int], list[int]]:
                ``(recovered, pruned)`` — indices newly added to the sentinel
                bucket, and indices removed because Revit no longer knows them.
        """
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
                if idx in bucket:
                    bucket.remove(idx)
                self._handler._unregister_control(self._doc, idx)
                pruned.append(idx)

        return recovered, pruned

    def remove_all_untracked(self):
        """Remove every control Revit knows about that is not in the dict.

        Useful after a script reload when you want a guaranteed clean slate
        without caring about preserving any existing controls.

        Warning:
            This includes controls created by other tools and add-ins.

        Returns:
            list[int]: Indices that were removed.
        """
        live = set(self.get_all_indices())
        tracked = set(idx for bucket in self._view_controls.values() for idx in bucket)
        removed = []
        for idx in live - tracked:
            try:
                self._mgr.RemoveControl(idx)
                removed.append(idx)
            except Exception as ex:
                mlogger.debug("Control {} is already gone: {}".format(idx, ex))
        return removed

    def set_visibility(self, index, visible):
        """Show or hide a single in-canvas control.

        Args:
            index (int): The control index to update.
            visible (bool): ``True`` to show, ``False`` to hide.
        """
        self._mgr.SetVisibility(index, visible)

    def set_visibility_all(self, visible, view=None):
        """Show or hide controls, optionally scoped to *view*.

        Args:
            visible (bool): ``True`` to show, ``False`` to hide.
            view (DB.View, optional):
                When provided, only controls tracked under that view are
                affected.  When ``None``, all tracked controls are affected.
        """
        if view is not None:
            view_id = get_elementid_value(view.Id)
            indices = list(self._view_controls.get(view_id, []))
        else:
            indices = [idx for bucket in self._view_controls.values() for idx in bucket]
        for idx in indices:
            self._mgr.SetVisibility(idx, visible)

    def update_control(self, index, icon_path, position):
        """Update the icon or position of an existing in-canvas control.

        Args:
            index (int): The control index to update.
            icon_path (str): Absolute path to the replacement BMP icon file.
            position (DB.XYZ): New world-space anchor position.
        """
        data = DB.InCanvasControlData(
            icon_path, position
        )  # compat-ignore: imported only on 2022+
        self._mgr.UpdateControl(index, data)  # compat-ignore: imported only on 2022+


# One handler per tool


def get_tool_guid(tool_name):
    """Return the stable handler id of the tool called *tool_name*."""
    return Guid(get_str_hash("pyrevit.tmpgfx.{}".format(tool_name)))


def get_manager(tool_name, doc, handler_factory=None):
    """Get a tool's manager for placing clickable icons in a view of *doc*.

    The tool keeps one handler across script runs and one manager per
    document, so running a script again neither adds handlers nor forgets
    controls placed earlier.

    Args:
        tool_name (str): Identifies the tool. Use something no other tool
            would pick.
        doc (DB.Document): Document to place controls in.
        handler_factory (callable, optional): Called with the tool's
            handler id and returns the handler, usually a :class:`Handler`
            subclass passing it on as ``guid``. When given, the new handler
            replaces the tool's previous one and takes over its controls,
            so the code of the latest run handles all clicks. None keeps
            the current handler, or creates a plain :class:`Handler`.

    Returns:
        ControlManager: The manager of this tool and document. Its
            :meth:`ControlManager.add_control` places an in-canvas icon.

    Raises:
        PyRevitException: The factory's handler does not use the given id.

    Note:
        The tool lives in the engine that created it, so the bundle needs a
        persistent engine.
    """
    envvar = _TOOL_ENVVAR_PREFIX + tool_name
    state = envvars.get_pyrevit_env_var(envvar)
    if not state or handler_factory is not None:
        guid = get_tool_guid(tool_name)
        handler = (handler_factory or Handler)(guid)
        if handler.guid != guid:
            raise PyRevitException(
                "The handler of tool '{}' must use the id passed to its factory".format(
                    tool_name
                )
            )
        if state:
            handler._control_map.update(state["handler"]._control_map)
            for _, manager in state["managers"].values():
                manager._handler = handler
        else:
            state = {"managers": {}}
        state["handler"] = handler
        envvars.set_pyrevit_env_var(envvar, state)

    managers = state["managers"]
    for key, (document, _) in list(managers.items()):
        if not document.IsValidObject:
            del managers[key]
            state["handler"]._forget_document(key)
    key = doc.GetHashCode()
    if key not in managers:
        managers[key] = (doc, ControlManager(doc, handler=state["handler"]))
    return managers[key][1]


def dispose(tool_name):
    """Remove the controls and the handler of a :func:`get_manager` tool.

    Controls of other tools and add-ins stay.

    Args:
        tool_name (str): The name passed to :func:`get_manager`.

    Returns:
        int: Number of controls removed, 0 if the tool is not known.
    """
    envvar = _TOOL_ENVVAR_PREFIX + tool_name
    state = envvars.get_pyrevit_env_var(envvar)
    if not state:
        return 0
    removed = 0
    for document, manager in state["managers"].values():
        if document.IsValidObject:
            removed += manager.clear_all()
    state["handler"].unregister()
    envvars.set_pyrevit_env_var(envvar, False)
    return removed
