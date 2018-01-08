""" Ready to use FlexForms. Replaces old forms """  #

import sys

from rpw.ui.forms.flexform import FlexForm, Label, ComboBox, TextBox, Button

def SelectFromList(title, options, description=None, sort=True, exit_on_close=True):
    """ Simple FlexForm wrapped function with ComboBox and button

    Args:
        title (str): Title of form
        options (dict,list[str]): Dictionary (string keys) or List[strings]
        description (str): Optional Description of input requested  [default: None]
        sort (bool): Optional sort flag - sorts keys [default: True]
        exit_on_close (bool): Form will call sys.exit() if Closed on X. [default: True]

    Usage:

        >>> from rpw.ui.forms import SelectFromList
        >>> value = SelectFromList('Test Window', ['1','2','3'])
        >>> # Dropdown shows '1', '2' ,'3'. User clicks Select '1'
        >>> print(value)
        '1'
        >>> # Dictionary
        >>> value = SelectFromList('Test Window', {'Text':str, 'Number':int})
        >>> # User clicks Text
        >>> print(value)
        str
    """
    components = []
    if description:
        components.append(Label(description))
    components.append(ComboBox('combobox', options, sort=sort))
    components.append(Button('Select'))
    form = FlexForm(title, components)
    ok = form.show()
    if ok:
        return form.values['combobox']
    if exit_on_close:
        sys.exit()


def TextInput(title, default=None, description=None, sort=True, exit_on_close=True):
    """ Simple FlexForm wrapped function with TextBox and button

    Args:
        title (str): Title of form
        default (str): Optional default value for text box [default: None]
        description (str): Optional Description of input requested  [default: None]
        exit_on_close (bool): Form will call sys.exit() if Closed on X. [default: True]

    Usage:

        >>> from rpw.ui.forms import TextInput
        >>> value = TextInput('Title', default="3")
        >>> print(value)
        3
    """
    components = []
    if description:
        components.append(Label(description))
    if default:
        textbox = TextBox('textbox', default=default)
    else:
        textbox = TextBox('textbox')
    components.append(textbox)
    components.append(Button('Select'))
    form = FlexForm(title, components)
    ok = form.show()
    if ok:
        return form.values['textbox']
    if exit_on_close:
        sys.exit()


if __name__ == '__main__':
    rv = SelectFromList('Title', ['A','B'], description="Your Options",
                            exit_on_close=True)
    print(rv)

    rv = SelectFromList('Title', {'A':5, 'B':10}, description="Your Options",
                            exit_on_close=True)
    print(rv)

    rv = TextInput('Title', default="3", exit_on_close=True)
    print(rv)
    print('forms.py ran')
