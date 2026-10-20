# -*- coding: utf-8 -*-
"""Elements selection utilities."""

from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import framework, DB, UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.revit import ensure
from pyrevit.revit import query
from Autodesk.Revit import Exceptions as RevitExceptions


__all__ = (
    "pick_element",
    "pick_element_by_category",
    "pick_elements",
    "pick_elements_by_category",
    "get_picked_elements",
    "get_picked_elements_by_category",
    "pick_edge",
    "pick_edges",
    "pick_face",
    "pick_faces",
    "pick_linked",
    "pick_linkeds",
    "pick_elementpoint",
    "pick_elementpoints",
    "pick_point",
    "pick_rectangle",
    "get_selection_category_set",
    "get_selection",
)


# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


class ElementSelection:
    """Element selection handler.

    Host elements are tracked as ``ElementId``s of the active document.
    Elements inside linked models are tracked separately as host-context link
    references (see `link_references` and `linked_elements`), because their ids
    belong to the link document and must never be resolved against the host.

    Note:
        Iteration, indexing, `elements`, `element_ids`, `first`, `last`,
        `include`, `exclude` and `expand_groups` only cover host elements.
        `__len__` and `is_empty` cover both host and linked entries.
        When created without arguments, only the host part of the current
        Revit selection is read.

    Args:
        element_list (list[DB.Element]): list of selected elements
    """

    def __init__(self, element_list=None):
        self._link_refs = []
        if element_list is None:
            if HOST_APP.uidoc:
                self._refs = [x for x in HOST_APP.uidoc.Selection.GetElementIds()]
            else:
                self._refs = []
        else:
            self._refs = ElementSelection.get_element_ids(element_list)

    def __len__(self):
        return len(self._refs) + len(self._link_refs)

    def __iter__(self):
        for elref in self._refs:
            yield DOCS.doc.GetElement(elref)

    def __getitem__(self, index):
        return self.elements[index]

    def __contains__(self, item):
        if isinstance(item, DB.Element):
            elref = item.Id
        elif isinstance(item, DB.ElementId):
            elref = item
        else:
            elref = DB.ElementId.InvalidElementId
        return elref in self._refs

    @classmethod
    def get_element_ids(cls, mixed_list):
        return ensure.ensure_element_ids(mixed_list)

    @staticmethod
    def _supports_link_selection():
        return HOST_APP.is_newer_than(2022)

    @staticmethod
    def _find_link_instance(link_doc):
        for link_instance in DB.FilteredElementCollector(DOCS.doc).OfClass(
            DB.RevitLinkInstance
        ):
            instance_doc = link_instance.GetLinkDocument()
            if instance_doc is not None and instance_doc.Equals(link_doc):
                return link_instance
        return None

    @staticmethod
    def _link_reference_from_element(element):
        link_instance = ElementSelection._find_link_instance(element.Document)
        if link_instance is None:
            return None
        return DB.Reference(element).CreateLinkReference(link_instance)

    @staticmethod
    def _link_reference_from_reference(reference):
        link_instance = DOCS.doc.GetElement(reference.ElementId)
        if not isinstance(link_instance, DB.RevitLinkInstance):
            return None
        link_doc = link_instance.GetLinkDocument()
        if link_doc is None:
            return None
        linked_element = link_doc.GetElement(reference.LinkedElementId)
        if linked_element is None:
            return None
        return DB.Reference(linked_element).CreateLinkReference(link_instance)

    @staticmethod
    def _split_host_and_linked(element_list):
        if element_list is None:
            return [], []
        if not hasattr(element_list, "__iter__"):
            element_list = [element_list]

        host_items = []
        link_refs = []
        for item in element_list:
            if item is None:
                continue
            if isinstance(item, DB.Reference):
                if item.LinkedElementId == DB.ElementId.InvalidElementId:
                    host_items.append(item.ElementId)
                    continue
                link_ref = ElementSelection._link_reference_from_reference(item)
            elif isinstance(item, DB.Element) and item.Document.IsLinked:
                link_ref = ElementSelection._link_reference_from_element(item)
            else:
                host_items.append(item)
                continue

            if link_ref is None:
                mlogger.debug("No loaded link instance found for: %s", item)
                continue
            link_refs.append(link_ref)
        return host_items, link_refs

    @property
    def is_empty(self):
        return len(self) == 0

    @property
    def elements(self):
        return [DOCS.doc.GetElement(x) for x in self._refs]

    @property
    def element_ids(self):
        return self._refs

    @property
    def link_references(self):
        """list[DB.Reference]: host-context references to the linked elements.

        Each reference points at the link instance (``ElementId``) and at the
        element inside the link document (``LinkedElementId``).
        """
        return self._link_refs

    @property
    def linked_elements(self):
        """list[DB.Element]: selected elements that live in linked documents.

        Entries whose link instance was deleted or whose link was unloaded
        since selection, or whose element no longer exists, are skipped.
        """
        linked_elements = []
        for link_ref in self._link_refs:
            link_instance = DOCS.doc.GetElement(link_ref.ElementId)
            if not isinstance(link_instance, DB.RevitLinkInstance):
                continue
            link_doc = link_instance.GetLinkDocument()
            if link_doc is None:
                continue
            linked_element = link_doc.GetElement(link_ref.LinkedElementId)
            if linked_element is not None:
                linked_elements.append(linked_element)
        return linked_elements

    @property
    def first(self):
        if self._refs:
            return DOCS.doc.GetElement(self._refs[0])

    @property
    def last(self):
        if self._refs:
            return DOCS.doc.GetElement(self._refs[-1])

    def set_to(self, element_list):
        """Replace the Revit selection with the given items.

        Accepts host elements, element ids, elements from linked documents
        (e.g. from `pick_linkeds`) and ``DB.Reference`` objects, in any mix.
        Linked elements end up individually selected, as if Tab-selected into
        the link. ``None`` entries and a ``None`` list are ignored.

        Note:
            A bare linked element carries no link instance, so the first loaded
            instance of its link document is used. Pass the picked
            ``DB.Reference`` objects instead to target a specific instance when
            the same file is linked more than once.

        Args:
            element_list (list | object | None): items to select.

        Raises:
            PyRevitException: If linked elements are given on Revit 2022 or
                older, which cannot select elements inside links. The
                selection is left unchanged in that case.
        """
        host_items, link_refs = ElementSelection._split_host_and_linked(element_list)
        if link_refs and not ElementSelection._supports_link_selection():
            raise PyRevitException(
                "Selecting elements inside links requires Revit 2023 or newer."
            )

        self._refs = ElementSelection.get_element_ids(host_items)
        self._link_refs = link_refs

        if link_refs:
            host_elements = [DOCS.doc.GetElement(x) for x in self._refs]
            all_refs = [DB.Reference(x) for x in host_elements if x is not None]
            all_refs.extend(link_refs)
            HOST_APP.uidoc.Selection.SetReferences(
                framework.to_clr_list(DB.Reference, all_refs)
            )
        else:
            HOST_APP.uidoc.Selection.SetElementIds(
                framework.to_clr_list(DB.ElementId, self._refs)
            )
        HOST_APP.uidoc.RefreshActiveView()

    def clear(self):
        self._refs = []
        self._link_refs = []
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.to_clr_list(DB.ElementId, [DB.ElementId.InvalidElementId])
        )
        HOST_APP.uidoc.RefreshActiveView()

    def append(self, element_list):
        if element_list is None:
            element_list = []
        elif not hasattr(element_list, "__iter__"):
            element_list = [element_list]
        self.set_to(list(self._refs) + list(self._link_refs) + list(element_list))

    def include(self, element_type):
        refs = [
            x for x in self._refs if isinstance(DOCS.doc.GetElement(x), element_type)
        ]
        return ElementSelection(refs)

    def exclude(self, element_type):
        refs = [
            x
            for x in self._refs
            if not isinstance(DOCS.doc.GetElement(x), element_type)
        ]
        return ElementSelection(refs)

    def no_views(self):
        return self.exclude(DB.View)

    def only_views(self):
        return self.include(DB.View)

    def expand_groups(self):
        expanded_refs = []
        for element in self.elements:
            if isinstance(element, DB.Group):
                expanded_refs.extend(element.GetMemberIds())
            else:
                expanded_refs.append(element.Id)
        self._refs = expanded_refs


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, category_id):
        self.category_id = category_id

    # standard API override function
    def AllowElement(self, element):
        if element.Category and self.category_id == element.Category.Id:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):  # pylint: disable=W0613
        return False


