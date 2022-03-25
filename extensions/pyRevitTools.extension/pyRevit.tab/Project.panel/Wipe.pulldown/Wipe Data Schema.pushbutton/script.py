"""Erase selected data schema and its entities."""

from pyrevit import revit, DB
from pyrevit import forms, HOST_APP

doc = revit.doc

class DataSchemaItem(forms.TemplateListItem):
    @property
    def name(self):
        return '{} ({})'.format(self.item.SchemaName, self.item.GUID)


schemas = DB.ExtensibleStorage.Schema.ListSchemas()

sschema = \
    forms.SelectFromList.show([DataSchemaItem(x) for x in schemas],
                              multiselect=True)

if sschema:
    for i in sschema:
        with revit.Transaction("Remove Schema"):
            if HOST_APP.version > 2020:
                try:
                    DB.ExtensibleStorage.Schema.EraseSchemaAndAllEntities(
                    schema=i,
                    overrideWriteAccessWithUserPermission=True
                    )
                except Exception as e:
                    print(e)
            else:
                try:
                    doc.EraseSchemaAndAllEntities(i)
                except Exception as e:
                    print(e)