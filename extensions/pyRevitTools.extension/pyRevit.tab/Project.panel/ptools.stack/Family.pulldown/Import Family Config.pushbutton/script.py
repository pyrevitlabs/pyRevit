"""Import family configurations from yaml file and modify current family.

Family configuration file is expected to be a yaml file,
providing info about the parameters and types to be created.

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
		category: PG_GEOMETRY
		instance: false
types:
	24D"x36H":
		Shelf Height (Upper): 3'-0"
"""
#pylint: disable=import-error,invalid-name,broad-except
# TODO: import parameter ordering
# TODO: merge configs on identical parameters
from collections import namedtuple

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

from pyrevit.coreutils import yaml


__author__ = "{{author}}"


logger = script.get_logger()
output = script.get_output()


DEFAULT_TYPE = 'Text'
DEFAULT_BIP_CATEGORY = 'PG_CONSTRUCTION'

PARAM_SECTION_NAME = 'parameters'
PARAM_SECTION_TYPE = 'type'
PARAM_SECTION_CAT = 'category'
PARAM_SECTION_GROUP = 'group'
PARAM_SECTION_INST = 'instance'
PARAM_SECTION_REPORT = 'reporting'
PARAM_SECTION_FORMULA = 'formula'
PARAM_SECTION_DEFAULT = 'default'

TYPES_SECTION_NAME = 'types'

FAMILY_SYMBOL_SEPARATOR = ' : '
TEMP_TYPENAME = "Default"

