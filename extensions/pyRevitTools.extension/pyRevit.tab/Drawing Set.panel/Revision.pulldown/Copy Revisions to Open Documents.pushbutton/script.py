"""Copy revisions to other open models."""

from pyrevit import revit, DB
from pyrevit import forms


__doc__ = 'Copy selected revisions from current model ' \
          'to selected open models.'


selected_revisions = forms.select_revisions(button_name='Select Revision',
                                            multiple=True)
if selected_revisions:
    dest_docs = forms.select_open_docs(title='Select Destination Documents')
    if dest_docs:
        for ddoc in dest_docs:
            with revit.Transaction('Copy Revisions', doc=ddoc):
                revit.create.copy_revisions(
                    selected_revisions,
                    src_doc=revit.doc,
                    dest_doc=ddoc
                    )
