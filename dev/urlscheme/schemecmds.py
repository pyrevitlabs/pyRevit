from pyrevit import framework
from pyrevit import revit, DB, UI
from pyrevit.output.urlscheme import baseunivcmd
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


DEFAULT_LINK = '<a title="Click to select or show element" ' \
               'style="background-color: #f5f7f2; ' \
               'font-size:8pt; ' \
               'color: #649417; ' \
               'border: 1px solid #649417; ' \
               'border-radius:3px; ' \
               'vertical-align:middle; '\
               'margin:-4,0,-4,0; ' \
               'margin: 2px; ' \
               'padding: 1px 4px; ' \
               'text-align: center; ' \
               'text-decoration: none; ' \
               'display: inline-block;" href="{}{}">{}</a>'


class SelectElementsCommand(baseunivcmd.GenericUniversalCommand):
    type_id = 'select'

    def get_elements(self):
        return [arg.IntegerValue for arg in self._args
                if isinstance(arg, DB.ElementId)]

    def make_command_url(self):
        return DEFAULT_LINK.format(baseunivcmd.SCHEME_PREFIX,
                                   self.url_data.replace('\"', '\''),
                                   self.url_title)

    def execute(self):
        el_list = framework.List[DB.ElementId]()
        for arg in self._args:
            if type(arg) == int:
                el_list.Add(DB.ElementId(arg))

        if not revit.doc:
            UI.TaskDialog.Show('pyRevit', 'doc error')
            logger.debug('Active document does not exist in Revit. '
                         'Can not get doc and uidoc.')
        else:
            revit.uidoc.Selection.SetElementIds(el_list)

            for ei_id in el_list:
                try:
                    el = revit.doc.GetElement(ei_id)
                    if isinstance(el, DB.View):
                        revit.uidoc.ActiveView = el
                    else:
                        owner_view = revit.doc.GetElement(el.OwnerViewId)
                        if owner_view:
                            revit.uidoc.ActiveView = owner_view
                except Exception as err:
                    print(err)
