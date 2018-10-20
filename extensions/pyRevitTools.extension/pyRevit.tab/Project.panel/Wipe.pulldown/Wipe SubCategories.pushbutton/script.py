"""Reset all model categories and subcategories back to default."""
#pylint: disable=E0401,C0103
from pyrevit import revit
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


class SubCategoryOption(forms.TemplateListItem):
    def __init__(self, subcategory):
        super(SubCategoryOption, self).__init__(subcategory)

    @property
    def name(self):
        return '{} --> {}'.format(self.item.Parent.Name, self.item.Name)


if forms.alert('This tool is very destructive. It resets all '
               'the element subcategories (what is shown in Object Styles '
               'panel) inside this model, effectively resetting all line '
               'styles and all other subcategory of any families imported '
               'in the model. Proceed only if you know what you are doing!\n\n'
               'Are you sure you want to proceed?', yes=True, no=True):
    subcats = revit.query.get_subcategories(doc=revit.doc, purgable=True)
    subcats_to_delete = \
        forms.SelectFromList.show([SubCategoryOption(x) for x in subcats],
                                  title='Select SubCategories to Purge',
                                  button_name='Purge',
                                  multiselect=True,
                                  checked_only=True)
    if subcats_to_delete \
            and forms.alert('Are you sure?', yes=True, no=True):
        with revit.Transaction('Reset SubCategories'):
            revit.delete.delete_elements(subcats_to_delete)
            del subcats_to_delete
