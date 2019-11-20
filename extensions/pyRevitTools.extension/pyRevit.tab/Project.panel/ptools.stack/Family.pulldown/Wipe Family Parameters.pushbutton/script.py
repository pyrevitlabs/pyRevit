"""This script removes all custom parameters that has not been used
in dimensions as labels and also resets the value for the other
parameters to zero or null."""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


output = script.get_output()
logger = script.get_logger()


# make sure user has saved open models in case the tool crashes
if not forms.alert('Make sure your models are saved and synced. '
                   'Hit OK to continue...', cancel=True):
    script.exit()

# ensure active document is a family document
forms.check_familydoc(revit.doc, exitscript=True)

def reset_param(family_param, reset_message):
    try:
        # reset formula
        if family_param.CanAssignFormula:
            revit.doc.FamilyManager.SetFormula(family_param, None)
            reset_message += '\n\tFormula set to none'
        # reset value
        if family_param.StorageType == DB.StorageType.Integer \
                or family_param.StorageType == DB.StorageType.Double:
            revit.doc.FamilyManager.Set(family_param, 0)
            reset_message += '\n\tValue set to 0'
        elif family_param.StorageType == DB.StorageType.String:
            revit.doc.FamilyManager.Set(family_param, '')
            reset_message += '\n\tValue set to empty string'
    except Exception as e:
        reset_message += '\n\tFailed reset. | %s' % str(e)
    return reset_message


if __name__ == '__main__':
    # get parameters to purge
    family_params = forms.select_family_parameters(revit.doc)
    if family_params:
        # now purge
        max_progress = len(family_params)
        with revit.Transaction('Remove all family parameters'):
            for idx, param in enumerate(family_params):
                logger.debug('%s, %s', param.Id, param.Definition)
                output.update_progress(idx + 1, max_progress)
                # if builtin, reset values and skip delete
                if param.Id.IntegerValue < 0:
                    message = \
                        'Can not delete builtin "%s"' % param.Definition.Name
                    logger.warning(reset_param(param, message))
                    continue
                # otherwise delete
                try:
                    print('Removing "{}" ({})'.format(
                        param.Definition.Name, param.Id))
                    revit.doc.FamilyManager.RemoveParameter(param)
                except Exception:
                    # if delete error, reset values and skip delete
                    message = 'Can not delete "%s"' % param.Definition.Name
                    logger.error(reset_param(param, message))
