"""Export family configurations to yaml file.

Family configuration file is a yaml file,
providing info about the parameters and types defined in the family.

The structure of this config file is as shown below:

parameters:
	<parameter-name>:
		type: <Autodesk.Revit.DB.ParameterType>
		category: <Autodesk.Revit.DB.BuiltInParameterGroup>
		instance: <true|false>
		formula: <str>
types:
	<type-name>:
		<parameter-name>: <value>
		<parameter-name>: <value>
		...


Example:

parameters:
	Shelf Height (Upper):
		type: Length
		category: PG_GEOMETRY
		instance: false
types:
	24D"x36H":
		Shelf Height (Upper): 3'-0"
"""
#pylint: disable=import-error,invalid-name,broad-except
# TODO: fix parameter ordering
# TODO: export defautl param values

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

from winterops import yaml


__author__ = "{{author}}"


logger = script.get_logger()
output = script.get_output()


PARAM_SECTION_NAME = 'parameters'
PARAM_SECTION_TYPE = 'type'
PARAM_SECTION_CAT = 'category'
PARAM_SECTION_INST = 'instance'
PARAM_SECTION_FORMULA = 'formula'

TYPES_SECTION_NAME = 'types'


FAMILY_SYMBOL_FORMAT = '{} : {}'


def get_symbol_name(symbol_id):
    for fsym in DB.FilteredElementCollector(revit.doc)\
                  .OfClass(DB.FamilySymbol)\
                  .ToElements():
        if fsym.Id == symbol_id:
            return FAMILY_SYMBOL_FORMAT.format(
                revit.query.get_name(fsym.Family),
                revit.query.get_name(fsym)
            )


def include_type_configs(cfgs_dict, fparams):
    fm = revit.doc.FamilyManager

    # grab param values for types
    for ftype in fm.Types:
        type_config = {}
        for fparam in fparams:
            fparam_name = fparam.Definition.Name
            fparam_value = None
            if fparam.StorageType == DB.StorageType.ElementId \
                    and fparam.Definition.ParameterType == \
                        DB.ParameterType.FamilyType:
                fparam_value = get_symbol_name(ftype.AsElementId(fparam))
            elif fparam.StorageType == DB.StorageType.String:
                fparam_value = ftype.AsString(fparam)
            elif fparam.StorageType == DB.StorageType.Integer \
                    and fparam.Definition.ParameterType.YesNo:
                fparam_value = \
                    'true' if ftype.AsInteger(fparam) == 1 else 'false'
            else:
                fparam_value = ftype.AsValueString(fparam)

            type_config[fparam_name] = fparam_value

        cfgs_dict[TYPES_SECTION_NAME][ftype.Name] = type_config


def read_configs(selected_fparam_names, include_types=False):
    cfgs_dict = {PARAM_SECTION_NAME: {}, TYPES_SECTION_NAME: {}}

    fm = revit.doc.FamilyManager

    export_fparams = [x for x in fm.GetParameters()
                      if x.Definition.Name in selected_fparam_names]

    # grab all parameter defs
    for fparam in export_fparams:
        fparam_name = fparam.Definition.Name
        fparam_type = str(fparam.Definition.ParameterType)
        fparam_group = str(fparam.Definition.ParameterGroup)
        fparam_isinst = fparam.IsInstance
        fparam_formula = fparam.Formula

        cfgs_dict[PARAM_SECTION_NAME][fparam_name] = {
            PARAM_SECTION_TYPE: fparam_type,
            PARAM_SECTION_CAT: fparam_group,
            PARAM_SECTION_INST: fparam_isinst,
            PARAM_SECTION_FORMULA: fparam_formula
        }

    if include_types:
        include_type_configs(cfgs_dict, export_fparams)

    return cfgs_dict


def get_config_file():
    # Get parameter definition yaml file from user
    return forms.save_file(file_ext='yaml')


def save_configs(configs_dict, parma_file):
    # Load contents of yaml file into an ordered dict
    return yaml.dump_dict(configs_dict, parma_file)


def get_parameters():
    fm = revit.doc.FamilyManager
    return forms.SelectFromList.show(
        [x.Definition.Name for x in fm.GetParameters()],
        title="Select Parameters",
        multiselect=True,
    ) or []


if __name__ == '__main__':
    forms.check_familydoc(exitscript=True)

    family_cfg_file = get_config_file()
    if family_cfg_file:
        family_params = get_parameters()
        if family_params:
            inctypes = forms.alert(
                "Do you want to export family types as well?",
                yes=True, no=True
            )
            family_configs = read_configs(family_params, include_types=inctypes)
            logger.debug(family_configs)
            save_configs(family_configs, family_cfg_file)
