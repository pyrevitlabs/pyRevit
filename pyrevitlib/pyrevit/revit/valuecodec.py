# -*- coding: utf-8 -*-
"""Converts between Revit parameter values and the text that tools show or read.

Every tool that displays a parameter as text, or writes typed, pasted or
imported text back, goes through :class:`ValueCodec`, so that they all read and
refuse the same text. A value is always converted with the spec and unit of the
parameter being read or written, never with those of a column or of another
element.

Number notation is defined by :func:`pyrevit.revit.units.parse_number` and
:func:`pyrevit.revit.units.format_number`. Text that is more than a bare
number, such as ``1500 mm``, ``1'-6"`` or ``=2*3``, is read by Revit's own
parser.

Works with the unit API of Revit 2021 and with the one of 2022 and newer.
"""

import math
import numbers
import re

from pyrevit import DB, HOST_APP
from pyrevit.compat import get_elementid_value_func, safe_strtype
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit import units as revit_units
from pyrevit.revit.db import get_parameter_data_type, is_yesno_parameter, query

mlogger = get_logger(__name__)

UNIT_DISPLAY = "display"
UNIT_NUMBER = "number"
UNIT_INTERNAL = "internal"
UNIT_MODES = (UNIT_DISPLAY, UNIT_NUMBER, UNIT_INTERNAL)

YES_WORDS = frozenset(
    "yes y true 1 x ja j wahr sí si s verdadero oui o vrai sim verdadeiro "
    "да д истина 예 네 참 是 真".split()
)
NO_WORDS = frozenset(
    "no n false 0 nein falsch falso non faux não nao нет н ложь "
    "아니요 아니오 거짓 否 假".split()
)

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
EXCEL_SIGNIFICANT_DIGITS = 15

_INTEGER_TEXT = re.compile(r"^[+-]?[0-9]+$")
_SEPARATED_NUMBER = re.compile(
    r"^[+-]?(?=[^.,]*[.,])[0-9.,\s]+(?:[eE][+-]?[0-9]+)?$", re.UNICODE
)

get_elementid_value = get_elementid_value_func()


def as_text(value):
    """Return a cell or field value as the text it stands for.

    Args:
        value (str | float | int | None): text, or a number from a source that
            stores numbers as floats, such as an Excel cell

    Returns:
        (str): text unchanged. A number is written with the 15 significant
            digits Excel shows, a dot as decimal symbol and no trailing ``.0``.
            None becomes an empty string.
    """
    if value is None:
        return ""
    if isinstance(value, numbers.Real):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return safe_strtype(value)
        return revit_units.format_number(
            number, significant_digits=EXCEL_SIGNIFICANT_DIGITS
        )
    return safe_strtype(value)


def parse_whole_number(value, decimal="."):
    """Read a value for an Integer parameter.

    Args:
        value (str | float | int): see :func:`pyrevit.revit.units.parse_number`
        decimal (str, optional): ``"."`` or ``","``

    Returns:
        (int): the value as a signed 32-bit integer

    Raises:
        ValueRefused: when the value is not a number, has a fraction or does
            not fit 32 bits. Nothing is rounded, truncated or wrapped.
    """
    number = revit_units.parse_number(value, decimal)
    if number != math.floor(number):
        raise revit_units.ValueRefused(
            revit_units.REFUSED_WHOLE_NUMBER,
            "'{}' is not a whole number".format(value),
        )
    if not INT32_MIN <= number <= INT32_MAX:
        raise revit_units.ValueRefused(
            revit_units.REFUSED_RANGE,
            "'{}' is outside the range of an Integer".format(value),
        )
    return int(number)


