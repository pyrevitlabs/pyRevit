"""Import family configurations from yaml file and modify current family.

Family configuration file is expected to be a yaml file,
providing info about the parameters and types to be created.

The structure of this config file is as shown below:

parameters:
	<parameter-name>:
		type: <Autodesk.Revit.DB.ParameterType>
		category: <Autodesk.Revit.DB.BuiltInParameterGroup>
		instance: <true|false>
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
from collections import namedtuple

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

PARAM_SECTION_NAME = 'parameters'
TYPES_SECTION_NAME = 'types'


ParamConfig = \
    namedtuple(
        'ParamConfig',
        ['name', 'bicat', 'bitype', 'isinst', 'formula']
    )


ParamValueConfig = \
    namedtuple(
        'ParamValueConfig',
        ['name', 'value']
    )


TypeConfig = \
    namedtuple(
        'TypeConfig',
        ['name', 'param_values']
    )


def get_symbol(symbol_name):
    for fsym in DB.FilteredElementCollector(revit.doc)\
                  .OfClass(DB.FamilySymbol)\
                  .ToElements():
        name = revit.query.get_name(fsym)
        if name == symbol_name:
            return fsym.Id


def get_param_config(param_name, param_opts):
    # Extract parameter configurations from given dict
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
    param_formula = param_opts.get('formula', None)

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

    return ParamConfig(
        name=param_name,
        bicat=param_bip_cat,
        bitype=param_type,
        isinst=param_isinst,
        formula=param_formula
        )


def ensure_param(param_name, param_opts):
    # Create family parameter based on name and options
    fm = revit.doc.FamilyManager
    if param_name and param_opts:
        logger.debug('ensuring parameter: %s', param_name)

        # extract param config from dict
        pcfg = get_param_config(param_name, param_opts)

        if pcfg:
            logger.debug('%s %s %s', pcfg.bicat, pcfg.bitype, pcfg.isinst)
            fparam = revit.query.get_family_parameter(param_name, revit.doc)
            if not fparam:
                # create param in family doc
                fparam = fm.AddParameter(
                    pcfg.name,
                    pcfg.bicat,
                    pcfg.bitype,
                    pcfg.isinst
                )
            
            if pcfg.formula:
                fm.SetFormula(fparam, pcfg.formula)

            return fparam


def ensure_params(fconfig):
    param_cfgs = fconfig.get(PARAM_SECTION_NAME, None)
    if param_cfgs:
        for pname, popts in param_cfgs.items():
            ensure_param(pname, popts)


def get_type_config(type_name, type_opts):
    if type_name and type_opts:
        pvalue_cfgs = []
        for pname, pvalue in type_opts.items():
            pvalue_cfgs.append(ParamValueConfig(name=pname, value=pvalue))

        return TypeConfig(name=type_name, param_values=pvalue_cfgs)


def ensure_type(type_config):
    fm = revit.doc.FamilyManager
    # extract type config from dict
    logger.debug('%s %s', type_config.name, type_config.param_values)
    ftype = revit.query.get_family_type(type_config.name, revit.doc)
    if not ftype:
        # create type in family doc
        ftype = fm.NewType(type_config.name)

    return ftype


def ensure_types(fconfig):
    fm = revit.doc.FamilyManager
    type_cfgs = fconfig.get(TYPES_SECTION_NAME, None)
    if type_cfgs:
        for tname, topts in type_cfgs.items():
            logger.debug('ensuring type: %s', tname)
            tcfg = get_type_config(tname, topts)
            if tcfg:
                ftype = ensure_type(tcfg)
                if ftype:
                    logger.debug('setting type values: %s', tname)
                    fm.CurrentType = ftype
                    for pvcfg in tcfg.param_values:
                        fparam = \
                            revit.query.get_family_parameter(
                                pvcfg.name,
                                revit.doc
                                )
                        logger.debug('setting value for: %s', pvcfg.name)
                        if fparam:
                            if fparam.StorageType == DB.StorageType.ElementId \
                                    and fparam.Definition.ParameterType == DB.ParameterType.FamilyType:
                                fsym_id = get_symbol(pvcfg.value)
                                fm.Set(fparam, fsym_id)
                            elif fparam.StorageType == DB.StorageType.String:
                                fm.Set(fparam, pvcfg.value)
                            elif fparam.StorageType == DB.StorageType.Integer \
                                    and fparam.Definition.ParameterType.YesNo:
                                fm.Set(fparam, 1 if pvcfg.value.lower() == 'true' else 0)
                            else:
                                fm.SetValueString(fparam, pvcfg.value)
                        else:
                            logger.warning('can not find parameter: %s', pvcfg.name)


def get_config_file():
    # Get parameter definition yaml file from user
    return forms.pick_file(file_ext='yaml')


def load_configs(parma_file):
    # Load contents of yaml file into an ordered dict
    return yaml.load_as_dict(parma_file)


if __name__ == '__main__':
    forms.check_familydoc(exitscript=True)

    family_cfg_file = get_config_file()
    if family_cfg_file:
        family_configs = load_configs(family_cfg_file)
        logger.debug(family_configs)
        with revit.Transaction('Import Params from Config'):
            ensure_params(family_configs)
            ensure_types(family_configs)
