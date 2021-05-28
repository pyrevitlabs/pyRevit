"""Export family configurations to yaml file.

Family configuration file is a yaml file,
providing info about the parameters and types defined in the family.
The shared parameters are exported to a txt file.
In the yaml file, the shared parameters are distinguished
by the presence of their GUID.

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

Note: If a parameter is in the revit file and the yaml file,
but shared in one and family in the other, after import,
the parameter won't change. So if it was shared in the revit file,
but family in the yaml file, it will remain shared.
"""
#pylint: disable=import-error,invalid-name,broad-except
# TODO: export parameter ordering
import codecs

from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import coreutils
from pyrevit import script
from pyrevit.coreutils import yaml

from Autodesk.Revit import Exceptions


logger = script.get_logger()
output = script.get_output()


# yaml sections and keys ------------------------------------------------------
PARAM_SECTION_NAME = 'parameters'
PARAM_SECTION_TYPE = 'type'
PARAM_SECTION_CAT = 'category'
PARAM_SECTION_GROUP = 'group'
PARAM_SECTION_INST = 'instance'
PARAM_SECTION_REPORT = 'reporting'
PARAM_SECTION_FORMULA = 'formula'
PARAM_SECTION_DEFAULT = 'default'
PARAM_SECTION_GUID = 'GUID' # To store unique if of shared parameters

TYPES_SECTION_NAME = 'types'

SHAREDPARAM_DEF = 'xref_sharedparams'
# -----------------------------------------------------------------------------

FAMILY_SYMBOL_FORMAT = '{} : {}'
ELECTRICAL_LOAD_CLASS_FORMAT = 'ELECTRICAL_LOAD_CLASS : {}'


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


def get_load_class_name(load_class_id):
    # load_class_id is an element id
    load_class = revit.doc.GetElement(load_class_id)
    return ELECTRICAL_LOAD_CLASS_FORMAT.format(load_class.Name)


def get_param_typevalue(ftype, fparam):
    fparam_value = None
    # extract value by param type
    if fparam.StorageType == DB.StorageType.ElementId:
        # support various types of params that reference other elements
        # these values can not be stored by their id since the same symbol
        # will most probably have a different id in another document
        if fparam.Definition.ParameterType == DB.ParameterType.FamilyType:
            # storing type references by their name
            fparam_value = get_symbol_name(ftype.AsElementId(fparam))

        elif fparam.Definition.ParameterType == \
                DB.ParameterType.LoadClassification:
            # storing load classifications by a unique id
            fparam_value = get_load_class_name(ftype.AsElementId(fparam))

    elif fparam.StorageType == DB.StorageType.String:
        fparam_value = ftype.AsString(fparam)

    elif fparam.StorageType == DB.StorageType.Integer:
        if DB.ParameterType.YesNo == fparam.Definition.ParameterType:
            fparam_value = \
                'true' if ftype.AsInteger(fparam) == 1 else 'false'
        else:
            fparam_value = ftype.AsInteger(fparam)

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
    cfgs_dict = dict({
        PARAM_SECTION_NAME: {},
        TYPES_SECTION_NAME: {},
        SHAREDPARAM_DEF: '',
        })

    fm = revit.doc.FamilyManager

    # pick the param objects from list of param names
    # params are wrapped by SortableParam
    # SortableParam helps sorting parameters based on their formula
    # dependencies. A parameter that is being used inside another params
    # formula is considered smaller (lower on the output) than that param
    export_sparams = [SortableParam(x) for x in fm.GetParameters()
                      if x.Definition.Name in selected_fparam_names]

    shared_params = []

    # grab all parameter defs
    for sparam in sorted(export_sparams, reverse=True):
        fparam_name = sparam.fparam.Definition.Name
        fparam_type = sparam.fparam.Definition.ParameterType
        fparam_group = sparam.fparam.Definition.ParameterGroup
        fparam_isinst = sparam.fparam.IsInstance
        fparam_isreport = sparam.fparam.IsReporting
        fparam_formula = sparam.fparam.Formula
        fparam_shared = sparam.fparam.IsShared

        cfgs_dict[PARAM_SECTION_NAME][fparam_name] = {
            PARAM_SECTION_TYPE: str(fparam_type),
            PARAM_SECTION_GROUP: str(fparam_group),
            PARAM_SECTION_INST: fparam_isinst,
            PARAM_SECTION_REPORT: fparam_isreport,
            PARAM_SECTION_FORMULA: fparam_formula,
        }

        # add extra data for shared params
        if fparam_shared:
            cfgs_dict[PARAM_SECTION_NAME][fparam_name][PARAM_SECTION_GUID] = \
                sparam.fparam.GUID

        # get the family category if param is FamilyType selector
        if fparam_type == DB.ParameterType.FamilyType:
            cfgs_dict[PARAM_SECTION_NAME][fparam_name][PARAM_SECTION_CAT] = \
                get_famtype_famcat(sparam.fparam)

        # Check if the current family parameter is a shared parameter
        if sparam.fparam.IsShared:
            # Add to an array of sorted shared parameters
            shared_params.append(sparam.fparam)

    # include type configs?
    if include_types:
        include_type_configs(cfgs_dict, export_sparams)
    elif include_defaults:
        add_default_values(cfgs_dict, export_sparams)

    return cfgs_dict, shared_params


