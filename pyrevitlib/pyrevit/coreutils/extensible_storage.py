# -*- coding: utf-8 -*-
"""Generic Extensible Storage helper.

Extensible Storage lets a tool attach small bits of typed data to any
Element and have Revit persist it as part of the model. Used directly,
that means writing SchemaBuilder/Entity boilerplate -- a GUID, field
types, access levels, generic Get[T]/Set[T] calls -- every time a tool
needs to remember something about an element. This module wraps that
boilerplate behind two things:

    * BaseSchema -- a plain class a tool subclasses to *declare* its
      schema (GUID, name, vendor id, fields) instead of building one
      by hand.
    * ElementDataStorage -- reads/writes/clears an element's Entity for
      a given schema as a plain dict, so callers never touch
      SchemaBuilder, Entity, or Get[T]/Set[T] directly.

Only "simple" fields (a single value per field -- str, int, float,
bool, DB.ElementId, System.Guid, etc.) are covered directly. A schema
that also needs SchemaBuilder.AddArrayField / AddMapField can add them
via the BaseSchema.extend_builder hook (see below).

Example:

    from pyrevit import DB
    from pyrevit.coreutils import extensible_storage

    class MyToolLinkSchema(extensible_storage.BaseSchema):
        guid = "a1b2c3d4-e5f6-4a7b-8c9d-0123456789ab"
        schema_name = "MyToolElementLink"
        vendor_id = "mytool"
        fields = {"LinkedId": DB.ElementId}

    storage = extensible_storage.ElementDataStorage(MyToolLinkSchema)

    with revit.Transaction("Link elements"):
        storage.set_data(some_element, LinkedId=other_element.Id)

    data = storage.get_data(some_element)
    if data:
        linked_id = data["LinkedId"]
"""

from pyrevit import DB
from pyrevit.framework import Guid


class BaseSchema(object):
    """Subclass to declaratively define an Extensible Storage schema.

    Class attributes:
        guid (str): fixed schema GUID as a string. Generate a fresh
            one per schema and never change it once the schema is in use)
        schema_name (str): schema name (letters/digits/underscore,
            must start with a letter)
        vendor_id (str): short vendor/application id required by
            SchemaBuilder.SetVendorId -- any short alphanumeric string
            is accepted, Revit does not validate it against a registry
        application_guid (str or None): optional -- only needed to
            further scope AccessLevel.Application/Vendor reads
        read_access_level / write_access_level
            (DB.ExtensibleStorage.AccessLevel): default Public
            (readable/writable by any application, not just the one
            that wrote it)
        fields (dict): {field_name: field_type}, e.g.
            {"LinkedId": DB.ElementId, "Note": str}. Only simple
            (non-array, non-map) fields are supported directly -- see
            extend_builder() for anything beyond that.
        documentation (str or None): optional overall schema doc string
    """

    guid = None
    schema_name = None
    vendor_id = "pyrvt"
    application_guid = None
    read_access_level = DB.ExtensibleStorage.AccessLevel.Public
    write_access_level = DB.ExtensibleStorage.AccessLevel.Public
    fields = None
    documentation = None

    @classmethod
    def extend_builder(cls, builder):
        """Override to add anything SchemaBuilder supports beyond
        simple fields -- e.g. builder.AddArrayField(...) or
        builder.AddMapField(...) -- before the schema is finished.
        Called once, right before Finish(), only when the schema is
        being newly registered. No-op by default.

        Args:
            builder: DB.ExtensibleStorage.SchemaBuilder being built
        """
        pass


