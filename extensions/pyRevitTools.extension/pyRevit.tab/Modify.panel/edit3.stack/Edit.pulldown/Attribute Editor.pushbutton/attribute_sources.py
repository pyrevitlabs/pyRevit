# -*- coding: utf-8 -*-
"""Where the Attribute Editor gets its rows and columns from.

``ScheduleSource`` mirrors an existing Revit schedule: its elements, its
supported fields in order, its sort. ``ScratchSource`` builds a grid from
categories without any schedule. Both hand out the same shapes so the grid
code does not care which one it reads.
"""

import itertools

from pyrevit import DB, framework, revit, script
from pyrevit.compat import get_elementid_from_value_func
from pyrevit.coreutils import get_enum_none

from attribute_columns import (
    SCOPE_ELEMENT,
    SCOPE_TYPE,
    ColumnSpec,
    id_value,
    key_for_parameter,
    key_for_parameter_id,
)

logger = script.get_logger()

get_elementid_from_value = get_elementid_from_value_func()

SCRATCH_SCOPES = ("model", "view", "selection")
INSTANCE_SAMPLE = 60
TYPE_SAMPLE = 40
SCAN_ALL_SAMPLE = 5000


def list_schedules(doc):
    """Return ``[{id, name}]`` for every usable schedule, sorted by name."""
    listing = [
        {"id": id_value(schedule.Id), "name": schedule.Name}
        for schedule in revit.query.get_all_schedules(doc=doc)
    ]
    return sorted(listing, key=lambda item: item["name"].lower())


def list_categories(doc):
    """Return ``[{id, name, instances, types}]`` for categories that hold elements."""
    listing = []
    for category in doc.Settings.Categories:
        if category.CategoryType not in (
            DB.CategoryType.Model,
            DB.CategoryType.Annotation,
        ):
            continue
        if not category.AllowsBoundParameters or category.IsTagCategory:
            continue
        collector = DB.FilteredElementCollector(doc).OfCategoryId(category.Id)
        instances = collector.WhereElementIsNotElementType().GetElementCount()
        collector = DB.FilteredElementCollector(doc).OfCategoryId(category.Id)
        types = collector.WhereElementIsElementType().GetElementCount()
        if instances or types:
            listing.append(
                {
                    "id": id_value(category.Id),
                    "name": category.Name,
                    "instances": instances,
                    "types": types,
                }
            )
    return sorted(listing, key=lambda item: item["name"].lower())


def _scope_of_field_type(field_type):
    if field_type == DB.ScheduleFieldType.Instance:
        return SCOPE_ELEMENT
    if field_type == DB.ScheduleFieldType.ElementType:
        return SCOPE_TYPE
    return None


class ScheduleSource(object):
    """The elements and fields of one Revit schedule."""

    kind = "schedule"

    def __init__(self, doc, schedule):
        self.doc = doc
        self.schedule = schedule
        self.title = schedule.Name

    def to_json(self):
        return {"kind": self.kind, "id": id_value(self.schedule.Id)}

    def elements(self):
        collector = DB.FilteredElementCollector(self.doc, self.schedule.Id)
        return [
            element
            for element in collector
            if element.Category is not None and not element.Category.IsTagCategory
        ]

    def default_columns(self):
        """Return a ColumnSpec per visible, supported field, in schedule order."""
        definition = self.schedule.Definition
        columns = []
        seen = set()
        for field_id in definition.GetFieldOrder():
            field = definition.GetField(field_id)
            key = self._key_of_field(field)
            if field.IsHidden or key is None or key in seen:
                continue
            seen.add(key)
            columns.append(ColumnSpec(key, field.ColumnHeading))
        return columns

    def _key_of_field(self, field):
        scope = _scope_of_field_type(field.FieldType)
        if scope is None or field.IsCalculatedField:
            return None
        if field.ParameterId == DB.ElementId.InvalidElementId:
            return None
        return key_for_parameter_id(self.doc, field.ParameterId, scope)

    def field_ids_by_key(self):
        """Return ``{column key: ScheduleFieldId}`` of the visible supported fields."""
        definition = self.schedule.Definition
        by_key = {}
        for field_id in definition.GetFieldOrder():
            field = definition.GetField(field_id)
            key = self._key_of_field(field)
            if not field.IsHidden and key is not None and key not in by_key:
                by_key[key] = field_id
        return by_key

    def sort_hints(self, keys):
        """Return the schedule's sort fields that map to ``keys``."""
        definition = self.schedule.Definition
        key_of_field = dict(
            (int(field_id.IntegerValue), key)
            for key, field_id in self.field_ids_by_key().items()
        )
        hints = []
        for index in range(definition.GetSortGroupFieldCount()):
            sort_field = definition.GetSortGroupField(index)
            key = key_of_field.get(int(sort_field.FieldId.IntegerValue))
            if key in keys:
                descending = sort_field.SortOrder == DB.ScheduleSortOrder.Descending
                hints.append({"key": key, "dir": "desc" if descending else "asc"})
        return hints

    def schedulable_fields(self):
        """Return ``{column key: SchedulableField}`` for every field that can be added."""
        by_key = {}
        for field in self.schedule.Definition.GetSchedulableFields():
            scope = _scope_of_field_type(field.FieldType)
            if scope is None or field.ParameterId == DB.ElementId.InvalidElementId:
                continue
            key = key_for_parameter_id(self.doc, field.ParameterId, scope)
            if key is not None and key not in by_key:
                by_key[key] = field
        return by_key

    def available(self, scan_all=False):
        return sorted(
            (
                {
                    "key": key,
                    "heading": field.GetName(self.doc),
                    "scope": key.rsplit("|", 1)[1],
                }
                for key, field in self.schedulable_fields().items()
            ),
            key=lambda item: item["heading"].lower(),
        )


