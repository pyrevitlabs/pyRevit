import inspect
import types
import wipeactions

from pyrevit import forms
from pyrevit import script
from pyrevit import revit, DB
from pyrevit import compat


__doc__ = 'This tools helps you to remove extra unnecessary information in '\
          'the model when sending to a contractor or consultant. '\
          'Run the tools and select the categories that you\'d like '\
          'to be removed from the model. Then hit \"Wipe Model\" and '\
          'the process will go through each category and will ' \
          'remove them. You might see some errors or warnings from Revit '\
          '(since this is a very destructive) ' \
          'process but generally they should not crash the script.'


logger = script.get_logger()


class WipeOption:
    def __init__(self, name, wipe_action=None, wipe_args=None):
        self.name = name
        self.wipe_action = wipe_action
        self.wipe_args = wipe_args
        self.is_dependent = getattr(self.wipe_action, 'is_dependent', False)

    def __repr__(self):
        return '<WipeOption Name:{} Action:{}>'\
               .format(self.name, self.wipe_action)


# generate wipe options based on functions in
# wipeactions module
wipe_options = []

for mem in inspect.getmembers(wipeactions):
    moduleobject = mem[1]
    if inspect.isfunction(moduleobject) \
            and hasattr(moduleobject, 'is_wipe_action'):
        if moduleobject.__doc__:
            wipe_options.append(WipeOption(moduleobject.__doc__,
                                           wipe_action=moduleobject))

for wscleaner_func in wipeactions.get_worksetcleaners():
    wipe_options.append(WipeOption(wscleaner_func.docstring,
                                   wipe_action=wscleaner_func.func,
                                   wipe_args=wscleaner_func.args))


# ask user for wipe actions
return_options = \
    forms.SelectFromList.show(
        sorted(wipe_options, key=lambda x: x.name),
        title='Wipe Options',
        width=500,
        button_name='Wipe Model',
        multiselect=True
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
            logger.debug('Calling: {}'.format(wipe_act))
            if wipe_act.wipe_args:
                wipe_act.wipe_action(*wipe_act.wipe_args)
            else:
                wipe_act.wipe_action()
