"""Unit Tests for pyrevit.forms module."""
#pylint: disable=E0401
from pyrevit import script
from pyrevit import forms


__context__ = 'zero-doc'


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
        kwargs['filterfunc'] = lambda x: filterfuncstr in str(x)
    selection = forms_func(*args, **kwargs)
    if selection:
        print(selection)
    else:
        print('No selection...')


print(
    forms.ask_for_string(
        default='test default',
        prompt='test prompt',
        title='test title'
    ))


print(
    forms.ask_for_one_item(
        ['test item 1', 'test item 2', 'test item 3'],
        default='test item 2',
        prompt='test prompt',
        title='test title'
    ))


print(
    forms.ask_for_date(
        default='2018/11/09',
        prompt='test prompt',
        title='test title'
    ))


print(
    forms.select_swatch(
        title='test title',
        button_name='Test button name'
    ))


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

print(
    forms.SelectFromList.show(
        {'All': '1 2 3 4 5 6 7 8 9 0'.split(),
         'Odd': '1 3 5 7 9'.split(),
         'Even': '2 4 6 8 0'.split()},
        title='MultiGroup List',
        group_selector_title='Select Integer Range:',
        multiselect=True
    ))


print(
    forms.select_image(script.get_bundle_files('images/'))
    )