def _pick_obj(obj_type, message, multiple=False, world=False, selection_filter=None):
    mlogger.debug(
        "Picking elements: %s message: %s multiple: %s world: %s",
        obj_type,
        message,
        multiple,
        world,
    )
    picker_func = (
        HOST_APP.uidoc.Selection.PickObjects
        if multiple
        else HOST_APP.uidoc.Selection.PickObject
    )
    try:
        pick_result = (
            picker_func(obj_type, selection_filter, message)
            if selection_filter
            else picker_func(obj_type, message)
        )
    except RevitExceptions.OperationCanceledException:
        mlogger.debug("Operation canceled by user")
        return None
    refs = list(pick_result) if multiple else [pick_result]
    if not refs:
        mlogger.debug("Nothing picked by user")
        return None

    mlogger.debug("Picked elements are: %s", refs)

    if obj_type == UI.Selection.ObjectType.Element:
        return_values = [DOCS.doc.GetElement(ref) for ref in refs]
    elif obj_type == UI.Selection.ObjectType.PointOnElement:
        if world:
            return_values = [ref.GlobalPoint for ref in refs]
        else:
            return_values = [ref.UVPoint for ref in refs]
    else:
        return_values = []
        for ref in refs:
            element = DOCS.doc.GetElement(ref)
            if obj_type == UI.Selection.ObjectType.LinkedElement and isinstance(
                element, DB.RevitLinkInstance
            ):
                link_doc = element.GetLinkDocument()
                if link_doc and ref.LinkedElementId != DB.ElementId.InvalidElementId:
                    return_values.append(link_doc.GetElement(ref.LinkedElementId))
                else:
                    mlogger.debug(
                        "Skipping unloaded link or invalid reference: %s", ref
                    )
                    return_values.append(None)
            else:
                return_values.append(element.GetGeometryObjectFromReference(ref))

    mlogger.debug("Processed return elements are: %s", return_values)

    if len(return_values) > 1 or multiple:
        return return_values
    if len(return_values) == 1:
        return return_values[0]
    mlogger.error("Error processing picked elements. return_values should be a list.")


