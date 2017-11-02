from pyrevit import revit


__doc__ = 'Removes the space and newlines between paragraphs '\
          'in the selected text note element.'


selection = revit.get_selection()

with revit.Transaction('Merge Paragraphs'):
    tnotes = sorted(selection, key=lambda txnote: 0 - txnote.Coord.Y)

    if len(tnotes) > 1:
        mtxt = tnotes[0]
        mtxtwidth = mtxt.Width
        for txt in tnotes[1:]:
            if txt.Text[0] == '\r\n\r\n':
                mtxt.Text = mtxt.Text + txt.Text
            else:
                mtxt.Text = mtxt.Text + '\r\n\r\n' + txt.Text
            revit.doc.Delete(txt.Id)

        mtxt.Width = mtxtwidth
