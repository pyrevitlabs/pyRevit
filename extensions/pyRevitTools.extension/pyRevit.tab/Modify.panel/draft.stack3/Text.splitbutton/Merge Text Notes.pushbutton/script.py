"""Merges the selected text note elements into one."""

from pyrevit import revit


selection = revit.get_selection()

with revit.Transaction('Merge Text Notes'):
    tnotes = sorted(selection, key=lambda txnote: 0 - txnote.Coord.Y)

    mtxt = tnotes[0]
    mtxtwidth = mtxt.Width
    for txt in tnotes[1:]:
        if txt.Text[0] == ' ':
            mtxt.Text = mtxt.Text + txt.Text
        else:
            mtxt.Text = mtxt.Text + ' ' + txt.Text
        revit.doc.Delete(txt.Id)

    mtxt.Width = mtxtwidth