ParamConfig = \
    namedtuple(
        'ParamConfig',
        ['name', 'bigroup', 'bitype', 'famcat',
         'isinst', 'isreport', 'formula', 'default']
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


failed_params = []


def get_symbol_id(symbol_name):
    # translate family-symbol formatted name and find the loaded symbol
    # current implementation matches the repr to how Revit shows the value
    # famil-name : symbol-name
    if FAMILY_SYMBOL_SEPARATOR not in symbol_name:
        logger.warning(
            'Family type parameter value must be formatted as '
            '<family-name> : <symbol-name> | incorrect format: %s',
            symbol_name
        )
        return

    fam_name, sym_name = symbol_name.split(FAMILY_SYMBOL_SEPARATOR)
    for fsym in DB.FilteredElementCollector(revit.doc)\
                  .OfClass(DB.FamilySymbol)\
                  .ToElements():
        famname = revit.query.get_name(fsym.Family)
        symname = revit.query.get_name(fsym)
        if famname == fam_name and symname == sym_name:
            return fsym.Id


def get_param_config(param_name, param_opts):
    # Extract parameter configurations from given dict
    # extract configured values
    param_bip_cat = coreutils.get_enum_value(
        DB.BuiltInParameterGroup,
        param_opts.get(PARAM_SECTION_GROUP, DEFAULT_BIP_CATEGORY)
        )
    param_type = coreutils.get_enum_value(
        DB.ParameterType,
        param_opts.get(PARAM_SECTION_TYPE, DEFAULT_TYPE)
        )
    param_famtype = None
    if param_type == DB.ParameterType.FamilyType:
        param_famtype = param_opts.get(PARAM_SECTION_CAT, None)
        if param_famtype:
            param_famtype = revit.query.get_category(param_famtype)
    param_isinst = \
        param_opts.get(PARAM_SECTION_INST, 'false').lower() == 'true'
    param_isreport = \
        param_opts.get(PARAM_SECTION_REPORT, 'false').lower() == 'true'
    param_formula = param_opts.get(PARAM_SECTION_FORMULA, None)
    param_default = param_opts.get(PARAM_SECTION_DEFAULT, None)

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

    # return a bundle with extracted values
    return ParamConfig(
        name=param_name,
        bigroup=param_bip_cat,
        bitype=param_type,
        famcat=param_famtype,
        isinst=param_isinst,
        isreport=param_isreport,
        formula=param_formula,
        default=param_default
        )


def set_fparam_value(pvcfg, fparam):
    # set param name:value on given param object
    # it is smart about the type and can resolve FamilyType values
    fm = revit.doc.FamilyManager

    if fparam.Formula:
        logger.debug(
            'can not set parameter value with formula: %s', pvcfg.name
            )
        return

    if not pvcfg.value:
        logger.debug('skipping parameter with no value: %s', pvcfg.name)
        return

    if fparam.StorageType == DB.StorageType.ElementId \
            and fparam.Definition.ParameterType == \
                DB.ParameterType.FamilyType:
        # resolve FamilyType value and get the symbol id
        fsym_id = get_symbol_id(pvcfg.value)
        fm.Set(fparam, fsym_id)
    elif fparam.StorageType == DB.StorageType.String:
        fm.Set(fparam, pvcfg.value)
    elif fparam.StorageType == DB.StorageType.Integer \
            and fparam.Definition.ParameterType.YesNo:
        fm.Set(fparam, 1 if pvcfg.value.lower() == 'true' else 0)
    else:
        fm.SetValueString(fparam, pvcfg.value)


def ensure_param(param_name, param_opts):
    # Create family parameter based on name and options
    fm = revit.doc.FamilyManager
    if param_name and param_opts:
        logger.debug('ensuring parameter: %s', param_name)

        # extract param config from dict
        pcfg = get_param_config(param_name, param_opts)

        if pcfg:
            logger.debug(
                '%s %s %s %s %s',
                pcfg.bigroup,
                pcfg.bitype,
                '"%s"' % pcfg.famcat.Name if pcfg.famcat else None,
                pcfg.isinst,
                pcfg.formula
            )
            fparam = revit.query.get_family_parameter(param_name, revit.doc)
            if not fparam:
                # create param in family doc
                try:
                    fparam = fm.AddParameter(
                        pcfg.name,
                        pcfg.bigroup,
                        pcfg.famcat if pcfg.famcat else pcfg.bitype,
                        pcfg.isinst
                    )
                except Exception as addparam_ex:
                    if pcfg.famcat:
                        failed_params.append(pcfg.name)
                        logger.error(
                            'Error creating parameter: %s\n'
                            'This parameter is a nested family selector. '
                            'Make sure at least one nested family of type "%s" '
                            'is already loaded in this family. | %s',
                            pcfg.name,
                            pcfg.famcat.Name,
                            addparam_ex
                            )

            logger.debug('Created: %s', fparam)

            # either set the formula
            if pcfg.formula:
                try:
                    if any([x in pcfg.formula for x in failed_params]):
                        logger.error(
                            'Can not set formula for: %s\n'
                            'One of the failed parameters is used in formula.',
                            pcfg.name,
                        )
                    else:
                        fm.SetFormula(fparam, pcfg.formula)
                except Exception as formula_ex:
                    logger.error('Failed to set formula on: %s | %s',
                                 pcfg.name, formula_ex)
            # or the default value if any
            elif pcfg.default:
                try:
                    set_fparam_value(
                        ParamValueConfig(name=pcfg.name, value=pcfg.default),
                        fparam
                        )
                except Exception as defaultval_ex:
                    logger.error('Failed to set default value for: %s | %s',
                                 pcfg.name, defaultval_ex)

            # is it reporting?
            # if param has default value, it is already set
            # value can not be set on reporting params
            if pcfg.isreport and not pcfg.formula:
                try:
                    fm.MakeReporting(fparam)
                except Exception as makereport_ex:
                    logger.error('Failed to make reporting: %s | %s',
                                 pcfg.name, makereport_ex)

            return fparam


def ensure_params(fconfig):
    # ensure all defined parameters exist
    param_cfgs = fconfig.get(PARAM_SECTION_NAME, None)
    if param_cfgs:
        for pname, popts in param_cfgs.items():
            ensure_param(pname, popts)


def get_type_config(type_name, type_opts):
    # get defined param:value configs from input
    if type_name and type_opts:
        pvalue_cfgs = []
        for pname, pvalue in type_opts.items():
            pvalue_cfgs.append(ParamValueConfig(name=pname, value=pvalue))

        return TypeConfig(name=type_name, param_values=pvalue_cfgs)


def ensure_type(type_config):
    # ensure given family type exist
    fm = revit.doc.FamilyManager
    # extract type config from dict
    logger.debug('%s %s', type_config.name, type_config.param_values)
    ftype = revit.query.get_family_type(type_config.name, revit.doc)
    if not ftype:
        # create type in family doc
        ftype = fm.NewType(type_config.name)

    return ftype


def ensure_types(fconfig):
    # ensure all defined family types exist
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
                            set_fparam_value(pvcfg, fparam)
                        else:
                            logger.warning(
                                'can not find parameter: %s', pvcfg.name
                                )


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
        family_mgr = revit.doc.FamilyManager
        family_configs = load_configs(family_cfg_file)
        logger.debug(family_configs)
        with revit.Transaction('Import Params from Config'):
            # remember current type
            # if family does not have type, create a temp type
            # otherwise setting formula will fail
            ctype = family_mgr.CurrentType
            if not ctype:
                ctype = family_mgr.NewType(TEMP_TYPENAME)

            ensure_params(family_configs)
            ensure_types(family_configs)

            # restore current type
            if ctype.Name != TEMP_TYPENAME:
                family_mgr.CurrentType = ctype
