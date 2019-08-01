"""Provides options for overriding Visibility/Graphics on selected elements."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


__context__ = 'OST_TextNotes'


selection = revit.get_selection()


def merge_paragraphs():
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


def merge_texts():
    with revit.Transaction('Merge Text Notes'):
        tnotes = sorted(selection, key=lambda txnote: 0 - txnote.Coord.Y)

        if len(tnotes) > 1:
            mtxt = tnotes[0]
            mtxtwidth = mtxt.Width
            for txt in tnotes[1:]:
                if txt.Text[0] == ' ':
                    mtxt.Text = mtxt.Text + txt.Text
                else:
                    mtxt.Text = mtxt.Text + ' ' + txt.Text
                revit.doc.Delete(txt.Id)

            mtxt.Width = mtxtwidth


def remove_return():
    with revit.Transaction('Merge Single-Line Text'):
        for el in selection.elements:
            el.Text = str(el.Text).replace('\r', ' ')


def text_tolower():
    with revit.Transaction('to Lower'):
        for el in selection.elements:
            el.Text = el.Text.lower()


def get_first_alpha_index(src_string):
    for idx, char in enumerate(src_string):
        if char.isalpha():
            return idx

    return None


def text_totitle():
    with revit.Transaction('to Sentence case'):
        for el in selection.elements:
            new_sentence = ''
            for word in unicode(el.Text).split():
                idx = get_first_alpha_index(word)
                if idx is not None:
                    new_sentence += ' ' \
                                    + word[:idx].lower() \
                                    + word[idx].upper() \
                                    + word[idx+1:].lower()

            el.Text = new_sentence


def text_toupper():
    with revit.Transaction('to Upper'):
        for el in selection.elements:
            el.Text = el.Text.upper()


options = {'Merge': merge_texts,
           'Merge Paragraphs': merge_paragraphs,
           'Remove Returns': remove_return,
           'Text To Lower': text_tolower,
           'Text To Upper': text_toupper,
           'Text To Title Case': text_totitle}


selected_switch = \
    forms.CommandSwitchWindow.show(
        sorted(options.keys()),
        message='Pick text override option:'
        )

if selected_switch:
    options[selected_switch]()
