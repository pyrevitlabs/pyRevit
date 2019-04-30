"""Import parameter definitions from yaml file and create in current family.

Parameter definition file is expected to be a yaml file,
providing info about the parameters to be created.
The schema for the parameter definition is shown below:

<parameter-name>:
	type: <Autodesk.Revit.DB.ParameterType>
	category: <Autodesk.Revit.DB.BuiltInParameterGroup>
	instance: <true|false>

Example:

Shelf (Upper):
	type: YesNo
	category: PG_CONSTRUCTION
	instance: false
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

from winterops import yaml


__author__ = "{{author}}"


logger = script.get_logger()
output = script.get_output()


DEFAULT_TYPE = 'Text'
DEFAULT_BIP_CATEGORY = 'PG_CONSTRUCTION'


def create_param(param_name, param_opts):
    """Create family parameter based on name and options."""
    fm = revit.doc.FamilyManager
    if param_name and param_opts:
        logger.debug('creating: %s', param_name)

        # extract configured values
        param_bip_cat = coreutils.get_enum_value(
            DB.BuiltInParameterGroup,
            param_opts.get('category', DEFAULT_BIP_CATEGORY)
            )
        param_type = coreutils.get_enum_value(
            DB.ParameterType,
            param_opts.get('type', DEFAULT_TYPE)
            )
        param_isinst = param_opts.get('instance', 'false').lower() == 'true'
        # TODO: extratc default value from configs
        # param_value = param_opts.get('value', None)

        # create param in family doc
        if not param_bip_cat:
            logger.critical(
                'can not determine parameter category for %s', param_name
                )
            return
        elif not param_type:
            logger.critical(
                'can not determine parameter type', param_name
                )
            return

        logger.debug('%s %s %s', param_bip_cat, param_type, param_isinst)
        # fparam = fm.AddParameter(
        fm.AddParameter(
            param_name,
            param_bip_cat,
            param_type,
            param_isinst
        )

        # set value
        # TODO: needs value checking and correct setting based on param_type
        # if param_value:
        #     fm.Set(fparam, param_value)


def get_param_def_file():
    """Get parameter definition yaml file from user."""
    return forms.pick_file(file_ext='yaml')


def load_params(parma_file):
    """Load contents of yaml file into an ordered dict."""
    return yaml.load_as_dict(parma_file)


if __name__ == '__main__':
    forms.check_familydoc(exitscript=True)

    pfile = get_param_def_file()
    paramdefs = load_params(pfile)
    with revit.Transaction('Import Params from Config'):
        for pname, popts in paramdefs.items():
            create_param(pname, popts)