class ScratchSource(object):
    """Elements of chosen categories, with columns picked by the user."""

    kind = "scratch"
    title = ""

    def __init__(self, doc, payload):
        self.doc = doc
        self.category_ids = [int(value) for value in payload.get("categories") or []]
        scope = payload.get("scope")
        self.scope = scope if scope in SCRATCH_SCOPES else "model"
        self.types = bool(payload.get("types"))

    def to_json(self):
        return {
            "kind": self.kind,
            "categories": self.category_ids,
            "scope": self.scope,
            "types": self.types,
        }

    def default_columns(self):
        return []

    def sort_hints(self, keys):
        return []

    def _category_filter(self):
        ids = [get_elementid_from_value(value) for value in self.category_ids]
        return DB.ElementMulticategoryFilter(framework.to_clr_list(DB.ElementId, ids))

    def _type_collector(self):
        return (
            DB.FilteredElementCollector(self.doc)
            .WherePasses(self._category_filter())
            .WhereElementIsElementType()
        )

    def _scoped_collector(self):
        if self.scope == "view":
            return DB.FilteredElementCollector(self.doc, self.doc.ActiveView.Id)
        if self.scope == "selection":
            ids = list(revit.get_selection().element_ids)
            return DB.FilteredElementCollector(
                self.doc, framework.to_clr_list(DB.ElementId, ids)
            )
        return DB.FilteredElementCollector(self.doc)

    def _instance_collector(self):
        return (
            self._scoped_collector()
            .WherePasses(self._category_filter())
            .WhereElementIsNotElementType()
        )

    def iter_elements(self):
        if not self.category_ids:
            return []
        if self.types and self.scope == "model":
            return self._type_collector()
        if not self.types:
            return self._instance_collector()
        return self._types_of_scoped_instances()

    def _types_of_scoped_instances(self):
        seen = set()
        types = []
        for element in self._instance_collector():
            type_id = element.GetTypeId()
            if type_id == DB.ElementId.InvalidElementId or id_value(type_id) in seen:
                continue
            seen.add(id_value(type_id))
            types.append(self.doc.GetElement(type_id))
        return types

    def elements(self):
        return list(self.iter_elements())

    def available(self, scan_all=False):
        """Return the parameters found on a sample of the chosen elements.

        The sample is the first few elements and types, so a parameter that only
        a few families carry can be missed unless ``scan_all`` reads them all.
        """
        instance_limit = SCAN_ALL_SAMPLE if scan_all else INSTANCE_SAMPLE
        type_limit = SCAN_ALL_SAMPLE if scan_all else TYPE_SAMPLE
        sources = [(itertools.islice(self.iter_elements(), instance_limit), "i")]
        if self.category_ids and not self.types:
            type_sample = itertools.islice(self._type_collector(), type_limit)
            sources.append((type_sample, SCOPE_TYPE))
        no_storage = get_enum_none(DB.StorageType)
        found = {}
        for elements, scope in sources:
            for element in elements:
                for parameter in element.Parameters:
                    if parameter.StorageType == no_storage:
                        continue
                    key = key_for_parameter(parameter, scope)
                    if key not in found:
                        found[key] = {
                            "key": key,
                            "heading": parameter.Definition.Name,
                            "scope": scope,
                            "readOnly": parameter.IsReadOnly,
                        }
        return sorted(found.values(), key=lambda item: item["heading"].lower())


def source_from_payload(doc, payload):
    """Build the source a page message describes.

    Raises:
        ValueError: when a schedule id no longer resolves to a schedule.
    """
    description = payload.get("source") or {}
    if description.get("kind") == "schedule":
        schedule = doc.GetElement(get_elementid_from_value(int(description["id"])))
        if not isinstance(schedule, DB.ViewSchedule):
            raise ValueError("schedule")
        return ScheduleSource(doc, schedule)
    return ScratchSource(doc, description)