def pick_element(message="", pick_filter=None):
    """Asks the user to pick an element.

    Args:
        message (str): An optional message to display.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (Element): element selected by the user.
    """
    return _pick_obj(
        UI.Selection.ObjectType.Element, message, selection_filter=pick_filter
    )


def pick_element_by_category(cat_name_or_builtin, message=""):
    """Returns the element of the specified category picked by the user.

    Args:
        cat_name_or_builtin (str): name or built-in category of the element
            to pick.
        message (str, optional): message to display on selection.
            Defaults to ''.

    Returns:
        (Element): picked element.

    Raises:
        PyRevitException: If no category matches the specified name or builtin.
    """
    category = query.get_category(cat_name_or_builtin)
    if category:
        pick_filter = PickByCategorySelectionFilter(category.Id)
        return _pick_obj(
            UI.Selection.ObjectType.Element, message, selection_filter=pick_filter
        )
    else:
        raise PyRevitException(
            "Can not determine category id from: {}".format(cat_name_or_builtin)
        )


def pick_elementpoint(message="", world=False):
    """Returns the element point selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.
        world (bool, optional): whether to use world coordinates. Defaults to False.

    Returns:
        (PointOnElement): The selected point.
    """
    return _pick_obj(UI.Selection.ObjectType.PointOnElement, message, world=world)


def pick_edge(message=""):
    """Returns the edge selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.

    Returns:
        (Edge): The selected edge.
    """
    return _pick_obj(UI.Selection.ObjectType.Edge, message)


def pick_face(message=""):
    """Returns the face selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.

    Returns:
        (Face): The selected face.
    """
    return _pick_obj(UI.Selection.ObjectType.Face, message)


def pick_linked(message="", pick_filter=None):
    """Returns the linked element selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (LinkedElement): The selected linked element.
    """
    return _pick_obj(
        UI.Selection.ObjectType.LinkedElement, message, selection_filter=pick_filter
    )


def pick_elements(message="", pick_filter=None):
    """Asks the user to pick multiple elements.

    Args:
        message (str): An optional message to display.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (list[Element]): elements selected by the user.
    """
    return _pick_obj(
        UI.Selection.ObjectType.Element,
        message,
        multiple=True,
        selection_filter=pick_filter,
    )


def pick_elements_by_category(cat_name_or_builtin, message=""):
    """Returns the elements of the specified category picked by the user.

    Args:
        cat_name_or_builtin (str): name or built-in category of the elements
            to pick.
        message (str, optional): message to display on selection.
            Defaults to ''.

    Returns:
        (list[Element]): picked elements.

    Raises:
        PyRevitException: If no category matches the specified name or builtin.
    """
    category = query.get_category(cat_name_or_builtin)
    if category:
        pick_filter = PickByCategorySelectionFilter(category.Id)
        return _pick_obj(
            UI.Selection.ObjectType.Element,
            message,
            multiple=True,
            selection_filter=pick_filter,
        )
    else:
        raise PyRevitException(
            "Can not determine category id from: {}".format(cat_name_or_builtin)
        )


def get_picked_elements(message=""):
    """Allows the user to pick multple elements, one at a time.

    It keeps asking the user to pick an element until no elements are selected.

    Args:
        message (str, optional): The message to display. Defaults to ''.

    Yields:
        (DB.Element): selected element
    """
    picked_element = True
    while picked_element:
        picked_element = pick_element(message=message)
        if not picked_element:
            break
        yield picked_element


