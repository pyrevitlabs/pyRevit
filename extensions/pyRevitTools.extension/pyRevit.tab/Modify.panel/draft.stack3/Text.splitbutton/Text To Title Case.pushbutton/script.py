"""Capitalizes the first letter of the selected text note."""

from revitutils import doc, selection, Action


def get_first_alpha_index(src_string):
    for idx, char in enumerate(src_string):
        if char.isalpha():
            return idx

    return None

with Action('to Sentence case'):
    for el in selection.elements:
        new_sentence = ''
        for word in unicode(el.Text).split():
            idx = get_first_alpha_index(word)
            if idx is not None:
                new_sentence += ' ' + word[:idx].lower() + word[idx].upper() + word[idx+1:].lower()

        el.Text = new_sentence