def parse_yes_no(value, decimal=".", yes_words=YES_WORDS, no_words=NO_WORDS):
    """Read a value for a Yes/No parameter.

    Args:
        value (str | float | int): a word in ``yes_words`` or ``no_words`` in
            any letter case, or the number 1 or 0
        decimal (str, optional): ``"."`` or ``","``
        yes_words (frozenset, optional): lower-case words that mean Yes;
            defaults to those of the languages pyRevit is translated to
        no_words (frozenset, optional): lower-case words that mean No

    Returns:
        (int): 1 or 0

    Raises:
        ValueRefused: for anything else. Unknown text never means No.
    """
    if not isinstance(value, numbers.Real):
        word = value.strip().lower()
        if word in yes_words:
            return 1
        if word in no_words:
            return 0
    try:
        number = revit_units.parse_number(value, decimal)
    except revit_units.ValueRefused:
        number = None
    if number in (0, 1):
        return int(number)
    raise revit_units.ValueRefused(
        revit_units.REFUSED_YES_NO, "'{}' is not a Yes/No value".format(value)
    )


def _refuse(reason, message):
    raise revit_units.ValueRefused(reason, message)


def _required_text(value):
    text = value.strip()
    if not text:
        _refuse(revit_units.REFUSED_EMPTY, "a value is required")
    return text


def _bare_number(text, decimal):
    """Return the number that ``text`` writes without a unit.

    None means that the text is left to Revit's parser.

    Raises:
        ValueRefused: for digits and separators that are not a number in this
            notation. Revit's parser must not get them, because it would read
            ``1.234`` as a decimal number in a comma-decimal project.
    """
    try:
        return revit_units.parse_number(text, decimal)
    except revit_units.ValueRefused:
        if _SEPARATED_NUMBER.match(text):
            raise
        return None


def _spec_of(parameter):
    if HOST_APP.is_newer_than(2021):
        return parameter.Definition.GetDataType()
    return parameter.Definition.UnitType


def _unit_of(format_options):
    if HOST_APP.is_newer_than(2021):
        return format_options.GetUnitTypeId()
    return format_options.DisplayUnits


def _is_valid_unit(spec, unit):
    if HOST_APP.is_newer_than(2021):
        return DB.UnitUtils.IsValidUnit(spec, unit)
    return DB.UnitUtils.IsValidDisplayUnit(spec, unit)


def _is_modifiable(spec):
    if HOST_APP.is_newer_than(2021):
        return DB.Units.IsModifiableSpec(spec)
    return DB.Units.IsModifiableUnitType(spec)


def _format_with_units(units, spec, value):
    if HOST_APP.is_newer_than(2021):
        return DB.UnitFormatUtils.Format(units, spec, value, False)
    return DB.UnitFormatUtils.Format(units, spec, value, False, False)


def _is_material_parameter(definition):
    if HOST_APP.is_newer_than(2021):
        return get_parameter_data_type(definition) == DB.SpecTypeId.Reference.Material
    return definition.ParameterType == DB.ParameterType.Material


def _is_workset_parameter(definition):
    return (
        isinstance(definition, DB.InternalDefinition)
        and definition.BuiltInParameter == DB.BuiltInParameter.ELEM_PARTITION_PARAM
    )


def _same_parameter(element, parameter):
    definition = parameter.Definition
    if (
        isinstance(definition, DB.InternalDefinition)
        and definition.BuiltInParameter != DB.BuiltInParameter.INVALID
    ):
        return element.get_Parameter(definition.BuiltInParameter)
    if parameter.IsShared:
        return element.get_Parameter(parameter.GUID)
    return element.get_Parameter(definition)


def _names_of(element):
    name = query.get_name(element)
    names = [name]
    family = (
        getattr(element, "FamilyName", None)
        if isinstance(element, DB.ElementType)
        else None
    )
    if family:
        names.append("{} : {}".format(family, name))
        names.append("{}: {}".format(family, name))
    return names


def _in_category(element, category):
    if category is None or element.Category is None:
        return True
    return element.Category.Id == category.Id


