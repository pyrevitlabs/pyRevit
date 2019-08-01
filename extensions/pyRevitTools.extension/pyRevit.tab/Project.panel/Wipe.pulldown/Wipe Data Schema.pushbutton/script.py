"""Erase selected data schema and its entities."""

from pyrevit import revit, DB
from pyrevit import forms


class DataSchemaItem(forms.TemplateListItem):
    @property
    def name(self):
        return '{} ({})'.format(self.item.SchemaName, self.item.GUID)


schemas = DB.ExtensibleStorage.Schema.ListSchemas()

sschema = \
    forms.SelectFromList.show([DataSchemaItem(x) for x in schemas],
                              multiselect=False)

if sschema:
    with revit.Transaction("Remove Schema"):
        DB.ExtensibleStorage.Schema.EraseSchemaAndAllEntities(
            schema=sschema,
            overrideWriteAccessWithUserPermission=True
            )
