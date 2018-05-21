"""Unit Tests for pyrevit.forms module."""


__context__ = 'zerodoc'


from pyrevit import forms


def test_forms(forms_func, test_title, filterfuncstr='', *args, **kwargs):
    print('\n\n' + test_title)
    test_title += '({}):'
    ttitle = test_title.format('Single')
    print(ttitle)
    kwargs['title'] = ttitle
    kwargs['multiple'] = False
    print(forms_func(*args, **kwargs))

    ttitle = test_title.format('Multiple')
    print(ttitle)
    kwargs['title'] = ttitle
    kwargs['multiple'] = True
    selection = forms_func(*args, **kwargs)
    if selection:
        print(selection)
    else:
        print('No selection...')

    ttitle = test_title.format('Filter Func')
    print(ttitle)
    kwargs['title'] = ttitle
    kwargs['multiple'] = True
    if 'filterfunc' not in kwargs:
        kwargs['filterfunc'] = lambda x: filterfuncstr in x
    selection = forms_func(*args, **kwargs)
    if selection:
        print(selection)
    else:
        print('No selection...')


test_forms(forms.select_titleblocks,
           test_title='Testing Selecting Titleblocks',
           filterfuncstr='pyRevit')

test_forms(forms.select_open_docs,
           test_title='Testing Selecting Open Docs',
           filterfunc=lambda x: 'pyRevit' in x.Title)

test_forms(forms.select_views,
           test_title='Testing Selecting Views',
           filterfuncstr='pyRevit')

test_forms(forms.select_sheets,
           test_title='Testing Selecting Sheets',
           filterfuncstr='pyRevit')

test_forms(forms.select_revisions,
           test_title='Testing Selecting Revisions',
           filterfuncstr='pyRevit')
