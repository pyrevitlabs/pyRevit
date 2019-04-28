"""Copy selected view templates to other open models."""
#pylint: disable=import-error,invalid-name
from pyrevit import revit
from pyrevit import forms


selected_viewtemplates = forms.select_viewtemplates(doc=revit.doc)
if selected_viewtemplates:
    dest_docs = forms.select_open_docs(title='Select Destination Documents')
    if dest_docs:
        for ddoc in dest_docs:
            with revit.Transaction('Copy View Templates', doc=ddoc):
                revit.create.copy_viewtemplates(
                    selected_viewtemplates,
                    src_doc=revit.doc,
                    dest_doc=ddoc
                    )
