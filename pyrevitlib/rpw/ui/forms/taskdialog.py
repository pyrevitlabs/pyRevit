""" TaskDialogs Wrappers"""  #

import sys
from rpw import UI
from rpw.exceptions import RpwValueError
from rpw.base import BaseObjectWrapper, BaseObject

class Alert():
    """
    A Simple Revit TaskDialog for displaying quick messages

    Usage:
        >>> from rpw.ui.forms import Alert
        >>> Alert('Your Message', title="Title", header="Header Text")
        >>> Alert('You need to select Something', exit=True)

    Args:
        message (str): TaskDialog Content
        title (str, optional): TaskDialog Title
        header (str, optional): TaskDialog content header
        exit (bool, optional): Exit Script after Dialog.
            Useful for displayin Errors. Default is False

    """
    def __init__(self, content, title='Alert', header='', exit=False):
        dialog = UI.TaskDialog(title)
        dialog.TitleAutoPrefix = False
        dialog.MainInstruction = header
        dialog.MainContent = content
        self.result = dialog.Show()

        if exit:
            sys.exit(1)

class CommandLink(BaseObject):
    """
    Command Link Helper Class

    Usage:
        >>> from rpw.ui.forms import CommandLink, TaskDialog
        >>> CommandLink('Open Dialog', return_value=func_to_open)
        >>> TaskDialog('Title', commands=[CommandLink])

    Args:
        text (str): Command Text
        subtext (str, optional): Button Subtext
        return_value (any, optional): Value returned if button is clicked.
            If none is provided, text is returned.

    """
    def __init__(self, text, subtext='', return_value=None):
        self._id = None  # This will later be set to TaskDialogCommandLinkId(n)
        self.text = text
        self.subtext = subtext
        self.return_value = return_value if return_value is not None else text

    def __repr__(self):
        return super(CommandLink, self).__repr__(data={'id': self._id,
                                                       'text':self.text})


class TaskDialog(BaseObjectWrapper):
    """
    Task Dialog Wrapper

    >>> from rpw.ui.forms import CommandLink, TaskDialog
    >>> commands= [CommandLink('Open Dialog', return_value='Open'),
    >>> ...           CommandLink('Command', return_value=lambda: True)]
    >>> ...
    >>> dialog = TaskDialog('This TaskDialog has Buttons ',
    >>> ...                 title_prefix=False,
    >>> ...                 content="Further Instructions",
    >>> ...                 commands=commands,
    >>> ...                 buttons=['Cancel', 'OK', 'RETRY'],
    >>> ...                 footer='It has a footer',
    >>> ...                 # verification_text='Add Verification Checkbox',
    >>> ...                 # expanded_content='Add Expanded Content',
    >>> ...                 show_close=True)
    >>> dialog.show()
    'Open'

    Wrapped Element:
        self._revit_object = `Revit.UI.TaskDialog`

    Args:
        content (str): Main text of TaskDialog.
        commands (list, optional): List of CommandLink Instances.
            Default is no buttons.
        buttons (list, optional): List of TaskDialogCommonButtons names.
            Default is no buttons. 'Close' is shown if no commands are passed.
        title (str, optional): Title of TaskDialog. Default is 'Task Dialog'.p
        instruction (str, optional): Main Instruction.
        footer (str, optional): Footer Text. Default is ``blank``.
        expanded_content (str, optional): Expandable Text. Default is ``blank``.
        verification_text (str, optional): Checkbox text. Default is ``blank``.
        title_prefix (bool, optional): Prefix Title with app name.
            Default is ``False``
        show_close (bool, optional): Show X to close. Default is False.

    """
    _revit_object_class = UI.TaskDialog
    _common_buttons = ['Ok', 'Yes', 'No', 'Cancel', 'Retry', 'Close']

    def __init__(self, instruction, commands=None, buttons=None,
                 title='Task Dialog', content='',
                 title_prefix=False, show_close=False,
                 footer='', expanded_content='', verification_text=''
                 ):

        super(TaskDialog, self).__init__(UI.TaskDialog(title))
        self.dialog = self._revit_object

        # Settings
        self.dialog.TitleAutoPrefix = title_prefix
        self.dialog.AllowCancellation = show_close

        # Properties
        self.dialog.Title = title
        self.dialog.MainInstruction = instruction
        self.dialog.MainContent = content
        self.dialog.FooterText = footer
        self.dialog.ExpandedContent = expanded_content
        self.dialog.VerificationText = verification_text
        self.verification_checked = None if not verification_text else False

        # Add Buttons
        self.buttons = buttons or []
        common_buttons_names = []
        for button_name in [b.capitalize() for b in self.buttons]:
            if button_name not in self._common_buttons:
                raise RpwValueError('TaskDialogCommonButtons member', button_name)
            button_full_name = 'UI.TaskDialogCommonButtons.' + button_name
            common_buttons_names.append(button_full_name)

        if common_buttons_names:
            common_buttons = eval('|'.join(common_buttons_names))
            self.dialog.CommonButtons = common_buttons

        # Set Default Button
        self.dialog.DefaultButton = UI.TaskDialogResult["None"]

        # Validate Commands
        commands = commands or []
        if len(commands) > 4:
            raise RpwValueError('4 or less command links', len(commands))

        # Process Commands
        self.commands = {}
        for link_index, command_link in enumerate(commands, 1):
            command_id = 'CommandLink{}'.format(link_index)
            command_link._id = getattr(UI.TaskDialogCommandLinkId, command_id)
            self.commands[command_id] = command_link
            self.dialog.AddCommandLink(command_link._id,
                                       command_link.text,
                                       command_link.subtext)

    def show(self, exit=False):
        """
        Show TaskDialog

        Args:
            exit (bool, optional): Exit Script after Dialog. Useful for
                displaying Errors. Default is False.

        Returns:
            Returns is ``False`` if dialog is Cancelled (X or Cancel button).
            If CommandLink button is clicked, ``CommandLink.return_value``
            is returned - if one was not provided, ``CommandLink.text`` is used.
            If CommonButtons are clicked ``TaskDialog.TaskDialogResult`` name is
            returned ie('Close', 'Retry', 'Yes', etc).
        """
        self.result = self.dialog.Show()

        try:
            self.verification_checked = self.dialog.WasVerificationChecked()
        except:
            self.verification_checked = None

        # Handle Cancel
        if self.result == UI.TaskDialogResult.Cancel:
            if exit:
                sys.exit(1)
            return None

        # If result is a CommandLink, return Return Value else Result
        command_link = self.commands.get(str(self.result))
        if command_link:
            return command_link.return_value
        else:
            return self.result.ToString()



if __name__ == '__main__':
    Alert('Test Alert!')

    def sample_callback():
        print('Calling B')
        d = UI.TaskDialog("Revit Build Information")
        d.MainInstruction = "Button 1"
        d.Show()


    from rpw.ui.forms.taskdialog import *
    commands = [
                CommandLink('TestTitle', return_value=sample_callback, subtext='test subtext'),
                CommandLink('TestTitle2', return_value=lambda: 'Empty', subtext='test subtext2')
                ]

    t = TaskDialog(commands=commands, buttons=['Yes'])