def get_config_file():
    # Get parameter definition yaml file from user
    return forms.save_file(file_ext='yaml')


def get_parameters():
    # get list of parameters to be exported from user
    fm = revit.doc.FamilyManager
    return forms.SelectFromList.show(
        [x.Definition.Name for x in fm.GetParameters()],
        title="Select Parameters",
        multiselect=True,
    ) or []


def store_sharedparam_def(shared_params):
    # Reads the shared parameters into a txt file
    sparam_file = HOST_APP.app.OpenSharedParameterFile()
    exported_sparams_grp = sparam_file.Groups.Create("Exported Parameters")
    for sparam in shared_params:
        sparamdef_create_options = \
            DB.ExternalDefinitionCreationOptions(
                sparam.Definition.Name,
                sparam.Definition.ParameterType,
                GUID=sparam.GUID
            )

        try:
            exported_sparams_grp.Definitions.Create(sparamdef_create_options)
        except Exceptions.ArgumentException:
            forms.alert(
                "A parameter with the same GUID already exists. "
                "Parameter: %s will be ignored." % sparam.Definition.Name
            )


def get_shared_param_def_contents(shared_params):
    global family_cfg_file

    # get a temporary text file to store the generated shared param data
    temp_defs_filepath = \
        script.get_instance_data_file(
            file_id=coreutils.get_file_name(family_cfg_file),
            add_cmd_name=True
        )
    # make sure the file exists and it is empty
    open(temp_defs_filepath, 'w').close()

    # swap existing shared param with temp
    existing_sharedparam_file = HOST_APP.app.SharedParametersFilename
    HOST_APP.app.SharedParametersFilename = temp_defs_filepath
    # write the shared param data
    store_sharedparam_def(shared_params)
    # restore the original shared param file
    HOST_APP.app.SharedParametersFilename = existing_sharedparam_file

    return revit.files.read_text(temp_defs_filepath)


def save_configs(configs_dict, parma_file):
    # Load contents of yaml file into an ordered dict
    return yaml.dump_dict(configs_dict, parma_file)


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

            family_configs, shared_parameters = \
                read_configs(family_params,
                             include_types=inctypes,
                             include_defaults=incdefault)

            logger.debug(family_configs)

            # get revit to generate contents of a shared param file definition
            # for the shared parameters and store that inside the yaml file
            if shared_parameters:
                family_configs[SHAREDPARAM_DEF] = \
                    get_shared_param_def_contents(shared_parameters)

            save_configs(family_configs, family_cfg_file)
