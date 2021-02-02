"Erase selected BIM360 collaboration cache"
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit.revit import bim360
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


class CacheModelItem(forms.TemplateListItem):
    """SelectFromList wrapper item"""
    def __init__(self, item, linked=False):
        super(CacheModelItem, self).__init__(item)
        self.linked = linked

    @property
    def name(self):
        """Item name"""
        return '{} [ Revit: {} ]{}'.format(
            self.item.project,
            self.item.product,
            ' [ Linked ]' if self.linked else ''
            )


cmodels = []
# grab collab caches
for cc in bim360.get_collab_caches():
    # add models
    cmodels.extend(
        [CacheModelItem(x) for x in cc.cache_models]
        )
    # and linked models
    cmodels.extend(
        [CacheModelItem(x, linked=True) for x in cc.cache_linked_models]
        )

# ask user for which model to delete
selected_cmodels = forms.SelectFromList.show(cmodels, multiselect=True)
if selected_cmodels:
    # delete each selected cache
    for cm in selected_cmodels:
        logger.info('Deleting %s', cm)
        bim360.clear_model_cache(cm)
