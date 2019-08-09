"""Export family configurations to yaml file.

Family configuration file is a yaml file,
providing info about the parameters and types defined in the family.

The structure of this config file is as shown below:

parameters:
	<parameter-name>:
		type: <Autodesk.Revit.DB.ParameterType>
		category: <Autodesk.Revit.DB.BuiltInParameterGroup>
		instance: <true|false>
		reporting: <true|false>
		formula: <str>
		default: <str>
types:
	<type-name>:
		<parameter-name>: <value>
		<parameter-name>: <value>
		...


Example:

parameters:
	Shelf Height (Upper):
		type: Length
		group: PG_GEOMETRY
		instance: false
types:
	24D"x36H":
		Shelf Height (Upper): 3'-0"
"""
#pylint: disable=import-error,invalid-name,broad-except
# TODO: export parameter ordering
from collections import OrderedDict

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

from pyrevit.coreutils import yaml


__author__ = "{{author}}"


logger = script.get_logger()
output = script.get_output()


PARAM_SECTION_NAME = 'parameters'
PARAM_SECTION_TYPE = 'type'
PARAM_SECTION_CAT = 'category'
PARAM_SECTION_GROUP = 'group'
PARAM_SECTION_INST = 'instance'
PARAM_SECTION_REPORT = 'reporting'
PARAM_SECTION_FORMULA = 'formula'
PARAM_SECTION_DEFAULT = 'default'

TYPES_SECTION_NAME = 'types'


FAMILY_SYMBOL_FORMAT = '{} : {}'


class SortableParam(object):
    def __init__(self, fparam):
        self.fparam = fparam

    def __lt__(self, other_sortableparam):
        formula = other_sortableparam.fparam.Formula
        if formula:
            return self.fparam.Definition.Name in formula


def get_symbol_name(symbol_id):
    # get family-symbol formatted name for export
    # current implementation matches the repr to how Revit shows the value
    # famil-name : symbol-name
    for fsym in DB.FilteredElementCollector(revit.doc)\
                  .OfClass(DB.FamilySymbol)\
                  .ToElements():
        if fsym.Id == symbol_id:
            return FAMILY_SYMBOL_FORMAT.format(
                revit.query.get_name(fsym.Family),
                revit.query.get_name(fsym)
            )


def get_param_typevalue(ftype, fparam):
    fparam_value = None
    # extract value by param type
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

    return fparam_value


def include_type_configs(cfgs_dict, sparams):
    # add the parameter values for all types into the configs dict
    fm = revit.doc.FamilyManager

    # grab param values for each family type
    for ftype in fm.Types:
        # param value dict for this type
        type_config = {}
        # grab value from each param
        for sparam in sparams:
            fparam_name = sparam.fparam.Definition.Name
            # add the value to this type config
            type_config[fparam_name] = \
                get_param_typevalue(ftype, sparam.fparam)

        # add the type config to overall config dict
        cfgs_dict[TYPES_SECTION_NAME][ftype.Name] = type_config


def add_default_values(cfgs_dict, sparams):
    # add the parameter values for all types into the configs dict
    fm = revit.doc.FamilyManager

    # grab value from each param
    for sparam in sparams:
        fparam_name = sparam.fparam.Definition.Name
        param_config = cfgs_dict[PARAM_SECTION_NAME][fparam_name]
        # grab current param value
        fparam_value = get_param_typevalue(fm.CurrentType, sparam.fparam)
        if fparam_value:
            param_config[PARAM_SECTION_DEFAULT] = fparam_value


def get_famtype_famcat(fparam):
    # grab the family category from para with type DB.ParameterType.FamilyType
    # these parameters point to a family and symbol but the Revit API
    # does not provide info on what family categories they are assinged to
    fm = revit.doc.FamilyManager
    famtype = revit.doc.GetElement(fm.CurrentType.AsElementId(fparam))
    return famtype.Category.Name


def read_configs(selected_fparam_names,
                 include_types=False, include_defaults=False):
    # read parameter and type configurations into a dictionary
    cfgs_dict = OrderedDict({PARAM_SECTION_NAME: {}, TYPES_SECTION_NAME: {}})

    fm = revit.doc.FamilyManager

    # pick the param objects from list of param names
    # params are wrapped by SortableParam
    # SortableParam helps sorting parameters based on their formula
    # dependencies. A parameter that is being used inside another params
    # formula is considered smaller (lower on the output) than that param
    export_sparams = [SortableParam(x) for x in fm.GetParameters()
                      if x.Definition.Name in selected_fparam_names]

    # grab all parameter defs
    for sparam in sorted(export_sparams, reverse=True):
        fparam_name = sparam.fparam.Definition.Name
        fparam_type = sparam.fparam.Definition.ParameterType
        fparam_group = sparam.fparam.Definition.ParameterGroup
        fparam_isinst = sparam.fparam.IsInstance
        fparam_isreport = sparam.fparam.IsReporting
        fparam_formula = sparam.fparam.Formula

        cfgs_dict[PARAM_SECTION_NAME][fparam_name] = {
            PARAM_SECTION_TYPE: str(fparam_type),
            PARAM_SECTION_GROUP: str(fparam_group),
            PARAM_SECTION_INST: fparam_isinst,
            PARAM_SECTION_REPORT: fparam_isreport,
            PARAM_SECTION_FORMULA: fparam_formula
        }

        # get the family category if param is FamilyType selector
        if fparam_type == DB.ParameterType.FamilyType:
            cfgs_dict[PARAM_SECTION_NAME][fparam_name][PARAM_SECTION_CAT] = \
                get_famtype_famcat(sparam.fparam)

    # include type configs?
    if include_types:
        include_type_configs(cfgs_dict, export_sparams)
    elif include_defaults:
        add_default_values(cfgs_dict, export_sparams)

    return cfgs_dict


def get_config_file():
    # Get parameter definition yaml file from user
    return forms.save_file(file_ext='yaml')


def save_configs(configs_dict, parma_file):
    # Load contents of yaml file into an ordered dict
    return yaml.dump_dict(configs_dict, parma_file)


def get_parameters():
    # get list of parameters to be exported from user
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
            inctypes = incdefault = False
            # ask user to include family type definitions
            inctypes = forms.alert(
                "Do you want to export family types as well?",
                yes=True, no=True
            )
            # if said no, ask if the current param values should be included
            if not inctypes:
                incdefault = forms.alert(
                    "Do you want to include the current parameter values as "
                    "default? Otherwise the parameters will not include any "
                    "value and their default value will be assigned "
                    "by Revit at import.",
                    yes=True, no=True
                )

            family_configs = \
                read_configs(family_params,
                             include_types=inctypes,
                             include_defaults=incdefault)

            logger.debug(family_configs)
            save_configs(family_configs, family_cfg_file)
