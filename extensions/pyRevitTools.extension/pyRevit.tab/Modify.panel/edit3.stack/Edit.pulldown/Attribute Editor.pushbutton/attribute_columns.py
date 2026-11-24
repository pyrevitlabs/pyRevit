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
from pyrevit.revit import get_parameter_data_type, query, units as revit_units

logger = script.get_logger()

SCOPE_ELEMENT = "i"
SCOPE_TYPE = "t"

KIND_BOOL = "bool"
KIND_CHOICE = "choice"
KIND_NUMBER = "number"
KIND_INTEGER = "integer"
KIND_REFERENCE = "reference"
KIND_TEXT = "text"

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


def _is_unitless_unit(unit_id):
    for name in ("General", "Currency"):
        unitless = getattr(DB.UnitTypeId, name, None)
        if unitless is not None and unit_id == unitless:
            return True
    return False


def unit_label(unit_id, symbol_id, symbol_label):
    """Return the short text that names a unit in a column heading, or ``""``."""
    if unit_id == DB.UnitTypeId.FeetFractionalInches:
        return "ft"
    if unit_id == DB.UnitTypeId.FractionalInches:
        return "in"
    if symbol_label:
        return symbol_label
    if _is_unitless_unit(unit_id):
        return ""
    try:
        return DB.LabelUtils.GetLabelForUnit(unit_id)
    except Exception as ex:
        logger.debug("No unit label: %s", ex)
        return ""


class ParameterTraits(object):
    """What the value codec must know about one live parameter.

    Traits belong to a parameter, not to a column: a project parameter is keyed
    by name, so one column can hold an Area on one element and an Angle on
    another, and each cell must be converted with its own unit.
    """

    def __init__(self, storage, spec_id, is_yesno, is_workset, unit_id, unit_symbol):
        self.storage = storage
        self.spec_id = spec_id
        self.is_yesno = is_yesno
        self.is_workset = is_workset
        self.unit_id = unit_id
        self.unit_symbol = unit_symbol

    def cell_kind(self):
        """Return how the page edits the cell: a ``KIND_*`` constant."""
        if self.is_yesno:
            return KIND_BOOL
        if self.is_workset:
            return KIND_CHOICE
        if self.storage == DB.StorageType.Double:
            return KIND_NUMBER
        if self.storage == DB.StorageType.Integer:
            return KIND_INTEGER
        if self.storage == DB.StorageType.ElementId:
            return KIND_REFERENCE
        return KIND_TEXT


def read_traits(parameter, doc, cache):
    """Return the ``ParameterTraits`` of ``parameter``.

    Args:
        parameter (DB.Parameter): the live parameter.
        doc (DB.Document): document whose project units apply.
        cache (dict): memo shared by one reading pass, keyed by spec.
    """
    definition = parameter.Definition
    storage = parameter.StorageType
    spec = get_parameter_data_type(definition)
    spec_id = spec.TypeId if spec is not None else ""
    if spec_id not in cache:
        cache[spec_id] = _spec_facts(spec, storage, doc)
    is_yesno, unit_id, unit_symbol = cache[spec_id]
    is_workset = (
        isinstance(definition, DB.InternalDefinition)
        and definition.BuiltInParameter == DB.BuiltInParameter.ELEM_PARTITION_PARAM
    )
    if storage != DB.StorageType.Double:
        unit_id, unit_symbol = None, ""
    return ParameterTraits(storage, spec_id, is_yesno, is_workset, unit_id, unit_symbol)


def _spec_facts(spec, storage, doc):
    if spec is None:
        return False, None, ""
    is_yesno = spec == DB.SpecTypeId.Boolean.YesNo
    if not DB.UnitUtils.IsMeasurableSpec(spec):
        return is_yesno, None, ""
    unit_id, _, symbol_id, symbol_label = revit_units.get_unit_info(spec, doc)
    return is_yesno, unit_id, unit_label(unit_id, symbol_id, symbol_label)


class ColumnSpec(object):
    """One grid column: locates its parameter on an element and describes it.

    Attributes:
        traits (ParameterTraits | None): traits of the first parameter found;
            None until :meth:`describe` ran. It describes the column heading
            and editor, while each cell is converted with its own traits.
        field_format (DB.FormatOptions | None): the schedule field's own number
            format, when the field overrides the project units.
    """

    def __init__(self, key, heading=None, field_format=None):
        parts = key.split("|")
        self.key = key
        self.kind = parts[0]
        self.scope = parts[-1]
        self.value = "|".join(parts[1:-1])
        self.name = self.value if self.kind == "name" else ""
        self.heading = heading or self.name
        self.field_format = field_format
        self.read_only = True
        self.available = False
        self.traits = None
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
                return query.get_param(target, self._built_in)
            if self._guid is not None:
                return query.get_param(target, self._guid)
            return target.LookupParameter(self.value)
        except Exception as ex:
            logger.debug("Parameter lookup failed for %s: %s", self.key, ex)
            return None

    def describe(self, parameter, doc, cache):
        """Fill the column's metadata from one live parameter."""
        definition = parameter.Definition
        self.name = definition.Name
        self.heading = self.heading or self.name
        self.read_only = parameter.IsReadOnly
        self.traits = read_traits(parameter, doc, cache)
        self.available = True

    def cell_kind(self):
        return self.traits.cell_kind() if self.traits else KIND_TEXT

    def accepts(self, traits, unit_mode):
        """Whether a cell with ``traits`` may be shown and edited as this column.

        A cell of another kind is never accepted. In Number mode a cell whose
        spec differs from the column's is refused too, because the heading's
        unit would be wrong for it.
        """
        if self.traits is None:
            return True
        if traits.cell_kind() != self.traits.cell_kind():
            return False
        if unit_mode != "number":
            return True
        if traits.unit_id is None and self.traits.unit_id is None:
            return True
        return traits.spec_id == self.traits.spec_id

    def to_json(self, choices=None):
        return {
            "key": self.key,
            "heading": self.heading,
            "name": self.name,
            "scope": self.scope,
            "kind": self.cell_kind(),
            "readOnly": self.read_only,
            "unit": self.traits.unit_symbol if self.traits else "",
            "available": self.available,
            "choices": choices,
        }