class ElementDataStorage(object):
    """Reads/writes/clears one element's Entity for a given
    `BaseSchema` subclass, as a plain dict of field name -> value.
    """

    def __init__(self, schema_cls):
        """
        Args:
            schema_cls: a BaseSchema subclass describing the schema to
                read/write
        """
        if not schema_cls.guid or not schema_cls.schema_name:
            raise ValueError(
                "{0} must define both 'guid' and 'schema_name'".format(
                    schema_cls.__name__
                )
            )
        if not schema_cls.fields:
            raise ValueError(
                "{0} must define at least one field".format(schema_cls.__name__)
            )
        self._schema_cls = schema_cls
        self._schema = None

    @property
    def schema(self):
        """DB.ExtensibleStorage.Schema: the registered schema, built
        and registered on first access if not already present in this
        document/session."""
        if self._schema is None:
            self._schema = self._get_or_create_schema()
        return self._schema

    def has_data(self, element):
        """bool: whether `element` currently has an Entity for this
        schema."""
        schema = self._lookup_schema()
        if schema is None:
            return False
        entity = element.GetEntity(schema)
        return entity is not None and entity.IsValid()

    def get_data(self, element):
        """Read this schema's data off `element`.

        Args:
            element: DB.Element to read from

        Returns:
            dict: {field_name: value} for every field declared on the
                schema (default-valued for any field never explicitly
                set), or None if `element` has no Entity for this
                schema -- including if the schema has never been
                written anywhere in this document at all
        """
        schema = self._lookup_schema()
        if schema is None:
            return None

        entity = element.GetEntity(schema)
        if not entity.IsValid():
            return None

        data = {}
        for field_name, field_type in self._schema_cls.fields.items():
            data[field_name] = entity.Get[field_type](field_name)
        return data

    def set_data(self, element, **field_values):
        """Write (or overwrite) this schema's Entity on `element`.

        This replaces the whole Entity, not just the fields passed --
        any declared field you don't pass reverts to its CLR default
        (0 / empty string / InvalidElementId, depending on type) rather
        than keeping whatever was there before. Pass every field you
        care about each time.

        Args:
            element: DB.Element to write to
            **field_values: value for each field name declared in the
                schema's `fields`; passing a name that isn't a declared
                field raises KeyError

        Must be called inside an open transaction.
        """
        for field_name in field_values:
            if field_name not in self._schema_cls.fields:
                raise KeyError(
                    "'{0}' is not a field on schema '{1}'".format(
                        field_name, self._schema_cls.schema_name
                    )
                )

        entity = DB.ExtensibleStorage.Entity(self.schema)
        for field_name, field_type in self._schema_cls.fields.items():
            if field_name in field_values:
                entity.Set[field_type](field_name, field_values[field_name])
        element.SetEntity(entity)

    def clear_data(self, element):
        """Remove this schema's Entity from `element`, if present.

        Args:
            element: DB.Element to clear

        Must be called inside an open transaction.
        """
        schema = self._lookup_schema()
        if schema is None:
            return
        element.DeleteEntity(schema)

    def _lookup_schema(self):
        """Look up the schema without registering it if it isn't
        already known -- used by every read path (get_data/has_data/
        clear_data) so reading a document that has never had this
        schema written to it doesn't spuriously register an unused
        schema in the session.

        Returns:
            DB.ExtensibleStorage.Schema or None
        """
        return DB.ExtensibleStorage.Schema.Lookup(Guid(self._schema_cls.guid))

    def _get_or_create_schema(self):
        existing = self._lookup_schema()
        if existing is not None:
            return existing

        schema_guid = Guid(self._schema_cls.guid)
        builder = DB.ExtensibleStorage.SchemaBuilder(schema_guid)
        builder.SetSchemaName(self._schema_cls.schema_name)
        builder.SetVendorId(self._schema_cls.vendor_id)
        if self._schema_cls.application_guid:
            builder.SetApplicationGUID(Guid(self._schema_cls.application_guid))
        builder.SetReadAccessLevel(self._schema_cls.read_access_level)
        builder.SetWriteAccessLevel(self._schema_cls.write_access_level)
        if self._schema_cls.documentation:
            builder.SetDocumentation(self._schema_cls.documentation)
        for field_name, field_type in self._schema_cls.fields.items():
            builder.AddSimpleField(field_name, field_type)
        self._schema_cls.extend_builder(builder)
        return builder.Finish()
