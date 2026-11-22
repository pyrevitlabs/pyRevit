# -*- coding: utf-8 -*-
"""Grid columns of the Attribute Editor: how to find a parameter and describe it.

A column is identified by a key of the form ``<kind>|<value>|<scope>``:
``kind`` is ``bip`` (built-in parameter id), ``guid`` (shared parameter) or
``name`` (project parameter); ``scope`` is ``i`` when the value lives on the
element itself and ``t`` when it lives on the element's type. The page can
therefore ask for any column set again without Python keeping state.
"""

from pyrevit import DB, script
from pyrevit.compat import get_elementid_value_func
from pyrevit.framework import System
from pyrevit.revit import get_parameter_data_type, is_yesno_parameter

logger = script.get_logger()

SCOPE_ELEMENT = "i"
SCOPE_TYPE = "t"

get_elementid_value = get_elementid_value_func()


def id_value(element_id):
    return int(get_elementid_value(element_id))


def make_key(kind, value, scope):
    return "|".join((kind, value, scope))


def key_for_parameter_id(doc, parameter_id, scope):
    """Return the column key of a schedule field's parameter id, or None."""
    value = id_value(parameter_id)
    if value < 0:
        return make_key("bip", str(value), scope)
    parameter_element = doc.GetElement(parameter_id)
    if isinstance(parameter_element, DB.SharedParameterElement):
        return make_key("guid", str(parameter_element.GuidValue), scope)
    if isinstance(parameter_element, DB.ParameterElement):
        return make_key("name", parameter_element.GetDefinition().Name, scope)
    return None


def key_for_parameter(parameter, scope):
    """Return the column key that finds ``parameter`` again on another element."""
    definition = parameter.Definition
    if isinstance(definition, DB.InternalDefinition):
        built_in = definition.BuiltInParameter
        if built_in != DB.BuiltInParameter.INVALID:
            return make_key("bip", str(int(built_in)), scope)
    if parameter.IsShared:
        return make_key("guid", str(parameter.GUID), scope)
    return make_key("name", definition.Name, scope)


def unit_label(format_options):
    unit_id = format_options.GetUnitTypeId()
    if unit_id == DB.UnitTypeId.FeetFractionalInches:
        return "ft"
    if unit_id == DB.UnitTypeId.FractionalInches:
        return "in"
    try:
        return DB.LabelUtils.GetLabelForSymbol(format_options.GetSymbolTypeId())
    except Exception as ex:
        logger.debug("No unit symbol label: %s", ex)
    try:
        return DB.LabelUtils.GetLabelForUnit(format_options.GetUnitTypeId())
    except Exception as ex:
        logger.debug("No unit label: %s", ex)
    return ""


class ColumnSpec(object):
    """One grid column: locates its parameter on an element and describes it."""

    def __init__(self, key, heading=None):
        parts = key.split("|")
        self.key = key
        self.kind = parts[0]
        self.scope = parts[-1]
        self.value = "|".join(parts[1:-1])
        self.name = self.value if self.kind == "name" else ""
        self.heading = heading or self.name
        self.storage = None
        self.read_only = True
        self.available = False
        self.spec = None
        self.unit_id = None
        self.unit_symbol = ""
        self.is_yesno = False
        self.is_workset = False
        self._built_in = None
        self._guid = None
        if self.kind == "bip":
            self._built_in = DB.BuiltInParameter(int(self.value))
        elif self.kind == "guid":
            self._guid = System.Guid(self.value)

    def target(self, element):
        """Return the element that carries this column's parameter."""
        if self.scope == SCOPE_TYPE and not isinstance(element, DB.ElementType):
            return element.Document.GetElement(element.GetTypeId())
        return element

    def find(self, element):
        """Return the parameter on ``element`` (or its type), or None."""
        target = self.target(element)
        if target is None:
            return None
        try:
            if self._built_in is not None:
                return target.get_Parameter(self._built_in)
            if self._guid is not None:
                return target.get_Parameter(self._guid)
            return target.LookupParameter(self.value)
        except Exception as ex:
            logger.debug("Parameter lookup failed for %s: %s", self.key, ex)
            return None

    def describe(self, parameter, units):
        """Fill the column's metadata from one live parameter."""
        definition = parameter.Definition
        self.name = definition.Name
        self.heading = self.heading or self.name
        self.storage = parameter.StorageType
        self.read_only = parameter.IsReadOnly
        self.spec = get_parameter_data_type(definition)
        self.is_yesno = is_yesno_parameter(definition)
        self.is_workset = (
            isinstance(definition, DB.InternalDefinition)
            and definition.BuiltInParameter == DB.BuiltInParameter.ELEM_PARTITION_PARAM
        )
        if (
            self.storage == DB.StorageType.Double
            and self.spec is not None
            and DB.UnitUtils.IsMeasurableSpec(self.spec)
        ):
            format_options = units.GetFormatOptions(self.spec)
            self.unit_id = format_options.GetUnitTypeId()
            self.unit_symbol = unit_label(format_options)
        self.available = True

    def cell_kind(self):
        if self.is_yesno:
            return "bool"
        if self.is_workset:
            return "choice"
        if self.storage == DB.StorageType.Double:
            return "number"
        if self.storage == DB.StorageType.Integer:
            return "integer"
        if self.storage == DB.StorageType.ElementId:
            return "reference"
        return "text"

    def to_json(self, choices=None):
        return {
            "key": self.key,
            "heading": self.heading,
            "name": self.name,
            "scope": self.scope,
            "kind": self.cell_kind(),
            "readOnly": self.read_only,
            "unit": self.unit_symbol,
            "available": self.available,
            "choices": choices,
        }
