import inspect
import pyrevittoolslib.wipeactions

from pyrevit import forms
from pyrevit import script


__doc__ = 'This tools helps you to remove extra unnecessary information in '\
          'the model when sending to a contractor or consultant. '\
          'Run the tools and select the categories that you\'d like '\
          'to be removed from the model. Then hit \"Wipe Model\" and '\
          'the process will go through each category and will ' \
          'remove them. You might see some errors or warnings from Revit '\
          '(since this is a very distructive) ' \
          'process but generally they should not crash the script.'


logger = script.get_logger()


class WipeOption:
    def __init__(self, name, default_state=False, wipe_action=None):
        self.name = name
        self.state = default_state
        self.wipe_action = wipe_action
        self.is_dependent = self.wipe_action.is_dependent

    def __repr__(self):
        return '<WipeOption Name:{} State:{} Action:{}>'\
               .format(self.name, self.state, self.wipe_action)

    def __bool__(self):
        return self.state

    def __nonzero__(self):
        return self.state


# generate wipe options based on functions in
# pyrevittoolslib.wipeactions module
wipe_options = []

for mem in inspect.getmembers(pyrevittoolslib.wipeactions):
    moduleobject = mem[1]
    if inspect.isfunction(moduleobject):
        if moduleobject.__doc__:
            wipe_options.append(WipeOption(moduleobject.__doc__,
                                           wipe_action=moduleobject))

# generate wipe options based on model worksets
for wscleaner_func in pyrevittoolslib.wipeactions.get_worksetcleaners():
    if wscleaner_func.__doc__:
        wipe_options.append(WipeOption(wscleaner_func.__doc__,
                                       wipe_action=wscleaner_func))


# ask user for wipe actions
return_options = \
    forms.SelectFromCheckBoxes.show(
        sorted(wipe_options, key=lambda x: x.name),
        title='Wipe Options',
        width=500,
        button_name='Wipe Model'
        )

if return_options:
    dependent_actions = [wipe_act
                         for wipe_act in return_options
                         if wipe_act.is_dependent]

    not_dependent_actions = [wipe_act
                             for wipe_act in return_options
                             if not wipe_act.is_dependent]

    for actions in [dependent_actions, not_dependent_actions]:
        for wipe_act in actions:
            if wipe_act:
                logger.debug('Calling: {}'.format(wipe_act))
                wipe_act.wipe_action()