def get_picked_elements_by_category(cat_name_or_builtin, message=""):
    """Pick elements by category.

    Keeps asking the user to pick an element until no elements are selected.

    Args:
        cat_name_or_builtin (str): category name or built-in category.
        message (str, optional): message to display while picking elements.

    Yields:
        (DB.Element): The picked elements from the specified category.
    """
    picked_element = True
    while picked_element:
        picked_element = pick_element_by_category(cat_name_or_builtin, message=message)
        if not picked_element:
            break
        yield picked_element


def pick_elementpoints(message="", world=False):
    """Selects element points.

    Args:
        message (str): The message to display when selecting element points.
        world (bool, optional): Select points in world coordinates. Defaults to False.

    Returns:
        (list[PointOnElement]): selected element points.
    """
    return _pick_obj(
        UI.Selection.ObjectType.PointOnElement, message, multiple=True, world=world
    )


def pick_edges(message=""):
    """Selects edges.

    Args:
        message (str): The message to display when selecting edges.

    Returns:
        (list[Edge]): selected edges.
    """
    return _pick_obj(UI.Selection.ObjectType.Edge, message, multiple=True)


def pick_faces(message=""):
    """Selects faces.

    Args:
        message (str): The message to display when selecting the faces.

    Returns:
        (list[Face]): selected faces.
    """
    return _pick_obj(UI.Selection.ObjectType.Face, message, multiple=True)


def pick_linkeds(message="", pick_filter=None):
    """Selects linked elements.

    Args:
        message (str, optional): The message to display when selecting
            linked elements. Default is an empty string.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (list[LinkedElement]): selected linked elements.
    """
    return _pick_obj(
        UI.Selection.ObjectType.LinkedElement,
        message,
        multiple=True,
        selection_filter=pick_filter,
    )


def pick_point(message=""):
    # type: (str) -> DB.XYZ | None
    """Pick a point from the user interface.

    Args:
        message (str): A message to display when prompting for the point.

    Returns:
        (tuple or None): A tuple representing the picked point as (x, y, z)
            coordinates, or None if no point was picked or an error occurred.

    Side Effects:
        If the active view does not have a ``SketchPlane`` assigned, this
        function will automatically create a temporary work plane (aligned with the
        active view) and assign it to the view before prompting for the point.
        The work plane is removed after picking to avoid modifying the document.
    """
    doc = HOST_APP.doc
    active_view = doc.ActiveView
    NO_SKETCHPLANE_VIEWTYPES = (
        DB.ViewType.DraftingView,
        DB.ViewType.Legend,
        DB.ViewType.DrawingSheet,
    )  # type: tuple[DB.ViewType]
    needs_plane = (
        active_view.SketchPlane is None
        and active_view.ViewType not in NO_SKETCHPLANE_VIEWTYPES
    )  # type: bool
    result = None

    try:
        if needs_plane:
            tg = DB.TransactionGroup(doc, "Assigning a workplane to the current view")
            tg.Start()

            with DB.Transaction(doc, "Create temporary workplane") as t:
                t.Start()
                try:
                    sketch_plane = DB.SketchPlane.Create(
                        doc,
                        DB.Plane.CreateByNormalAndOrigin(
                            active_view.ViewDirection, active_view.Origin
                        ),
                    )
                    active_view.SketchPlane = sketch_plane
                    t.Commit()
                except Exception as ex:
                    mlogger.error("Failed to create temporary sketch plane: %s", ex)
                    t.RollBack()
                    tg.RollBack()
                    return None

            result = HOST_APP.uidoc.Selection.PickPoint(message)

            tg.RollBack()
        else:
            result = HOST_APP.uidoc.Selection.PickPoint(message)

    except RevitExceptions.OperationCanceledException:
        mlogger.debug("Operation canceled by user")
        return None
    except Exception as ex:
        mlogger.error("An error occurred during point picking: %s", ex)
        return None

    return result


def pick_rectangle(message="", pick_filter=None):
    """Picks elements from the user interface by specifying a rectangular area.

    Args:
        message (str, optional): A custom message to display when prompting
            the user to pick elements. Default is an empty string.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (list[DB.ElementId]): The selected elements.
    """
    if pick_filter:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(pick_filter, message)
    else:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(message)


def get_selection_category_set():
    """Returns a CategorySet with the categories of the selected elements.

    Returns:
        (CategorySet): categories of the selected elements.
    """
    selection = ElementSelection()
    cset = DB.CategorySet()
    for element in selection:
        cset.Insert(element.Category)
    return cset


def get_selection():
    """Returns the current selected items.

    Returns:
        (ElementSelection): the current selected items
    """
    return ElementSelection()
