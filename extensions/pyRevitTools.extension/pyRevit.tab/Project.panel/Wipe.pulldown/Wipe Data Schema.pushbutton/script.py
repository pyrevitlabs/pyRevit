"""Erase selected data schema and its entities."""

from pyrevit import revit, DB
from pyrevit import forms

doc = revit.doc

class DataSchemaItem(forms.TemplateListItem):
    @property
    def name(self):
        return '{} ({})'.format(self.item.SchemaName, self.item.GUID)


schemas = DB.ExtensibleStorage.Schema.ListSchemas()

sschemas = \
    forms.SelectFromList.show([DataSchemaItem(x) for x in schemas],
                              multiselect=True) or []

for sschema in sschemas:
    with revit.Transaction("Remove Schema"):
        try:
            doc.EraseSchemaAndAllEntities(sschema)
        except Exception as e:
            print(e)