class ValueCodec(object):
    """Reads and writes the parameters of one document as text.

    The unit mode decides how a number with a unit appears and how a bare
    number is read:

    - ``UNIT_DISPLAY``: Revit's own text, with the unit symbol when the format
      shows one. A bare number means the same as in the Revit UI.
    - ``UNIT_NUMBER``: the bare number in the display unit of the parameter.
    - ``UNIT_INTERNAL``: the raw Revit value. Integers with named values also
      read as their raw number.

    In every mode, Yes/No parameters read as the Yes and No labels, worksets as
    the workset name and element references as the text Revit shows.

    The codec caches the units, worksets and element names of the document, so
    create one for each operation. One that outlives a model change looks up
    stale names.

    Args:
        doc (DB.Document): the document that owns the parameters
        unit_mode (str, optional): one of ``UNIT_MODES``
        yes_label (str, optional): text read for Yes; also accepted on write
        no_label (str, optional): text read for No; also accepted on write

    Raises:
        ValueError: for an unknown unit mode
    """

    def __init__(self, doc, unit_mode=UNIT_DISPLAY, yes_label="Yes", no_label="No"):
        if unit_mode not in UNIT_MODES:
            raise ValueError("unknown unit mode: {}".format(unit_mode))
        self.doc = doc
        self.unit_mode = unit_mode
        self.yes_label = yes_label
        self.no_label = no_label
        self._yes_words = YES_WORDS | frozenset((yes_label.lower(),))
        self._no_words = NO_WORDS | frozenset((no_label.lower(),))
        self._units = None
        self._decimal = None
        self._worksets = None
        self._labels = {}
        self._reference_samples = {}
        self._named_elements = {}

    @property
    def units(self):
        """The project's ``DB.Units``."""
        if self._units is None:
            self._units = self.doc.GetUnits()
        return self._units

    @property
    def decimal(self):
        """The project's decimal symbol, ``"."`` or ``","``."""
        if self._decimal is None:
            self._decimal = revit_units.decimal_symbol(self.doc)
        return self._decimal

    def format_options(self, spec, field_format=None):
        """Return the format that applies to a measurable spec.

        Args:
            spec (DB.ForgeTypeId or DB.UnitType): the parameter's spec
            field_format (DB.FormatOptions, optional): the format of a
                schedule field. It is ignored when it uses the project default
                or when its unit is not a unit of ``spec``.

        Returns:
            (DB.FormatOptions): the field's format, or the project's
        """
        return self._field_options(spec, field_format) or self.units.GetFormatOptions(
            spec
        )

    def display_unit(self, parameter, field_format=None):
        """Return the unit that a parameter's value is shown in.

        Args:
            parameter (DB.Parameter): the parameter
            field_format (DB.FormatOptions, optional): see
                :meth:`format_options`

        Returns:
            (DB.ForgeTypeId or DB.DisplayUnitType): the unit, or None for a
                parameter that carries no unit
        """
        if parameter.StorageType != DB.StorageType.Double:
            return None
        spec = _spec_of(parameter)
        if not revit_units.is_measurable(spec):
            return None
        return _unit_of(self.format_options(spec, field_format))

    def display_number(self, parameter, field_format=None):
        """Return a Double parameter's value as a number in its display unit.

        Args:
            parameter (DB.Parameter): a parameter with Double storage
            field_format (DB.FormatOptions, optional): see
                :meth:`format_options`

        Returns:
            (float): the unrounded value; the internal value when the parameter
                carries no unit
        """
        unit = self.display_unit(parameter, field_format)
        if unit is None:
            return parameter.AsDouble()
        return DB.UnitUtils.ConvertFromInternalUnits(parameter.AsDouble(), unit)

    def read(self, parameter, field_format=None):
        """Return a parameter's value as text.

        Args:
            parameter (DB.Parameter): the parameter
            field_format (DB.FormatOptions, optional): see
                :meth:`format_options`

        Returns:
            (str): the text; empty for a parameter without a value and for an
                empty element reference

        Note:
            In ``UNIT_DISPLAY`` mode digit grouping is left out, because
            Revit's parser refuses the grouped text that Revit shows. Shown
            numbers are rounded as the format says, so writing unchanged text
            back can change the value. Write only text that was edited.
        """
        if not parameter.HasValue:
            return ""
        storage = parameter.StorageType
        if storage == DB.StorageType.String:
            return parameter.AsString() or ""
        if storage == DB.StorageType.Double:
            return self._read_double(parameter, field_format)
        if storage == DB.StorageType.Integer:
            return self._read_integer(parameter)
        if storage == DB.StorageType.ElementId:
            if parameter.AsElementId() == DB.ElementId.InvalidElementId:
                return ""
            return parameter.AsValueString() or ""
        return ""

    def write(self, parameter, value, field_format=None, unit_id=None):
        """Write text, or a number, into a parameter.

        Args:
            parameter (DB.Parameter): the parameter; a transaction must be open
            value (str | float | int): what to write. A number is taken as is:
                in ``unit_id`` or the display unit for a value with a unit
                (the internal value in ``UNIT_INTERNAL`` mode).
            field_format (DB.FormatOptions, optional): see
                :meth:`format_options`; also applies when reading the text
            unit_id (DB.ForgeTypeId or DB.DisplayUnitType, optional): the unit
                that a bare number is expressed in, overriding the unit mode
                and ``field_format``. It only applies to values with a unit.

        Raises:
            ValueRefused: when the value must not be written. The parameter is
                then unchanged.

        Note:
            Empty text clears a text parameter or an element reference and is
            refused for every other parameter. An element reference is looked
            up by the text that the same parameter shows on other elements of
            the category, then by element name or ``Family: Type`` among
            elements like the current one. A name that matches several of
            them is refused. Revit's own exceptions pass through.
        """
        if parameter.IsReadOnly:
            _refuse(revit_units.REFUSED_READ_ONLY, "the parameter is read-only")
        storage = parameter.StorageType
        if storage == DB.StorageType.String:
            self._set(parameter, as_text(value))
        elif storage == DB.StorageType.Double:
            self._write_double(parameter, value, field_format, unit_id)
        elif storage == DB.StorageType.Integer:
            self._write_integer(parameter, value)
        elif storage == DB.StorageType.ElementId:
            self._write_reference(parameter, as_text(value).strip())
        else:
            _refuse(
                revit_units.REFUSED_UNSUPPORTED,
                "this kind of parameter cannot be written",
            )

    @staticmethod
    def _require(accepted):
        if accepted is False:
            _refuse(revit_units.REFUSED_REJECTED, "Revit did not accept the value")

    def _set(self, parameter, value):
        self._require(parameter.Set(value))

    def _field_options(self, spec, field_format):
        if field_format is None or field_format.UseDefault:
            return None
        if not _is_valid_unit(spec, _unit_of(field_format)):
            return None
        return field_format

    def _units_with(self, spec, format_options):
        units = self.doc.GetUnits()
        if _is_modifiable(spec):
            units.SetFormatOptions(spec, format_options)
        return units

    def _ungrouped_units(self, spec, format_options):
        units = self._units_with(spec, format_options)
        if _is_modifiable(spec):
            ungrouped = units.GetFormatOptions(spec)
            ungrouped.UseDigitGrouping = False
            units.SetFormatOptions(spec, ungrouped)
        return units

    def _read_double(self, parameter, field_format):
        if self.unit_mode == UNIT_INTERNAL:
            return revit_units.format_number(parameter.AsDouble(), self.decimal)
        spec = _spec_of(parameter)
        measurable = revit_units.is_measurable(spec)
        if measurable and self.unit_mode == UNIT_NUMBER:
            return revit_units.format_number(
                self.display_number(parameter, field_format), self.decimal
            )
        if measurable:
            field_options = self._field_options(spec, field_format)
            options = field_options or self.units.GetFormatOptions(spec)
            if field_options is not None or options.UseDigitGrouping:
                return _format_with_units(
                    self._ungrouped_units(spec, options), spec, parameter.AsDouble()
                )
        return parameter.AsValueString() or revit_units.format_number(
            parameter.AsDouble(), self.decimal
        )

    def _read_integer(self, parameter):
        if _is_workset_parameter(parameter.Definition):
            return parameter.AsValueString() or ""
        if is_yesno_parameter(parameter.Definition):
            return self.yes_label if parameter.AsInteger() else self.no_label
        raw = safe_strtype(parameter.AsInteger())
        if self.unit_mode == UNIT_INTERNAL:
            return raw
        return parameter.AsValueString() or raw

    def _write_double(self, parameter, value, field_format, unit_id):
        spec = _spec_of(parameter)
        measurable = revit_units.is_measurable(spec)
        number_unit = None
        if measurable:
            if unit_id is not None:
                if not _is_valid_unit(spec, unit_id):
                    _refuse(
                        revit_units.REFUSED_UNSUPPORTED,
                        "the given unit is not a unit of this parameter",
                    )
                number_unit = unit_id
            elif self.unit_mode != UNIT_INTERNAL:
                number_unit = _unit_of(self.format_options(spec, field_format))
        if isinstance(value, numbers.Real):
            self._set_number(parameter, revit_units.parse_number(value), number_unit)
            return
        text = _required_text(value)
        if not measurable or (number_unit is None and unit_id is None):
            self._set(parameter, revit_units.parse_number(text, self.decimal))
            return
        number = _bare_number(text, self.decimal)
        if number is not None:
            if unit_id is not None or self.unit_mode == UNIT_NUMBER:
                self._set_number(parameter, number, number_unit)
                return
            text = revit_units.format_number(number, self.decimal)
        if unit_id is not None:
            options = DB.FormatOptions(unit_id)
        else:
            options = self._field_options(spec, field_format)
        if options is None and self.unit_mode == UNIT_DISPLAY:
            self._require(parameter.SetValueString(text))
            return
        units = self.units if options is None else self._units_with(spec, options)
        self._set(parameter, self._parse_with_revit(units, spec, text))

    def _set_number(self, parameter, number, unit):
        if unit is not None:
            number = DB.UnitUtils.ConvertToInternalUnits(number, unit)
        self._set(parameter, number)

    @staticmethod
    def _parse_with_revit(units, spec, text):
        try:
            parsed, value = DB.UnitFormatUtils.TryParse(
                units, spec, text, DB.ValueParsingOptions()
            )
        except Exception as parse_error:
            mlogger.debug("Revit could not parse '%s': %s", text, parse_error)
            parsed, value = False, 0.0
        if not parsed or math.isnan(value) or math.isinf(value):
            _refuse(revit_units.REFUSED_REJECTED, "Revit cannot read '{}'".format(text))
        return value

    def _write_integer(self, parameter, value):
        if is_yesno_parameter(parameter.Definition):
            if not isinstance(value, numbers.Real):
                value = _required_text(value)
            self._set(
                parameter,
                parse_yes_no(value, self.decimal, self._yes_words, self._no_words),
            )
        elif _is_workset_parameter(parameter.Definition):
            self._write_workset(parameter, _required_text(as_text(value)))
        elif isinstance(value, numbers.Real):
            self._set(parameter, parse_whole_number(value))
        else:
            self._write_integer_text(parameter, _required_text(value))

    def _write_integer_text(self, parameter, text):
        if _INTEGER_TEXT.match(text):
            self._set(parameter, parse_whole_number(text))
            return
        labelled = self._integer_labels(parameter).get(text.lower())
        if labelled is not None:
            self._set(parameter, labelled)
        elif _bare_number(text, self.decimal) is not None:
            self._set(parameter, parse_whole_number(text, self.decimal))
        else:
            self._require(parameter.SetValueString(text))

    def _write_workset(self, parameter, name):
        if self._worksets is None:
            collector = DB.FilteredWorksetCollector(self.doc).OfKind(
                DB.WorksetKind.UserWorkset
            )
            self._worksets = dict(
                (workset.Name, int(workset.Id.IntegerValue)) for workset in collector
            )
        if name not in self._worksets:
            _refuse(
                revit_units.REFUSED_WORKSET,
                "there is no user workset named '{}'".format(name),
            )
        self._set(parameter, self._worksets[name])

    def _write_reference(self, parameter, name):
        if not name:
            self._set(parameter, DB.ElementId.InvalidElementId)
            return
        shown = self._reference_labels(parameter).get(name.lower(), [])
        self._set(
            parameter, self._single_match(shown or self._named(parameter, name), name)
        )

    @staticmethod
    def _single_match(matches, name):
        if not matches:
            _refuse(
                revit_units.REFUSED_REFERENCE,
                "no element named '{}' was found".format(name),
            )
        if len(matches) > 1:
            _refuse(
                revit_units.REFUSED_AMBIGUOUS,
                "more than one element is named '{}'".format(name),
            )
        return matches[0]

    def _named(self, parameter, name):
        sample = self.doc.GetElement(parameter.AsElementId())
        if sample is None:
            sample = self._reference_sample(parameter)
        if sample is not None:
            return self._elements_like(sample).get(name.lower(), [])
        if _is_material_parameter(parameter.Definition):
            materials = DB.FilteredElementCollector(self.doc).OfClass(DB.Material)
            return [
                material.Id
                for material in materials
                if query.get_name(material).lower() == name.lower()
            ]
        _refuse(
            revit_units.REFUSED_REFERENCE,
            "cannot tell which kind of element this empty parameter references",
        )

    def _peers(self, parameter):
        owner = parameter.Element
        if owner is None or owner.Category is None:
            return
        collector = DB.FilteredElementCollector(self.doc).OfCategoryId(
            owner.Category.Id
        )
        if isinstance(owner, DB.ElementType):
            collector = collector.WhereElementIsElementType()
        else:
            collector = collector.WhereElementIsNotElementType()
        for element in collector:
            peer = _same_parameter(element, parameter)
            if peer is not None and peer.StorageType == parameter.StorageType:
                yield peer

    @staticmethod
    def _peer_key(parameter):
        owner = parameter.Element
        category = owner.Category if owner is not None else None
        return (
            get_elementid_value(parameter.Id),
            get_elementid_value(category.Id) if category is not None else None,
            isinstance(owner, DB.ElementType),
        )

    def _integer_labels(self, parameter):
        key = ("integer",) + self._peer_key(parameter)
        if key not in self._labels:
            found = {}
            for peer in self._peers(parameter):
                label = peer.AsValueString() if peer.HasValue else None
                if label:
                    found.setdefault(label.lower(), set()).add(peer.AsInteger())
            self._labels[key] = dict(
                (label, next(iter(values)))
                for label, values in found.items()
                if len(values) == 1
            )
        return self._labels[key]

    def _reference_labels(self, parameter):
        key = ("reference",) + self._peer_key(parameter)
        if key not in self._labels:
            found = {}
            for peer in self._peers(parameter):
                target = peer.AsElementId()
                label = peer.AsValueString()
                if label and target != DB.ElementId.InvalidElementId:
                    targets = found.setdefault(label.lower(), [])
                    if target not in targets:
                        targets.append(target)
            self._labels[key] = found
        return self._labels[key]

    def _reference_sample(self, parameter):
        key = self._peer_key(parameter)
        if key not in self._reference_samples:
            referenced = (
                self.doc.GetElement(peer.AsElementId())
                for peer in self._peers(parameter)
            )
            self._reference_samples[key] = next(
                (element for element in referenced if element is not None), None
            )
        return self._reference_samples[key]

    def _elements_like(self, sample):
        element_class = sample.GetType()
        category = sample.Category
        key = (
            element_class.FullName,
            get_elementid_value(category.Id) if category is not None else None,
        )
        if key not in self._named_elements:
            by_name = {}
            for element in DB.FilteredElementCollector(self.doc).OfClass(element_class):
                if not _in_category(element, category):
                    continue
                for name in _names_of(element):
                    matches = by_name.setdefault(name.lower(), [])
                    if element.Id not in matches:
                        matches.append(element.Id)
            self._named_elements[key] = by_name
        return self._named_elements[key]
