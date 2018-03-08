"""Erase selected data schema and its entities."""

from pyrevit import revit, DB
from pyrevit import forms


class DataSchemaItem(object):
    def __init__(self, orig_item):
        self.item = orig_item

    def __str__(self):
        return '{} ({})'.format(self.item.SchemaName, self.item.GUID)

    def unwrap(self):
        return self.item


schemas = DB.ExtensibleStorage.Schema.ListSchemas()

selected_schemas = \
    forms.SelectFromList.show([DataSchemaItem(x) for x in schemas],
                              multiselect=False)

if selected_schemas:
    sschema = selected_schemas[0]
    with revit.Transaction("Remove Schema"):
        DB.ExtensibleStorage.Schema.EraseSchemaAndAllEntities(
            sschema.unwrap(),
            True
            )
